"""
bconsole MCP Server — Real-time Bacula Director access via bconsole over SSH.

Unlike the Bacularis REST API (which reads the catalog and shows 0 bytes for
running jobs), this server runs `status director` directly in the Director's
memory, giving accurate real-time byte counts for running jobs.
"""

import re
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bconsole")

BACULA_HOST = "sra-bacula-01"
BCONSOLE_CMD = "sudo bconsole"

# Storage device archive paths — used for physical file truncation
STORAGE_PATHS = {
    "File1": "/mnt/nas/bacula",
    "PlasticFile1": "/mnt/nas/plastic-bacula",
}

# MediaType → storage name mapping
MEDIATYPE_STORAGE = {
    "File1": "File1",
    "PlasticFile": "PlasticFile1",
}

# Known status suffixes for running jobs (longest-first for greedy match)
_RUNNING_STATUSES = [
    "is waiting for higher priority jobs to finish",
    "is waiting on max Job jobs",
    "is waiting on SD max Job jobs",
    "is waiting for a tape mount",
    "is waiting execution",
    "is waiting for Client resource",
    "is running (executing Before Job Scripts)",
    "is running",
    "has been canceled",
    "is being stopped",
]


def _reject_injection(value: str, name: str) -> str:
    """Reject values that could inject extra bconsole commands via stdin.

    _run() joins commands with '\\n' and pipes them to bconsole's REPL over
    stdin — a newline embedded in an otherwise-legitimate argument (job name,
    volume name, client name) would be interpreted as a second command.
    """
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"Invalid {name}: must be non-empty and contain no newlines")
    return value


def _require_confirm(confirm: bool, action: str) -> None:
    if not confirm:
        raise ValueError(
            f"SECURITY: {action} was not run. This is a destructive/high-impact Bacula "
            "operation. Ask the user for explicit permission, then call again with "
            "confirm=true."
        )


def _run(commands: list[str], timeout: int = 30) -> tuple[str, str]:
    """Send commands to bconsole on BACULA_HOST via SSH. Returns (stdout, stderr)."""
    input_str = "\n".join(commands) + "\nquit\n"
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", BACULA_HOST, BCONSOLE_CMD],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.stderr


def _ssh(command: str, timeout: int = 60) -> tuple[str, str]:
    """Run a shell command directly on BACULA_HOST via SSH (not bconsole)."""
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", BACULA_HOST, command],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip()


def _bytes_str_to_int(s: str) -> int:
    """Convert Bacula byte string like '8.597 T' or '246.0 G' to bytes."""
    s = s.strip()
    suffixes = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    for suffix, mult in suffixes.items():
        if s.endswith(suffix):
            try:
                return int(float(s[:-1].strip()) * mult)
            except ValueError:
                return 0
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return 0


