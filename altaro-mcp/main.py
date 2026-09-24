"""
Altaro MCP Server. Read-only Altaro VM Backup reporting for the Hyper-V hosts.

Altaro writes one "Backup Result" event per VM per run to the Application log
(provider "Altaro VM Backup"). This server reads those events over SSH
(OpenSSH + PowerShell on the Hyper-V hosts, same key Ansible uses) so a
failure can be traced to the specific VM and error code in one call.

Event IDs: 5000 = backup success, 5002 = backup failure, 5003 = verification.

Live job progress and per-VM status come from the Altaro REST API
(https://localhost:35113/api on each host, called over the same SSH session).
The API refuses sessions while the Altaro Management Console is connected to
that host; tools fall back to event-log/checkpoint data and say so.
API login: env ALTARO_API_USER / ALTARO_API_PASSWORD / ALTARO_API_DOMAIN, or the
enigma entry named by ALTARO_ENIGMA_KEY (default svc-altaro-mcp-altaro-api).
The password is sent to the host over SSH stdin, never on a command line.
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
        "log, live backup progress per VM (percent complete), per-VM last/next backup and offsite "
        "copy status, plus Altaro service state. Use it to find which VM an Altaro backup alert "
        "refers to and why it failed (ALTERR codes). Proxmox VMs are backed up by PBS and bare-metal servers "
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
_ACCOUNT_RE = re.compile(r"^[\w.\-]{1,64}$")


def _api_creds() -> tuple[str, str, str]:
    """Return (user, password, domain) for the Altaro REST API."""
    user = os.environ.get("ALTARO_API_USER")
    password = os.environ.get("ALTARO_API_PASSWORD")
    domain = os.environ.get("ALTARO_API_DOMAIN", "STEAMR")
    if not (user and password):
        key = os.environ.get("ALTARO_ENIGMA_KEY", "svc-altaro-mcp-altaro-api")
        with open(os.path.expanduser("~/.enigma.json")) as f:
            entry = json.load(f)[key]
        user, password = entry["username"], entry["password"]
        domain = entry.get("domain", domain)
    if not (_ACCOUNT_RE.match(user) and _ACCOUNT_RE.match(domain)) or "\n" in password:
        raise ValueError("Altaro API credentials contain unsupported characters")
    return user, password, domain


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


def _ps(host: str, script: str, timeout: int = 90, stdin: Optional[str] = None) -> object:
    """Run a PowerShell script on a Hyper-V host over SSH and parse its JSON output.

    `stdin` is readable in the script via [Console]::In.ReadLine(). Without it, ssh
    gets /dev/null so it can never consume the MCP server's own stdio stream.
    """
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    result = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-i", SSH_KEY, f"{SSH_USER}@{HOSTS[host]}",
            f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}",
        ],
        input=stdin + "\n" if stdin is not None else None,
        stdin=subprocess.DEVNULL if stdin is None else None,
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


# Shared PowerShell prologue for REST API calls. The password arrives on stdin.
# The API only listens on https://localhost with a self-signed cert, so cert
# validation is skipped for that loopback call only.
_API_PROLOGUE = r"""
$ProgressPreference = 'SilentlyContinue'
$pw = [Console]::In.ReadLine()
[Net.ServicePointManager]::SecurityProtocol = 'Tls12'
[Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
$u = 'https://localhost:35113/api'
function Start-AltaroSession {
    $b = @{ ServerAddress = 'localhost'; ServerPort = '35107'; Username = '__USER__'; Password = $pw; Domain = '__DOMAIN__' } | ConvertTo-Json -Compress
    Invoke-RestMethod -Method Post -Uri "$u/sessions/start" -Body $b -ContentType 'application/json' -TimeoutSec 60
}
function Stop-AltaroSession($t) { try { Invoke-RestMethod -Method Post -Uri "$u/sessions/end/$t" -TimeoutSec 30 | Out-Null } catch { } }
function Get-SessionError($s) {
    if ($s.ErrorAdditionalDetails -eq 'AnotherConsoleIsRegistered') { 'console_connected' } else { "$($s.ErrorCode): $($s.ErrorAdditionalDetails)" }
}
"""

_RUNNING_SCRIPT = r"""
$out = [ordered]@{ api_error = $null; jobs = @(); checkpoints = @() }
$now = Get-Date
$out.checkpoints = @(Get-VMSnapshot -VMName * -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'Altaro Temp Checkpoint*' } | ForEach-Object {
    [pscustomobject]@{ vm = $_.VMName; started = $_.CreationTime.ToString('yyyy-MM-dd HH:mm:ss'); elapsed_minutes = [int]($now - $_.CreationTime).TotalMinutes }
})
try {
    $s = Start-AltaroSession
    if (-not $s.Success) { $out.api_error = Get-SessionError $s }
    else {
        try {
            $st = Invoke-RestMethod -Uri "$u/activity/operation-status/$($s.Data)" -TimeoutSec 60
            $vms = (Invoke-RestMethod -Uri "$u/vms/list/$($s.Data)" -TimeoutSec 60).VirtualMachines
        } finally { Stop-AltaroSession $s.Data }
        $logDir = 'C:\ProgramData\Altaro\AltaroBackupProfile\Logs'
        $jh = Get-ChildItem $logDir -Filter 'Altaro.SubAgent*_JobHandler.log' -File -ErrorAction SilentlyContinue
        $ops = Get-ChildItem "$logDir\OpControllers" -Filter '*_inProgress.log' -File -ErrorAction SilentlyContinue
        $out.jobs = @(foreach ($j in $st.Statuses) {
            $vm = $null; $how = $null; $started = $null
            # Exact: the job handler logs "Concurrency Identifier for <JobId> set to <Hyper-V VM UUID>-<OP>"
            $m = $jh | Select-String -SimpleMatch "Concurrency Identifier for $($j.JobId) set to" | Select-Object -Last 1
            if ($m -and $m.Line -match 'set to ([0-9A-Fa-f-]{36})') {
                $uuid = $Matches[1]
                $v = $vms | Where-Object { $_.HypervisorVirtualMachineUuid -eq $uuid } | Select-Object -First 1
                if ($v) { $vm = $v.VirtualMachineName; $how = 'job_handler_log' }
            }
            # Fallback: per-job log named "<start>_<Op>_<uuid4>_<VM name>_<jobid4>_inProgress.log"
            $f = @($ops | Where-Object { $_.Name -like "*_$($j.JobId.Substring(0,4))_inProgress.log" })
            if ($f.Count -eq 1 -and $f[0].Name -match '^(\d{4}-\d\d-\d\d) (\d\d)-(\d\d)-(\d\d)_[^_]+_[0-9A-Fa-f]{4}_(.+)_[0-9A-Fa-f]{4}_inProgress\.log$') {
                $started = "$($Matches[1]) $($Matches[2]):$($Matches[3]):$($Matches[4])"
                if (-not $vm) { $vm = $Matches[5]; $how = 'op_log_filename' }
            }
            # Backup Health Monitor: "<start>_DataVerification_<jobid4>_inProgress.log" covers the whole backup location, no VM
            $scope = 'vm'
            if ($f.Count -eq 1 -and $f[0].Name -match '^(\d{4}-\d\d-\d\d) (\d\d)-(\d\d)-(\d\d)_DataVerification_[0-9A-Fa-f]{4}_inProgress\.log$') {
                $started = "$($Matches[1]) $($Matches[2]):$($Matches[3]):$($Matches[4])"
                $scope = 'backup_location'; $how = 'op_log_filename'
            }
            [pscustomobject]@{ vm = $vm; scope = $scope; matched_by = $how; operation = $j.Operation; sub_operation = $j.SubOperation;
                               percent = $j.Percentage; status = $j.Status; started = $started; job_id = $j.JobId }
        })
    }
} catch { $out.api_error = $_.Exception.Message }
ConvertTo-Json -InputObject $out -Depth 5 -Compress
"""

_VM_STATUS_SCRIPT = r"""
$out = [ordered]@{ api_error = $null; vms = @() }
try {
    $s = Start-AltaroSession
    if (-not $s.Success) { $out.api_error = Get-SessionError $s }
    else {
        try { $out.vms = @((Invoke-RestMethod -Uri "$u/vms/list/$($s.Data)" -TimeoutSec 60).VirtualMachines) }
        finally { Stop-AltaroSession $s.Data }
    }
} catch { $out.api_error = $_.Exception.Message }
ConvertTo-Json -InputObject $out -Depth 4 -Compress
"""

_CONSOLE_MSG = ("Altaro API refused the session because the Altaro Management Console is "
                "connected to this host. Close the console for live data.")


def _api(host: str, script: str) -> dict:
    user, password, domain = _api_creds()
    prologue = _API_PROLOGUE.replace("__USER__", user).replace("__DOMAIN__", domain)
    data = _ps(host, prologue + script, timeout=180, stdin=password)
    if not isinstance(data, dict):
        return {"api_error": "Unexpected output", "detail": str(data)[:300]}
    if data.get("api_error") == "console_connected":
        data["api_error"] = _CONSOLE_MSG
    return data


def _altaro_time(value: Optional[str]) -> Optional[str]:
    """Convert Altaro's '2026-09-24-00-49-38' to '2026-09-24 00:49:38'."""
    if not value or len(value) != 19:
        return value
    return f"{value[:10]} {value[11:13]}:{value[14:16]}:{value[17:19]}"


