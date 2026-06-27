# unifi-mcp

MCP server for the UniFi local controller API. Provides read and write access to network clients, devices, firewall policies, port forwards, VLANs, and monitoring data via X-API-KEY authentication (UniFi OS 3+ / UCG / UDM).

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- UniFi OS 3+ gateway (Cloud Gateway Ultra, UDM, UDM Pro, etc.)
- An API key generated in the UniFi Network UI

## Configuration

Set these environment variables (or use the `.mcp.json` `env` block):

| Variable | Required | Default | Description |
|---|---|---|---|
| `UNIFI_URL` | Yes | `https://10.0.1.1` | Base URL of the gateway |
| `UNIFI_API_KEY` | Yes | — | API key from UniFi Network → Settings → System → API |
| `UNIFI_SITE` | No | `default` | Site name (leave as `default` for single-site installs) |
| `UNIFI_VERIFY_SSL` | No | `false` | Set to `true` to enforce SSL certificate validation |

## Claude Code `.mcp.json` entry

```json
"unifi": {
  "command": "/path/to/uv",
  "args": [
    "run",
    "--with", "fastmcp==2.14.5",
    "--with", "httpx",
    "/path/to/unifi-mcp/main.py"
  ],
  "env": {
    "UNIFI_URL": "https://10.0.1.1",
    "UNIFI_API_KEY": "your-api-key-here",
    "UNIFI_VERIFY_SSL": "false",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  }
}
```

## Tools

### Clients & Devices

| Tool | Description |
|---|---|
| `list_clients` | Active (or all) network clients with MAC, IP, hostname, SSID |
| `list_devices` | All adopted UniFi devices (APs, switches, gateway) |
| `get_device_stats` | Per-device CPU, memory, uptime, satisfaction, and per-port TX/RX stats |
| `get_client_history` | All clients ever seen — last IP, last network, device type |
| `get_system_info` | Gateway firmware version, hostname, uptime, timezone |

### DHCP

| Tool | Description |
|---|---|
| `list_dhcp_reservations` | All fixed-IP (reserved) DHCP assignments |
| `add_dhcp_reservation` | Create or update a DHCP reservation by MAC address |
| `remove_dhcp_reservation` | Remove a DHCP reservation by MAC address |

### WiFi

| Tool | Description |
|---|---|
| `list_wlans` | All SSIDs with security type and VLAN |
| `list_rogue_aps` | Nearby APs detected by your APs; `rogue_only=True` for flagged ones only |

### Firewall

| Tool | Description |
|---|---|
| `list_firewall_policies` | Zone-based firewall rules; filter by `include_predefined` and `action_filter` |
| `get_firewall_policy` | Fetch a single policy by `_id` (returns full raw object) |
| `update_firewall_policy` | Update an existing policy by `_id` — name, action, enabled, logging, protocol, ip_version |
| `set_firewall_policy_logging` | Enable or disable logging on a specific policy |
| `set_block_rules_logging` | Bulk enable/disable logging on all custom BLOCK rules |
| `list_firewall_groups` | Address and port groups used as rule sources/destinations |
| `list_port_forwards` | All WAN → LAN NAT / port forward rules |
| `update_port_forward` | Update an existing port forward by `_id` — any field (proto, fwd IP, port, enabled, log, src) |

### Network Configuration

| Tool | Description |
|---|---|
| `list_networks` | All VLANs and subnets with purpose, DHCP ranges, and VLAN IDs |
| `list_switch_port_profiles` | Switch port profiles (VLAN trunk and native VLAN assignments) |

### Site

| Tool | Description |
|---|---|
| `get_site_stats` | Site health summary: WAN, LAN, WLAN, VPN subsystem status |

## API notes

- Uses the `X-API-KEY` header (UniFi OS 3+). Cookie-based session auth is not used.
- Firewall policies use the v2 API (`/proxy/network/v2/api/site/{site}/firewall-policies`). The legacy `/rest/firewallrule` endpoint returns empty on zone-based firewall setups.
- The `list_firewall_policies` tool returns custom rules only by default (`include_predefined=False`). Pass `include_predefined=True` to see all 100+ built-in rules.
- Event/alarm log endpoints return 404 on current UCG firmware — not supported.
- Bandwidth report endpoints exist but return stub data only — not implemented.