def _parse_status_director(output: str) -> dict:
    """Parse `status director` bconsole output into structured dict."""
    result = {
        "version": "",
        "started": "",
        "running_count": 0,
        "max_jobs": 0,
        "scheduled": [],
        "running": [],
        "terminated": [],
    }

    lines = output.splitlines()

    # Header
    for line in lines:
        if "bacula-dir Version:" in line:
            result["version"] = line.strip()
        elif "Daemon started" in line:
            result["started"] = line.strip()
        elif line.strip().startswith("Jobs:"):
            m = re.search(r"running=(\d+).*max=(\d+)", line)
            if m:
                result["running_count"] = int(m.group(1))
                result["max_jobs"] = int(m.group(2))

    # Sections
    section = None
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Scheduled Jobs"):
            section = "scheduled"
            continue
        elif stripped.startswith("Running Jobs"):
            section = "running"
            continue
        elif stripped.startswith("Terminated Jobs"):
            section = "terminated"
            continue
        elif stripped == "====" or stripped.startswith("===="):
            continue
        elif stripped.startswith("Level") or stripped.startswith("JobId"):
            continue  # header rows
        elif stripped.startswith("Console connected"):
            continue

        if not stripped or not section:
            continue

        if section == "scheduled":
            m = re.match(
                r"(\S+)\s+(\S+)\s+(\d+)\s+(\d{2}-\w{3}-\d{2}\s+\d{2}:\d{2})\s{2,}(.+?)\s{2,}(\S+)\s*$",
                stripped,
            )
            if m:
                result["scheduled"].append({
                    "level": m.group(1),
                    "type": m.group(2),
                    "priority": int(m.group(3)),
                    "scheduled": m.group(4),
                    "job": m.group(5).strip(),
                    "volume": m.group(6).strip(),
                })

        elif section == "running":
            m = re.match(r"\s*(\d+)\s+(\S+)\s+(\S+)\s+([\d,]+)\s+([\d,.]+\s*[KMGTP]?)\s{2,}(.+)$", line)
            if m:
                jobid = int(m.group(1))
                files = int(m.group(4).replace(",", ""))
                bytes_raw = m.group(5).strip()
                remainder = m.group(6).strip()

                name = remainder
                status = ""
                for known in _RUNNING_STATUSES:
                    if remainder.endswith(known):
                        name = remainder[: -len(known)].strip()
                        status = known
                        break

                result["running"].append({
                    "jobid": jobid,
                    "type": m.group(2),
                    "level": m.group(3),
                    "files": files,
                    "bytes": _bytes_str_to_int(bytes_raw),
                    "bytes_display": bytes_raw,
                    "name": name,
                    "status": status or remainder,
                })

        elif section == "terminated":
            m = re.match(
                r"\s*(\d+)\s+(\S+)\s+([\d,]+)\s+([\d,.]+\s*[KMGTP]?)\s+(OK|Cancel|Error|Warn)\s+"
                r"(\d{2}-\w{3}-\d{2}\s+\d{2}:\d{2})\s+(.+)$",
                line,
            )
            if m:
                result["terminated"].append({
                    "jobid": int(m.group(1)),
                    "level": m.group(2),
                    "files": int(m.group(3).replace(",", "")),
                    "bytes": _bytes_str_to_int(m.group(4).strip()),
                    "bytes_display": m.group(4).strip(),
                    "status": m.group(5),
                    "finished": m.group(6),
                    "name": m.group(7).strip(),
                })

    return result


def _parse_volumes(output: str) -> list[dict]:
    """Parse `list volumes` output into a list of volume dicts."""
    volumes = []
    for line in output.splitlines():
        # Skip headers and pool section lines
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6 or not parts[1].isdigit():
            continue
        volumes.append({
            "media_id": int(parts[1]),
            "volume_name": parts[2],
            "vol_status": parts[3],
            "enabled": parts[4],
            "vol_bytes": int(parts[5].replace(",", "")) if parts[5].replace(",", "").isdigit() else 0,
            "vol_files": int(parts[6].replace(",", "")) if len(parts) > 6 and parts[6].replace(",", "").isdigit() else 0,
            "media_type": parts[10] if len(parts) > 10 else "",
            "last_written": parts[13] if len(parts) > 13 else "",
        })
    return volumes


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def status_director() -> dict:
    """Get real-time Bacula Director status including running job byte counts.

    This calls `status director` in bconsole, which reads from the Director's
    memory — unlike Bacularis which reads the catalog and shows 0 bytes for
    running jobs. Use this to check actual progress of running backup jobs.

    Returns structured data with:
    - running: jobs currently executing with live files/bytes transferred
    - scheduled: jobs queued for future execution
    - terminated: recently completed jobs (last ~10)
    """
    stdout, stderr = _run(["status dir"])
    if not stdout:
        return {"error": f"bconsole failed: {stderr[:200]}"}
    return _parse_status_director(stdout)


@mcp.tool()
def list_running_jobs() -> list[dict]:
    """List currently running Bacula jobs with real-time byte counts.

    Returns only the running jobs section from `status director`, with
    accurate files/bytes transferred as reported by the Director (not catalog).
    """
    result = status_director()
    if "error" in result:
        return [result]
    return result.get("running", [])


@mcp.tool()
def cancel_job(jobid: int, confirm: bool = False) -> str:
    """Cancel a running or queued Bacula job.

    WARNING: Verify the job is actually a zombie (stuck with no real progress)
    before canceling. Use list_running_jobs() first to check actual byte counts —
    a job showing 0 bytes in Bacularis may have significant real data per
    status_director().

    Args:
        jobid: The Bacula job ID to cancel
        confirm: Must be true to cancel. Ask the user for permission first.
    """
    _require_confirm(confirm, f"cancel_job({jobid})")
    stdout, stderr = _run([f"cancel jobid={jobid}"])
    if not stdout:
        return f"Error: {stderr[:200]}"
    for line in stdout.splitlines():
        if "marked to be canceled" in line or "already been canceled" in line or "not found" in line:
            return line.strip()
    return stdout.strip()


