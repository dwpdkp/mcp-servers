# Bacularis MCP Server

Read-only MCP server for querying Bacula/Bareos backup infrastructure via the [Bacularis](https://bacularis.app/) REST API.

## Setup

```bash
cd bacularis-mcp
uv venv
uv pip install mcp httpx
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `BACULARIS_URL` | Yes | Bacularis base URL (e.g., `http://10.100.0.42:9097`) |
| `BACULARIS_USER` | Yes | Bacularis API username |
| `BACULARIS_PASSWORD` | Yes | Bacularis API password |

**Credential:** Enigma entry `22178` (mcp-service account on SRA-BACULA-01).

## MCP Client Configuration

Add to `.mcp.json`:

```json
"bacularis": {
  "command": "/path/to/bacularis-mcp/.venv/bin/python",
  "args": ["/path/to/bacularis-mcp/main.py"],
  "env": {
    "BACULARIS_URL": "http://your-bacularis-server:9097",
    "BACULARIS_USER": "mcp-service",
    "BACULARIS_PASSWORD": "see enigma 22178"
  }
}
```

## Available Tools (13)

### Jobs

| Tool | Description |
|------|-------------|
| `get_jobs` | List jobs with filters (limit, name, status, client, level) |
| `get_job` | Get details for a specific job by ID |
| `get_job_files` | List files in a job backup |
| `get_job_totals` | Total bytes and files across all jobs |
| `get_job_log` | Actual job log/termination summary (`/joblog/{id}`) — fixed 2026-07-23, previously called `/jobs/{id}/show` and returned the static job-resource config instead of the real log |

### Clients

| Tool | Description |
|------|-------------|
| `get_clients` | List all backup clients |
| `get_client` | Get details for a specific client |
| `get_client_jobs` | List jobs for a specific client |

### Volumes & Pools

| Tool | Description |
|------|-------------|
| `get_volumes` | List all volumes |
| `get_pools` | List all pools |
| `get_pool_volumes` | List volumes in a specific pool |

### Storage

| Tool | Description |
|------|-------------|
| `get_storages` | List all storage daemons |
| `get_storage_status` | Get storage daemon status |

## Bacularis API

- **API Version:** v3
- **Auth:** HTTP Basic
- **Docs:** https://bacularis.app/api/ (Swagger/OpenAPI)
- **Server:** SRA-BACULA-01 (10.100.0.42:9097)

## Notes

- All operations are read-only — no job execution or configuration changes
- Works with both Bacula Community and Bareos (Bacularis supports both)
- Self-signed TLS certificates are accepted (verify=False)
- **This server reads the catalog (MariaDB), not live Director state.** A running job's catalog row (`jobbytes`, `volsessionid`, etc.) is only written periodically and finalized at completion — `get_job`/`get_jobs` can show 0 bytes for a job that is genuinely transferring data. For live status of running/queued jobs, use the companion **bconsole-mcp** server's `status_director()` or `list_running_jobs()`, which read the Director's in-memory state instead. Never decide a job is a stuck zombie from this server's data alone before cancelling it.

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-19 | Doug Pearson | Initial creation |
| 2026-07-23 | Doug Pearson | Fixed `get_job_log` — was calling `/jobs/{id}/show` (static config dump) instead of `/joblog/{id}` (real log/termination summary). Added explicit staleness warnings to `get_job`/`get_jobs` docstrings and README after a bad zombie-job cancel caused by trusting a stale catalog snapshot over live Director state. |
