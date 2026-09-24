"""
Altaro MCP Server. Read-only Altaro VM Backup reporting for the Hyper-V hosts.

Altaro writes one "Backup Result" event per VM per run to the Application log
(provider "Altaro VM Backup"). This server reads those events over SSH
(OpenSSH + PowerShell on the Hyper-V hosts, same key Ansible uses) so a
failure can be traced to the specific VM and error code in one call.

Event IDs: 5000 = backup success, 5002 = backup failure, 5003 = verification.
"""

import base64
import json
import os
import re
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "altaro",
    instructions=(
        "Read-only Altaro VM Backup reporting for the work Hyper-V hosts STEAMHV1 and STEAMHV2. "
        "Reads per-VM backup, failure and verification results from the Windows Application event "
        "log, plus Altaro service state. Use it to find which VM an Altaro backup alert refers to "
        "and why it failed (ALTERR codes). Proxmox VMs are backed up by PBS and bare-metal servers "
        "by Bacula, not Altaro."
    ),
)

HOSTS = {
    "STEAMHV1": "10.100.0.101",
    "STEAMHV2": "10.100.0.106",
}
SSH_USER = os.environ.get("ALTARO_SSH_USER", "ansible")
SSH_KEY = os.path.expanduser(os.environ.get("ALTARO_SSH_KEY", "~/.ssh/ansible_win_ed25519"))

EVENT_KINDS = {5000: "backup_success", 5002: "backup_failed", 5003: "verification"}

_VM_NAME_RE = re.compile(r"^[\w .()\-]{1,100}$")


def _resolve_hosts(host: Optional[str]) -> list[str]:
    if not host:
        return list(HOSTS)
    key = host.upper()
    if key not in HOSTS:
        raise ValueError(f"Unknown host {host!r}. Valid: {', '.join(HOSTS)}")
    return [key]


def _check_vm(vm: Optional[str]) -> Optional[str]:
    if vm is not None and not _VM_NAME_RE.match(vm):
        raise ValueError("Invalid vm name: letters, digits, space, . ( ) - _ only")
    return vm


def _ps(host: str, script: str, timeout: int = 90) -> object:
    """Run a PowerShell script on a Hyper-V host over SSH and parse its JSON output."""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    result = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-i", SSH_KEY, f"{SSH_USER}@{HOSTS[host]}",
            f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return {"error": f"ssh exit {result.returncode}", "detail": result.stderr.strip()[:500]}
    out = result.stdout.strip()
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": "Non-JSON output", "detail": out[:500]}


_EVENTS_SCRIPT = r"""
$f = @{LogName='Application'; ProviderName='Altaro VM Backup'; Id=5000,5002,5003; StartTime=(Get-Date).AddDays(-__DAYS__)}
$ev = Get-WinEvent -FilterHashtable $f -ErrorAction SilentlyContinue
$rows = foreach ($e in $ev) {
    $m = $e.Message
    $vm = if ($m -match 'Guest VM Name:\s*(.+)') { $Matches[1].Trim() } else { $null }
    $err = if ($m -match '\((ALTERR_[A-Z_0-9]+)\)') { $Matches[1] } else { $null }
    [pscustomobject]@{
        time = $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
        id = $e.Id
        vm = $vm
        error_code = $err
        message = (($m -split "`n" | Select-Object -Skip 1) -join ' ' -replace '\s+', ' ').Trim()
    }
}
ConvertTo-Json -InputObject @($rows) -Depth 3 -Compress
"""


def _events(host: str, days: int) -> list[dict] | dict:
    data = _ps(host, _EVENTS_SCRIPT.replace("__DAYS__", str(int(days))))
    if isinstance(data, dict) and "error" in data:
        return data
    rows = data if isinstance(data, list) else [data]
    for r in rows:
        r["host"] = host
        r["result"] = EVENT_KINDS.get(r.get("id"), "other")
    return rows


@mcp.tool()
def get_backup_results(
    host: Optional[str] = None,
    vm: Optional[str] = None,
    days: int = 2,
    failed_only: bool = False,
) -> str:
    """Get recent Altaro VM Backup results per VM from STEAMHV1/STEAMHV2 (Hyper-V).

    Returns each backup success, failure (with ALTERR error code and message) and
    verification event, newest first. Use this to see which VM caused an
    "Altaro: Onsite backup failed" Zabbix alert.

    Args:
        host: STEAMHV1 or STEAMHV2. Omit to query both.
        vm: Filter to one Hyper-V VM name (case-insensitive substring).
        days: How many days back to read (1-30). Default 2.
        failed_only: Only return failed backups.
    """
    _check_vm(vm)
    days = max(1, min(int(days), 30))
    out, errors = [], []
    for h in _resolve_hosts(host):
        rows = _events(h, days)
        if isinstance(rows, dict):
            errors.append({"host": h, **rows})
            continue
        out.extend(rows)
    if vm:
        out = [r for r in out if r.get("vm") and vm.lower() in r["vm"].lower()]
    if failed_only:
        out = [r for r in out if r["result"] == "backup_failed"]
    out.sort(key=lambda r: r["time"], reverse=True)
    return json.dumps({"results": out, "errors": errors}, indent=2)


@mcp.tool()
def get_vm_backup_summary(days: int = 14, host: Optional[str] = None) -> str:
    """Summarize Altaro backup health per Hyper-V VM: last success, last failure, consecutive failures.

    Flags VMs whose most recent backups keep failing, which a single "latest
    result" check can miss when other VMs succeed later in the same run.

    Args:
        days: Lookback window in days (1-30). Default 14.
        host: STEAMHV1 or STEAMHV2. Omit to query both.
    """
    days = max(1, min(int(days), 30))
    summary: dict[str, dict] = {}
    errors = []
    for h in _resolve_hosts(host):
        rows = _events(h, days)
        if isinstance(rows, dict):
            errors.append({"host": h, **rows})
            continue
        for r in sorted(rows, key=lambda r: r["time"]):
            if r["result"] not in ("backup_success", "backup_failed") or not r.get("vm"):
                continue
            s = summary.setdefault(r["vm"], {
                "vm": r["vm"], "host": h, "last_success": None, "last_failure": None,
                "last_error_code": None, "consecutive_failures": 0,
            })
            if r["result"] == "backup_success":
                s["last_success"] = r["time"]
                s["consecutive_failures"] = 0
            else:
                s["last_failure"] = r["time"]
                s["last_error_code"] = r.get("error_code")
                s["consecutive_failures"] += 1
    vms = sorted(summary.values(), key=lambda s: (-s["consecutive_failures"], s["vm"]))
    return json.dumps({"window_days": days, "vms": vms, "errors": errors}, indent=2)


@mcp.tool()
def get_altaro_service_status(host: Optional[str] = None) -> str:
    """Get state and start time of the Altaro VM Backup Windows services on STEAMHV1/STEAMHV2.

    Args:
        host: STEAMHV1 or STEAMHV2. Omit to query both.
    """
    script = r"""
$svc = Get-CimInstance Win32_Service -Filter "Name LIKE 'Altaro%'" | ForEach-Object {
    $p = if ($_.ProcessId) { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue } else { $null }
    [pscustomobject]@{
        name = $_.Name; display_name = $_.DisplayName; state = $_.State; start_mode = $_.StartMode
        started = if ($p) { $p.StartTime.ToString('yyyy-MM-dd HH:mm:ss') } else { $null }
    }
}
ConvertTo-Json -InputObject @($svc) -Compress
"""
    return json.dumps({h: _ps(h, script) for h in _resolve_hosts(host)}, indent=2)


if __name__ == "__main__":
    mcp.run()
