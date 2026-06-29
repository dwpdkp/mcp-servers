# Proxmox MCP

[![PyPI version](https://img.shields.io/pypi/v/proxmox-mcp)](https://pypi.org/project/proxmox-mcp/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/proxmox-mcp)](https://pypi.org/project/proxmox-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An MCP (Model Context Protocol) server for managing Proxmox VE infrastructure through AI agents. Control your virtual machines, containers, storage, and snapshots via natural language.

> **WARNING: This project is under active development and is NOT intended for production use.**
> This MCP server can perform destructive operations on your Proxmox infrastructure, including deleting virtual machines and containers. **Data loss is possible.** Use at your own risk. Always test in a non-production environment first.

---

## Features

### Discovery
- **`list_nodes`** — Cluster node overview
- **`list_vms`** / **`list_lxc_containers`** — Instance inventory per node
- **`list_storage`** / **`list_storage_content`** — Storage pools, ISOs, and templates
- **`get_instance_config`** — Full guest configuration
- **`get_lxc_interfaces`** — Container network interfaces
- **`get_resource_usage`** — Performance metrics (CPU, memory, network, disk)

### Management
- **`power_control`** — Start, stop, shutdown, reboot VMs and containers
- **`create_lxc`** / **`create_vm`** — Provision new infrastructure
- **`execute_lxc_command`** — Run shell commands inside containers
- **`set_vm_cloudinit`** — Configure cloud-init (user, SSH keys, network)

### Protection
- **`create_snapshot`** / **`rollback_snapshot`** / **`list_snapshots`** — Snapshot management
- **`delete_instance`** — Permanently delete a VM or container (disabled by default, requires double confirmation)
- **`get_task_status`** / **`get_task_log`** — Monitor background operations
- **`get_mcp_logs`** — Server-side log inspection

---

## Installation

### From PyPI

```bash
pip install proxmox-mcp
```

### From source

```bash
git clone https://github.com/josky-com/proxmox-mcp.git
cd proxmox-mcp
./setup.sh
```

## Quick Start

```bash
# 1. Configure credentials
cp .env.example .env
nano .env    # Set your Proxmox URL, token name, and token value

# 2. Test connectivity
python scripts/test_connection.py

# 3. Run the server
python -m proxmox_mcp
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `PROXMOX_URL` | Proxmox API base URL (e.g., `https://192.168.1.100:8006/api2/json`) | — |
| `PROXMOX_TOKEN_NAME` | API token ID (e.g., `root@pam!mcp-token`) | — |
| `PROXMOX_TOKEN_VALUE` | API token secret | — |
| `PROXMOX_VERIFY_SSL` | Verify SSL certificates | `true` |
| `PROXMOX_ALLOW_DANGER` | Enable critical/destructive tools like `delete_instance` | `false` |

---

## AI Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "/absolute/path/to/proxmox-mcp/.venv/bin/python3",
      "args": ["-m", "proxmox_mcp"]
    }
  }
}
```

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "/absolute/path/to/proxmox-mcp/.venv/bin/python3",
      "args": ["-m", "proxmox_mcp"]
    }
  }
}
```

---

## Security

### Safety Tiers

All tools are classified into safety tiers:

| Tier | Behavior | Examples |
|---|---|---|
| **Safe** | Executes without confirmation | `list_nodes`, `list_vms`, `get_instance_config` |
| **Restricted** | Requires explicit user confirmation (`confirmed=true`) | `power_control`, `create_lxc`, `create_vm`, `execute_lxc_command` |
| **Critical** | Blocked unless `PROXMOX_ALLOW_DANGER=true` + confirmation | `delete_instance` |

### Contract Validation

Every Proxmox API response is validated against Pydantic schemas. If the Proxmox API returns unexpected data (e.g., after a version upgrade), the server returns an `API_CONTRACT_DIVERGENCE` error instead of silently passing bad data.

### Input Sanitization

All identifiers (node names, storage names, snapshot names) are validated against strict patterns. VMIDs must be positive integers. Shell commands are parsed through `shlex` to prevent injection.

---

## Project Structure

```
proxmox-mcp/
├── src/proxmox_mcp/
│   ├── __main__.py           # Entry point (python -m proxmox_mcp)
│   ├── server.py             # FastMCP instance and tool registration
│   ├── config.py             # Environment variables, client init
│   ├── models.py             # Pydantic response schemas
│   ├── api/
│   │   ├── client.py         # Async HTTP client for Proxmox API
│   │   └── permissions.py    # Permission mapping for 403 diagnostics
│   ├── core/
│   │   ├── logger.py         # Rotating file logger with redaction
│   │   ├── safety.py         # Safety policy enforcement
│   │   └── sanitization.py   # Input validation
│   └── tools/
│       ├── __init__.py       # safety_checked decorator, shared helpers
│       ├── discovery.py      # 10 tools: nodes, VMs, containers, storage, config, logs
│       ├── lifecycle.py      # 4 tools: power, create LXC/VM, delete
│       ├── snapshots.py      # 3 tools: list, create, rollback
│       ├── cloudinit.py      # 1 tool: cloud-init configuration
│       ├── exec.py           # 1 tool: execute commands in containers
│       └── metrics.py        # 1 tool: resource usage metrics
├── docs/
│   ├── api_manifest.md       # API contract registry (20 tools)
│   ├── architecture.md       # System design overview
│   └── requirements.md       # Functional requirements
├── scripts/
│   ├── test_connection.py    # Manual connectivity testing
│   └── admin_dashboard.py    # Live infrastructure overview
├── tests/                    # pytest suite (152 tests, fully offline)
├── pyproject.toml            # Build config and dependencies
├── setup.sh                  # Automated setup script
└── .env.example              # Credential template
```

---

## Development

```bash
pip install -e ".[dev]"    # Install with test dependencies
pytest -v                  # Run all 152 tests (no Proxmox needed)
```

All tests run fully offline — Proxmox API calls are mocked at the HTTP layer.

## Tech Stack

- **Python 3.10+**
- **MCP SDK** (`mcp`) — FastMCP server framework
- **Pydantic** — Response validation and contract enforcement
- **httpx** — Async HTTP client
- **pytest** + **pytest-httpx** — Testing with HTTP mocking
- **Transport** — stdio (JSON-RPC)

---

## Trademark Notice

"Proxmox" and the Proxmox logo are registered trademarks of **Proxmox Server Solutions GmbH** (Vienna, Austria). This project is not affiliated with, endorsed by, or sponsored by Proxmox Server Solutions GmbH. This is an independent, third-party tool that integrates with the Proxmox VE API.

---

## License

This project is licensed under the [MIT License](LICENSE).