@mcp.tool()
def run_job(
    job_name: str,
    level: Optional[str] = None,
    client: Optional[str] = None,
    confirm: bool = False,
) -> str:
    """Start a Bacula backup job immediately.

    Args:
        job_name: Exact job name as defined in Bacula config (e.g. "SRS-Plastic-01 Plastic Data Backup")
        level: Override backup level: Full, Incremental, or Differential
        client: Override client name
        confirm: Must be true to run the job. Ask the user for permission first.
    """
    _require_confirm(confirm, f"run_job({job_name!r})")
    _reject_injection(job_name, "job_name")
    if client is not None:
        _reject_injection(client, "client")
    cmd = f'run job="{job_name}"'
    if level:
        cmd += f" level={level}"
    if client:
        cmd += f" client={client}"
    cmd += " yes"
    stdout, stderr = _run([cmd])
    if not stdout:
        return f"Error: {stderr[:200]}"
    for line in stdout.splitlines():
        if "JobId=" in line or "Job queued" in line or "Error" in line:
            return line.strip()
    return stdout.strip()


@mcp.tool()
def purge_volume(volume_name: str, confirm: bool = False) -> str:
    """Purge all job records for a volume from the Bacula catalog.

    Marks the volume as Purged so Bacula can recycle it. Does not delete
    the physical file. Use this to clean up volumes from incomplete/canceled jobs.

    Args:
        volume_name: Volume name (e.g. "Plastic-Full-0781")
        confirm: Must be true to purge. Ask the user for permission first.
    """
    _require_confirm(confirm, f"purge_volume({volume_name!r})")
    _reject_injection(volume_name, "volume_name")
    stdout, stderr = _run([f"purge volume={volume_name}"])
    if not stdout:
        return f"Error: {stderr[:200]}"
    for line in stdout.splitlines():
        if "purged" in line.lower() or "Marking it purged" in line or "error" in line.lower():
            return line.strip()
    return stdout.strip()


@mcp.tool()
def prune_client(client_name: str) -> dict:
    """Prune expired job and file records for a specific client.

    Removes catalog entries that have exceeded their retention period.
    Safe — only removes expired records, never touches active job data
    or physical files.

    Args:
        client_name: Bacula client name (e.g. "SteamHV1")
    """
    _reject_injection(client_name, "client_name")
    commands = [
        f"prune jobs client={client_name} yes",
        f"prune files client={client_name} yes",
    ]
    stdout, stderr = _run(commands, timeout=120)
    if not stdout:
        return {"error": f"bconsole failed: {stderr[:200]}"}

    pruned_jobs = 0
    pruned_files = 0
    for line in stdout.splitlines():
        m = re.search(r"(\d+) Job", line)
        if m and "job" in line.lower():
            pruned_jobs = int(m.group(1))
        m = re.search(r"(\d+) File", line)
        if m and "file" in line.lower():
            pruned_files = int(m.group(1))

    return {
        "client": client_name,
        "pruned_jobs": pruned_jobs,
        "pruned_files": pruned_files,
        "output": stdout.strip(),
    }


@mcp.tool()
def prune_all(confirm: bool = False) -> dict:
    """Prune expired records for all clients and volumes.

    Sweeps the full catalog — jobs, files, and volumes — removing anything
    past its retention period. Equivalent to running the weekly maintenance
    job manually. Safe to run at any time; does not touch physical files.

    Args:
        confirm: Must be true to run. Ask the user for permission first.
    """
    _require_confirm(confirm, "prune_all()")
    # Get client list from catalog
    stdout, stderr = _run(["list clients"], timeout=30)
    client_names = re.findall(r"\|\s*(\S+-fd|\S+)\s*\|", stdout)
    # Filter out header/non-client rows
    client_names = [c for c in client_names if c not in ("Name", "ClientId")]

    if not client_names:
        return {"error": "Could not retrieve client list", "detail": stderr[:200]}

    # Build prune commands for all clients + volumes
    commands = []
    for client in client_names:
        commands.append(f"prune jobs client={client} yes")
        commands.append(f"prune files client={client} yes")
    commands.append("prune volumes yes")

    stdout, stderr = _run(commands, timeout=300)
    if not stdout:
        return {"error": f"bconsole failed: {stderr[:200]}"}

    return {
        "clients_pruned": client_names,
        "client_count": len(client_names),
        "volumes_pruned": True,
        "output": stdout.strip(),
    }


