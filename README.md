# MCP-Servers

A collection of Model Context Protocol (MCP) server implementations — some authored in-house, some vendored third-party frameworks/packages — used for AI-assistant integration with home lab and Steamroller Studios infrastructure.

## Overview

| Server | Description | Origin | Security model |
|---|---|---|---|
| **[proxmox-mcp](./proxmox-mcp/README.md)** | Proxmox VE management — nodes, VMs/LXCs, storage, snapshots, cloud-init, exec | In-house | Safety tiers (safe/restricted/critical); critical tools need `PROXMOX_ALLOW_DANGER=true` + confirmation; TLS fail-closed (`PROXMOX_ALLOW_INSECURE_TLS`) |
| **[unifi-mcp](./unifi-mcp/README.md)** | UniFi local controller — clients, devices, firewall policies, port forwards, WLANs, VLANs | In-house | Per-tool `confirm=true` gates; extra gates for WiFi security downgrade and internet-facing port forwards; RFC1918/port-range input validation |
| **[zabbix-mcp](./zabbix-mcp/README.md)** | Zabbix monitoring — hosts, templates, triggers, items, users, scripts, config import/export | Fork of [mhajder/zabbix-mcp](https://github.com/mhajder/zabbix-mcp) | `READ_ONLY_MODE` toggle (upstream) plus fork-specific `confirm=true` gates on destructive/privilege-changing tools, incl. dual-flag gate for granting super-admin |
| **[bconsole-mcp](./bconsole-mcp/README.md)** | Real-time Bacula Director access via `bconsole` over SSH (accurate live job byte counts) | In-house | `confirm=true` gates on job/catalog mutations; `console()` restricted to a read-only verb allowlist; stdin command-injection protection |
| **[bacularis-mcp](./bacularis-mcp/README.md)** | Read-only Bacula/Bareos backup reporting via the Bacularis REST API | In-house | Genuinely read-only — no gating needed |
| **[unraid-mcp](./unraid-mcp/README.md)** | Unraid GraphQL API — system, array, docker, VMs, plugins, notifications, live telemetry | Third-party ([jmagar/unraid-mcp](https://github.com/jmagar/unraid-mcp)) | Confirm-gated destructive subactions built in upstream; not modified here |
| **[mcp_youtube_dlp](./mcp_youtube_dlp/README.md)** | YouTube video/audio download via yt-dlp | In-house | Personal download tool; no destructive/shared-infrastructure operations |
| **[weather](./weather/README.md)** | Public NWS weather alerts and forecasts | In-house | Public, unauthenticated, read-only API wrapper |
| **[fastmcp](./fastmcp/README.md)** | Vendored MCP server/client framework used by several of the above | Third-party ([jlowin/fastmcp](https://github.com/jlowin/fastmcp)) | Framework, not a running server |
| **MCP-Builder-Stuff** | Vendored MCP Python SDK reference | Third-party ([modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)) | Framework, not a running server |

## Security posture

Several of the in-house servers (proxmox-mcp, unifi-mcp, zabbix-mcp, bconsole-mcp) went through a security-hardening pass driven by a CISSP-agent review. The consistent principle applied: **make mutating/destructive tools safe by default in code, not by disabling them.** Rather than shipping a global read-only toggle as the only safeguard, every destructive or high-impact tool call now requires the caller to pass an explicit `confirm=true` (or, for the highest-risk actions, two independent flags — see each server's README for its exact gate names). A tool call without confirmation raises an error before any request reaches the underlying API/SSH/subprocess layer — nothing is silently blocked, but nothing destructive runs by accident either.

Where relevant, additional hardening was layered on top of confirmation gates:

- **Input validation** — RFC1918/port-range checks on unifi-mcp port forwards; strict ObjectID pattern checks on all UniFi `_id` params; VMID/identifier sanitization in proxmox-mcp
- **Fail-closed TLS** — proxmox-mcp requires a second explicit opt-in (`PROXMOX_ALLOW_INSECURE_TLS`) to actually disable certificate verification, rather than silently downgrading on `PROXMOX_VERIFY_SSL=false`
- **Command-injection protection** — bconsole-mcp rejects any caller-controlled value containing a newline before it can reach bconsole's SSH-piped stdin REPL
- **Escape-hatch allowlisting** — bconsole-mcp's raw `console()` passthrough is restricted to read-only verbs, closing the loophole where it could otherwise bypass every other tool's confirm gate
- **Privilege-escalation dual-gating** — zabbix-mcp's `user_update` and proxmox-mcp's `delete_instance` require a second, distinct flag beyond `confirm=true` for their highest-risk case (granting Zabbix super-admin; deleting a VM/container)

See each server's README for its full tool list and exact gate names/parameters.

## What is MCP?

The Model Context Protocol (MCP) is an open standard created by Anthropic that provides a universal way to connect AI assistants to external data sources and tools. It uses JSON-RPC 2.0 for communication and supports multiple transport protocols (stdio, HTTP, SSE).

For detailed technical background, see [MCP-web-research.md](./MCP-web-research.md).

## Repository

```bash
git clone git@github.com:dwpdkp/mcp-servers.git
cd mcp-servers
```

Each in-house server directory has its own README with setup, environment variables, `.mcp.json` client config, and a full tool reference — start there for any given server. `fastmcp/` and `MCP-Builder-Stuff/` are vendored third-party dependencies, not standalone servers to run directly.

## Development

Most servers use `uv` as the package manager.

```bash
cd <server-dir>
uv sync
uv run pytest    # where a test suite exists (proxmox-mcp, unifi-mcp, zabbix-mcp)
```

See [CLAUDE.md](./CLAUDE.md) for repo-wide development guidelines.

## Documentation

- [CLAUDE.md](./CLAUDE.md) — development guidelines for Claude Code working in this repo
- [MCP-web-research.md](./MCP-web-research.md) — comprehensive MCP technical reference
- Per-server `README.md` — setup, tools, and security model for each server

## License

- **proxmox-mcp**, **unifi-mcp**, **bconsole-mcp**, **bacularis-mcp**, **weather** — MIT
- **zabbix-mcp** — MIT (fork of mhajder/zabbix-mcp, also MIT)
- **unraid-mcp** — see upstream project
- **mcp_youtube_dlp** — GPL-2.0
- **fastmcp**, **MCP-Builder-Stuff** — see vendored project license

## Resources

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://gofastmcp.com/)

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-07-14 | Doug Pearson | Full rewrite: added proxmox-mcp, zabbix-mcp, bconsole-mcp, unraid-mcp to the overview (previously missing); replaced placeholder clone URL with actual origin; added Security posture section summarizing the confirm-gate hardening pass across proxmox-mcp/unifi-mcp/zabbix-mcp/bconsole-mcp |
