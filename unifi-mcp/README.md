# unifi-mcp

MCP server for the UniFi local controller API. Provides read and write access to network clients, devices, firewall policies, port forwards, VLANs, and monitoring data via X-API-KEY authentication (UniFi OS 3+ / UCG / UDM).

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- UniFi OS 3+ gateway (Cloud Gateway Ultra, UDM, UDM Pro, etc.)
- An API key generated in the UniFi Network UI (Settings → System → API)

## Configuration

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
| `list_clients` | Active (or all) network clients — MAC, IP, hostname, SSID, uptime |
| `list_devices` | All adopted UniFi devices (APs, switches, gateway) via integrations API |
| `get_device_stats` | Per-device CPU, memory, uptime, satisfaction score, and per-port TX/RX byte counts |
| `get_client_history` | All clients ever seen — last IP, last network, device type, blocked status |
| `get_system_info` | Gateway firmware version, build, hostname, uptime, timezone |
| `block_client` | Block a client from the network by MAC address (disconnects immediately) |
| `unblock_client` | Unblock a previously blocked client by MAC address |
| `restart_device` | Reboot an AP, switch, or gateway by MAC address (**disruptive — causes ~60s outage**) |

### DHCP

| Tool | Description |
|---|---|
| `list_dhcp_reservations` | All fixed-IP (reserved) DHCP assignments |
| `add_dhcp_reservation` | Create or update a DHCP reservation by MAC address |
| `remove_dhcp_reservation` | Remove a DHCP reservation by MAC address |

### WiFi

| Tool | Description |
|---|---|
| `list_wlans` | All SSIDs — name, enabled state, security type, VLAN |
| `update_wlan` | Update a WiFi network by `_id` — name, enabled, passphrase, security mode, VLAN |
| `list_rogue_aps` | Nearby APs detected by your APs; `rogue_only=True` for UniFi-flagged rogues only |

### Firewall

| Tool | Description |
|---|---|
| `list_firewall_policies` | Zone-based firewall rules; filter by `include_predefined` and `action_filter` (`ALLOW`/`BLOCK`) |
| `get_firewall_policy` | Fetch a single policy by `_id` (returns full raw object for inspection before editing) |
| `update_firewall_policy` | Update a policy by `_id` — name, action, enabled, logging, protocol, ip_version |
| `set_firewall_policy_logging` | Enable or disable logging on a specific policy by `_id` |
| `set_block_rules_logging` | Bulk enable/disable logging on all custom BLOCK rules at once |
| `list_firewall_groups` | Address and port groups used as rule sources/destinations |
| `update_firewall_group` | Replace the full member list (IPs/CIDRs) of an address group by `_id` |
| `list_port_forwards` | All WAN → LAN NAT / port forward rules |
| `create_port_forward` | Create a new port forward rule |
| `update_port_forward` | Update an existing port forward by `_id` — proto, fwd IP, ports, enabled, src, log |
| `delete_port_forward` | Delete a port forward rule by `_id` (permanent) |

### Network Configuration

| Tool | Description |
|---|---|
| `list_networks` | All VLANs and subnets — name, purpose, subnet, VLAN ID, DHCP range |
| `list_switch_port_profiles` | Switch port profiles — native VLAN, trunk mode, PoE, 802.1X config |

### Site

| Tool | Description |
|---|---|
| `get_site_stats` | Site health summary — WAN, LAN, WLAN, VPN subsystem status and client counts |

## Security

All `_id` parameters are validated against a strict `^[a-f0-9]{24}$` pattern (MongoDB ObjectID format) before being interpolated into URL paths. Any value containing path traversal characters (`/`, `..`, `%`, `?`, `#`) or that doesn't match the 24-character hex format is rejected with a `ValueError` before any HTTP request is made.

## API notes

- Uses the `X-API-KEY` header (UniFi OS 3+). Cookie-based session auth is not supported.
- Firewall policies use the v2 API (`/proxy/network/v2/api/site/{site}/firewall-policies`). The legacy `/rest/firewallrule` endpoint returns empty on zone-based firewall setups (UCG and newer).
- `list_firewall_policies` returns custom rules only by default (`include_predefined=False`). Pass `include_predefined=True` to include all 100+ UniFi-managed built-in rules.
- `update_firewall_group` replaces the entire member list — fetch current members with `list_firewall_groups` first and include all IPs you want to keep.
- Event/alarm log endpoints return 404 on current UCG firmware — not supported via this API path.
- Bandwidth report endpoints (`/stat/report/hourly.site`) respond 200 but return only stub data — not implemented.
- `restart_device` takes effect immediately and causes a device outage of approximately 30–90 seconds. Restarting an AP disconnects all wireless clients on that AP.
