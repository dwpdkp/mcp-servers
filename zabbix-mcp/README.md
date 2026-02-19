# zabbix-mcp

MCP server that exposes the Zabbix monitoring system as a set of tools for AI assistants.

- **Package**: [zabbix-mcp on PyPI](https://pypi.org/project/zabbix-mcp/)
- **Source**: [GitLab - radek-sprta/zabbix-mcp](https://gitlab.com/radek-sprta/zabbix-mcp)
- **Version**: 0.7.0
- **License**: MIT
- **Python**: >= 3.13

## Installation

No local install needed. The server runs via `uvx`:

```bash
uvx zabbix-mcp
```

Installed automatically to: `~/.local/share/uv/tools/zabbix-mcp/`

## Configuration

### MCP JSON Config (in `.mcp.json`)

```json
{
  "mcpServers": {
    "zabbix": {
      "command": "~/.local/bin/uvx",
      "args": ["zabbix-mcp"],
      "env": {
        "ZABBIX_URL": "http://your-zabbix-server/zabbix/api_jsonrpc.php",
        "ZABBIX_TOKEN": "<your-zabbix-api-token>"
      }
    }
  }
}
```

Add this to your project's `.mcp.json` file.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZABBIX_URL` | Yes | - | Full URL to the Zabbix JSON-RPC API endpoint |
| `ZABBIX_TOKEN` | Yes | - | Zabbix API authentication token (Bearer token) |
| `ZABBIX_VERIFY_SSL` | No | `true` | Verify TLS certificates; set `false` for self-signed certs |
| `ZABBIX_TIMEOUT` | No | `30` | HTTP request timeout in seconds |
| `ZABBIX_DEBUG` | No | `false` | Enable debug logging |

## Authentication

The server supports two authentication methods:

1. **API Token** (Zabbix 5.4+): Set `ZABBIX_TOKEN` with an API token generated in the Zabbix frontend
2. **User/Password**: Set `ZABBIX_USER` and `ZABBIX_PASSWORD` instead of `ZABBIX_TOKEN` — creates a session that auto-reconnects on expiry

User/password auth is recommended for long-running MCP sessions as it handles session expiry gracefully.

## Available Tools (46)

### Hosts (4)

| Tool | Description |
|------|-------------|
| `host_get` | Retrieve hosts with filtering |
| `host_create` | Create a new host |
| `host_update` | Update an existing host |
| `host_delete` | Delete a host |

### Triggers (4)

| Tool | Description |
|------|-------------|
| `trigger_get` | Retrieve triggers with filtering |
| `trigger_create` | Create a new trigger |
| `trigger_update` | Update an existing trigger |
| `trigger_delete` | Delete a trigger |

### Items (5)

| Tool | Description |
|------|-------------|
| `item_get` | Retrieve items with filtering |
| `item_create` | Create a new item |
| `item_update` | Update an existing item |
| `item_delete` | Delete an item |
| `itemprototype_get` | Retrieve item prototypes (LLD) |

### Templates (4)

| Tool | Description |
|------|-------------|
| `template_get` | Retrieve templates with filtering |
| `template_create` | Create a new template |
| `template_update` | Update an existing template |
| `template_delete` | Delete a template |

### Events (2)

| Tool | Description |
|------|-------------|
| `event_get` | Retrieve events with filtering |
| `event_acknowledge` | Acknowledge an event |

### Maintenance (4)

| Tool | Description |
|------|-------------|
| `maintenance_get` | Retrieve maintenance periods |
| `maintenance_create` | Create a maintenance window |
| `maintenance_update` | Update a maintenance window |
| `maintenance_delete` | Delete a maintenance window |

### Users & Macros (8)

| Tool | Description |
|------|-------------|
| `user_get` | Retrieve users with filtering |
| `user_create` | Create a new user |
| `user_update` | Update an existing user |
| `user_delete` | Delete a user |
| `usermacro_get` | Retrieve user macros |
| `usermacro_create` | Create a user macro |
| `usermacro_update` | Update a user macro |
| `usermacro_delete` | Delete a user macro |

### Proxies (4)

| Tool | Description |
|------|-------------|
| `proxy_get` | Retrieve proxies with filtering |
| `proxy_create` | Create a new proxy |
| `proxy_update` | Update an existing proxy |
| `proxy_delete` | Delete a proxy |

### Actions (1)

| Tool | Description |
|------|-------------|
| `action_get` | Retrieve actions with filtering |

### Configuration (2)

| Tool | Description |
|------|-------------|
| `configuration_export` | Export Zabbix configuration |
| `configuration_import` | Import Zabbix configuration |

### Discovery (2)

| Tool | Description |
|------|-------------|
| `discoveryrule_get` | Retrieve low-level discovery rules |
| `drule_get` | Retrieve network discovery rules |

### Graphs (1)

| Tool | Description |
|------|-------------|
| `graph_get` | Retrieve graphs with filtering |

### Media Types (1)

| Tool | Description |
|------|-------------|
| `mediatype_get` | Retrieve media types |

### Scripts (2)

| Tool | Description |
|------|-------------|
| `script_get` | Retrieve scripts |
| `script_execute` | Execute a script on a host |

### Services & SLA (2)

| Tool | Description |
|------|-------------|
| `service_get` | Retrieve services |
| `sla_get` | Retrieve SLA definitions |

## Upgrading

```bash
# Upgrade to latest version
uvx upgrade zabbix-mcp

# Or reinstall fresh
uvx install --force zabbix-mcp
```

Check installed version:
```bash
ls ~/.local/share/uv/tools/zabbix-mcp/lib/python3.*/site-packages/zabbix_mcp-*.dist-info/
```

## Dependencies

Automatically installed by uvx:

- `httpx >= 0.28.1` - Async HTTP client
- `mcp[cli] >= 1.3.0` - MCP SDK
- `pydantic >= 2.10.6` - Data validation
- `pydantic-settings >= 2.8.2` - Settings management from env vars
