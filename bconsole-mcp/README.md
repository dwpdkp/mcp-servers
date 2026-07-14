# bconsole-mcp

MCP server for real-time Bacula Director access via `bconsole` over SSH. Unlike the Bacularis REST API (which reads the catalog and shows 0 bytes for running jobs), this server runs `status director` directly in the Director's memory, giving accurate real-time byte counts for running jobs.

## Requirements

- Python 3.10+
- SSH access to the Bacula Director host with `BatchMode=yes` key-based auth (no password prompt)
- Passwordless `sudo bconsole` (and `sudo mysqlcheck`, `sudo dbcheck` for maintenance tools) on that host

## Configuration

Connection details are hardcoded at the top of `main.py` rather than read from environment variables:

| Constant | Value | Description |
|---|---|---|
| `BACULA_HOST` | `sra-bacula-01` | SSH host running the Bacula Director |
| `BCONSOLE_CMD` | `sudo bconsole` | Command piped commands over stdin |
| `STORAGE_PATHS` | `{"File1": "/mnt/nas/bacula", "PlasticFile1": "/mnt/nas/plastic-bacula"}` | Storage device archive paths |
| `MEDIATYPE_STORAGE` | `{"File1": "File1", "PlasticFile": "PlasticFile1"}` | MediaType → storage name mapping |

## Claude Code `.mcp.json` entry

```json
"bconsole": {
  "command": "/path/to/uv",
  "args": [
    "run",
    "--with", "mcp",
    "/path/to/bconsole-mcp/main.py"
  ]
}
```

## Tools

Mutating tools require an explicit `confirm=true` argument. Omitting it (or passing `false`) raises a `ValueError` before any command reaches bconsole. See [Security](#security) for the full gating reference.

### Status & Monitoring

| Tool | Description |
|---|---|
| `status_director` | Real-time Director status (running/scheduled/terminated jobs) parsed from `status dir`: accurate live byte counts, unlike Bacularis |
| `list_running_jobs` | Just the running-jobs section of `status_director`, with live files/bytes transferred |
| `list_purged_volumes` | All volumes with `Purged` status across all pools: ready to recycle |

### Job Control

| Tool | Description |
|---|---|
| `run_job` | Start a Bacula backup job immediately by exact job name, optional level/client override; requires `confirm=true` |
| `cancel_job` | Cancel a running or queued job by job ID; requires `confirm=true`; verify the job is actually a zombie with `list_running_jobs` first |

### Catalog Maintenance

| Tool | Description |
|---|---|
| `purge_volume` | Purge all job records for a volume from the catalog, marking it recyclable (does not touch the physical file); requires `confirm=true` |
| `prune_client` | Prune expired job/file records for one client: safe, only removes already-expired retention data, no confirm gate |
| `prune_all` | Prune expired records for all clients and volumes (full catalog sweep); requires `confirm=true` |
| `optimize_catalog` | Run `mysqlcheck --optimize` on the Bacula catalog tables (File, Path, Job, etc.) to reclaim space and rebuild indexes |
| `dbcheck` | Run Bacula's built-in catalog consistency checker in batch mode (safe fixes only, no interactive prompts) |

### Raw Access

| Tool | Description |
|---|---|
| `console` | Run a raw bconsole command: restricted to a fixed allowlist of read-only verbs (see [Security](#security)) |

## Security

### Confirmation gates

`run_job`, `cancel_job`, `purge_volume`, and `prune_all` require an explicit `confirm: bool = True` argument. Calling one without `confirm=true` raises a `ValueError` describing the action and asking the caller to get explicit user approval first. No command is sent to bconsole in that case.

`prune_client` is deliberately **not** confirm-gated: it only removes catalog records that have already exceeded their retention period, never active job data or physical files.

### `console()` verb allowlist

`console()` is a read-only escape hatch for bconsole queries not covered by a dedicated tool. It only permits these verbs: `status`, `list`, `llist`, `show`, `help`, `version`, `.api`, `messages`, `query`, `estimate`. Any other verb (`run`, `purge`, `prune`, `cancel`, `delete`, `label`, `mount`, `sql`, etc.) is rejected with a message pointing to the dedicated, confirm-gated tool instead. This closes the loophole where an agent could otherwise bypass every confirm gate above by calling `console("run job=...")` or `console("purge volume=...")` directly.

### Command-injection protection

`_run()` joins multiple bconsole commands with `\n` and pipes them to bconsole's interactive REPL over SSH stdin. A newline embedded in a caller-controlled value (job name, volume name, client name) would otherwise be interpreted as the start of a second, attacker-chosen bconsole command. Every value that reaches `_run()` (`job_name`, `client`, `volume_name`, `client_name`, and the raw `command` passed to `console()`) is checked by `_reject_injection()`, which rejects any value that is empty or contains `\n`/`\r`, before it's ever included in a command string.

## Related Bacula tooling

- **bacularis-mcp**: read-only REST API wrapper (job/client/volume/pool/storage queries); use this for anything that doesn't need live in-memory Director state
- `Tools/Admin`: `bacula_job_checker`, `bacula_full_backup_checker` (see top-level `Dev-Stuff/CLAUDE.md`)

## License

MIT

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-07-14 | Doug Pearson | Initial creation: documents confirm-gate security hardening (run_job, cancel_job, purge_volume, prune_all), the console() read-only verb allowlist, and the bconsole stdin command-injection fix |
