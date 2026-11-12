# Proxmox MCP Server

Python-based MCP server for managing Proxmox VE infrastructure.

## Quick Reference

- **Entry point**: `src/proxmox_mcp/server.py` (FastMCP, stdio transport)
- **Config**: `src/proxmox_mcp/config.py` (env vars, client init, safety policy)
- **Data contracts**: `src/proxmox_mcp/models.py` (23 Pydantic models)
- **HTTP client**: `src/proxmox_mcp/api/client.py` (httpx async, `fetch_and_validate`)
- **Permissions**: `src/proxmox_mcp/api/permissions.py` (30 endpoint-to-privilege rules)
- **Safety**: `src/proxmox_mcp/core/safety.py` (`check_safety` with 3 tiers)
- **Sanitization**: `src/proxmox_mcp/core/sanitization.py` (`sanitize_identifier`, `sanitize_vmid`)
- **Logging**: `src/proxmox_mcp/core/logger.py` (rotating file log with sensitive data redaction)
- **Tool modules**: `src/proxmox_mcp/tools/` (discovery, lifecycle, snapshots, cloudinit, exec, metrics)
- **API registry**: `docs/api_manifest.md`

## Development

```bash
./setup.sh                          # First-time setup (pip install -e .)
python -m proxmox_mcp               # Run the MCP server
python scripts/test_connection.py   # Verify Proxmox connectivity
python scripts/admin_dashboard.py   # Live infrastructure overview
pytest                              # Run tests
```

## Key Patterns

- **Tool registration**: Decorate handlers with `@mcp.tool()` in the appropriate `tools/` module. Import the module in `server.py` to trigger registration.
- **Safety decorator**: Apply `@safety_checked` below `@mcp.tool()` to enforce safety tiers and input sanitization automatically.
- **Contract validation**: Every tool's Proxmox API response is validated via `client.fetch_and_validate(endpoint, ModelClass)`. Mismatches return `API_CONTRACT_DIVERGENCE`.
- **Safety tiers**: safe (no confirmation) -> restricted (requires `confirmed=true`) -> critical (requires `PROXMOX_ALLOW_DANGER=true` + confirmation).
- **Input sanitization**: All identifiers go through `sanitize_identifier()`, VMIDs through `sanitize_vmid()`. Shell commands are parsed via `shlex`.
- **Sensitive data**: Passwords, tokens, SSH keys, and network configs are redacted in logs. Never log raw values.

## Git Workflow

Use feature branches with PRs for every unit of work:

1. `git checkout -b feat/<topic>`: branch off main before starting
2. Work, then `/commit` when done
3. Push and open a PR: `git push -u origin HEAD && gh pr create`
4. Review the diff locally (`git diff main`) or on GitHub
5. Merge: `gh pr merge --squash --delete-branch`
6. Return to main: `git checkout main && git pull`

One branch per session/feature. Squash merge keeps main history clean.

## Adding a New Tool

1. Register the Proxmox endpoint and expected fields in `docs/api_manifest.md`.
2. Create a corresponding Pydantic model in `src/proxmox_mcp/models.py`.
3. Add an `@mcp.tool()` decorated handler in the appropriate `src/proxmox_mcp/tools/` module. Apply `@safety_checked` for safety and sanitization.
4. Import the module in `src/proxmox_mcp/server.py` if it's a new file.