@mcp.tool()
def list_purged_volumes() -> list[dict]:
    """List all volumes with Purged status across all pools.

    These volumes have had all job records removed and are ready to be
    recycled by Bacula. With ActionOnPurge = Truncate set on all pools,
    the physical files will be truncated automatically on the next prune cycle.
    """
    stdout, stderr = _run(["list volumes"], timeout=60)
    if not stdout:
        return [{"error": f"bconsole failed: {stderr[:200]}"}]

    all_volumes = _parse_volumes(stdout)
    purged = [v for v in all_volumes if v["vol_status"] == "Purged"]
    return purged


@mcp.tool()
def optimize_catalog() -> dict:
    """Run OPTIMIZE TABLE on the Bacula catalog database.

    Reclaims fragmented space and rebuilds indexes on the File, Path, Job,
    and related tables. The File table grows large over time (23M+ rows) —
    this keeps query performance healthy. Safe to run while Bacula is active.
    Typically takes 1-5 minutes depending on table size.
    Recommended cadence: monthly (also runs via scheduled Admin job).
    """
    cmd = (
        "sudo mysqlcheck --optimize --user=root bacula "
        "File Path Job JobMedia FileMedia PathHierarchy PathVisibility 2>&1"
    )
    stdout, stderr = _ssh(cmd, timeout=300)
    if not stdout and stderr:
        return {"error": stderr[:500]}

    results = {}
    for line in stdout.splitlines():
        if "." in line and ("OK" in line or "note" in line or "error" in line.lower()):
            parts = line.split(None, 1)
            if len(parts) == 2:
                results[parts[0]] = parts[1].strip()

    return {
        "status": "completed",
        "tables": results,
        "raw": stdout,
    }


@mcp.tool()
def dbcheck() -> dict:
    """Run Bacula's built-in catalog consistency checker.

    Finds and removes orphaned records: paths with no files, clients with
    no jobs, files with no valid paths, etc. Runs in batch mode — safe fixes
    only, no interactive prompts. Good to run after major config changes,
    bulk deletions, or a lot of canceled/failed jobs.
    """
    cmd = "sudo dbcheck -c /etc/bacula/bacula-dir.conf -b -v 2>&1"
    stdout, stderr = _ssh(cmd, timeout=120)
    if not stdout and stderr:
        return {"error": stderr[:500]}

    issues_found = []
    fixed = []
    for line in stdout.splitlines():
        if "found" in line.lower() or "fixing" in line.lower() or "orphan" in line.lower():
            issues_found.append(line.strip())
        if "fixed" in line.lower() or "deleted" in line.lower():
            fixed.append(line.strip())

    return {
        "status": "completed",
        "issues_found": issues_found,
        "fixed": fixed,
        "raw": stdout,
    }


# console() is a read-only escape hatch — only bconsole verbs that query state,
# never ones that mutate the catalog, storage, or run jobs. Mutating actions
# have dedicated tools above with confirm gates; this allowlist keeps console()
# from becoming a way to bypass those gates (e.g. "purge volume=...", "run job=...").
_CONSOLE_ALLOWED_VERBS = {
    "status", "list", "llist", "show", "help", "version", ".api",
    "messages", "query", "estimate",
}


@mcp.tool()
def console(command: str) -> str:
    """Run a raw, read-only bconsole command and return output.

    Escape hatch for read-only queries not covered by other tools (status,
    list, llist, show, help, version, messages, query, estimate). Mutating
    commands (run, purge, prune, cancel, delete, label, mount, sql, etc.) are
    rejected — use the dedicated tool for that action instead, which enforces
    a confirmation gate.

    Args:
        command: bconsole command string (e.g. "list volumes pool=Plastic-Full-Pool")
    """
    _reject_injection(command, "command")
    verb = command.strip().split(None, 1)[0].lower() if command.strip() else ""
    if verb not in _CONSOLE_ALLOWED_VERBS:
        raise ValueError(
            f"SECURITY: console() only allows read-only verbs {sorted(_CONSOLE_ALLOWED_VERBS)}. "
            f"'{verb}' is not permitted here. If this is a mutating action, use its "
            "dedicated tool (run_job, purge_volume, prune_client, prune_all, cancel_job), "
            "which requires explicit confirmation."
        )
    stdout, stderr = _run([command], timeout=60)
    if not stdout:
        return f"Error: {stderr[:200]}"
    lines = stdout.splitlines()
    body = [l for l in lines if not l.startswith("Connecting to") and
            not l.startswith("1000 OK") and
            not l.startswith("Enter a period")]
    return "\n".join(body).strip()


if __name__ == "__main__":
    mcp.run(transport="stdio")