@mcp.tool()
def get_running_backups(host: Optional[str] = None) -> str:
    """List Altaro backups and verifications in progress on STEAMHV1/STEAMHV2, with percent complete per VM.

    Uses the Altaro REST API for live job progress and maps each job to its VM
    exactly via Altaro's job handler log (JobId to Hyper-V VM UUID), falling back
    to the per-job log filename. Also lists VMs holding an "Altaro Temp Checkpoint",
    which is how Altaro marks a VM mid-backup; that list still works when the API
    is unavailable (e.g. the Altaro console is open on the host). A checkpoint many
    hours old with no matching job suggests a stuck or orphaned backup. Jobs with
    scope "backup_location" are the scheduled Backup Health Monitor verifying the
    whole backup store, not a single VM.

    Args:
        host: STEAMHV1 or STEAMHV2. Omit to query both.
    """
    return json.dumps({h: _api(h, _RUNNING_SCRIPT) for h in _resolve_hosts(host)}, indent=2)


@mcp.tool()
def get_vm_status(host: Optional[str] = None, include_unconfigured: bool = False) -> str:
    """Get Altaro per-VM status on STEAMHV1/STEAMHV2: last backup result/time/size, next scheduled backup, offsite copy status.

    Reads the Altaro REST API (same data as the console's dashboard). Unavailable
    while the Altaro console is connected to the host.

    Args:
        host: STEAMHV1 or STEAMHV2. Omit to query both.
        include_unconfigured: Also list Hyper-V VMs not set up for Altaro backup.
    """
    result = {}
    for h in _resolve_hosts(host):
        data = _api(h, _VM_STATUS_SCRIPT)
        vms = []
        for v in data.get("vms") or []:
            if not (v.get("Configured") or include_unconfigured):
                continue
            vms.append({
                "vm": v.get("VirtualMachineName"),
                "configured": v.get("Configured"),
                "last_backup_result": v.get("LastBackupResult"),
                "last_backup_time": _altaro_time(v.get("LastBackupTime")),
                "last_backup_minutes": round((v.get("LastBackupDuration") or 0) / 60, 1),
                "last_backup_gb_compressed": round((v.get("LastBackupTransferSizeCompressed") or 0) / 1e9, 2),
                "next_backup_time": _altaro_time(v.get("NextBackupTime")),
                "last_offsite_result": v.get("LastOffsiteCopyResult"),
                "last_offsite_time": _altaro_time(v.get("LastOffsiteCopyTime")),
                "next_offsite_time": _altaro_time(v.get("NextOffsiteCopyTime")),
            })
        result[h] = {"api_error": data.get("api_error"), "vms": sorted(vms, key=lambda x: x["vm"] or "")}
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
