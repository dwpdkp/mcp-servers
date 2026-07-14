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

Mutating tools require an explicit `confirm=true` argument — omitting it (or passing `false`) raises a `ValueError` before any request reaches the controller. See [Security](#security) for the full gating and validation reference.

### Clients & Devices

| Tool | Description |
|---|---|
| `list_clients` | Active (or all) network clients — MAC, IP, hostname, SSID, uptime |
| `list_devices` | All adopted UniFi devices (APs, switches, gateway) via integrations API |
| `get_device_stats` | Per-device CPU, memory, uptime, satisfaction score, and per-port TX/RX byte counts |
| `get_client_history` | All clients ever seen — last IP, last network, device type, blocked status |
| `get_system_info` | Gateway firmware version, build, hostname, uptime, timezone |
| `block_client` | Block a client from the network by MAC address (disconnects immediately) — requires `confirm=true` |
| `unblock_client` | Unblock a previously blocked client by MAC address |
| `restart_device` | Reboot an AP, switch, or gateway by MAC address (**disruptive — causes ~60s outage**) — requires `confirm=true` |

### DHCP

| Tool | Description |
|---|---|
| `list_dhcp_reservations` | All fixed-IP (reserved) DHCP assignments |
| `add_dhcp_reservation` | Create or update a DHCP reservation by MAC address |
| `remove_dhcp_reservation` | Remove a DHCP reservation by MAC address |

### WiFi

| Tool | Description |
|---|---|
| `list_wlans` | All SSIDs — name, enabled state, security type, VLAN, bound `networkconf_id`, L2 isolation |
| `update_wlan` | Update a WiFi network by `_id` — name, enabled, passphrase, security mode, VLAN — requires `confirm=true`; setting `security="open"` additionally requires `allow_open_security=true` (disables WiFi encryption on that SSID) |
| `list_rogue_aps` | Nearby APs detected by your APs; `rogue_only=True` for UniFi-flagged rogues only |

### Firewall

| Tool | Description |
|---|---|
| `list_firewall_policies` | Zone-based firewall rules; filter by `include_predefined` and `action_filter` (`ALLOW`/`BLOCK`) |
| `get_firewall_policy` | Fetch a single policy by `_id` (returns full raw object for inspection before editing) |
| `create_firewall_policy` | Create a new zone-based rule — src/dst zone + network targeting, action, protocol, auto-respond — requires `confirm=true` |
| `update_firewall_policy` | Update a policy by `_id` — name, action, enabled, logging, protocol, ip_version — requires `confirm=true` |
| `set_firewall_policy_logging` | Enable or disable logging on a specific policy by `_id` |
| `set_block_rules_logging` | Bulk enable/disable logging on all custom BLOCK rules at once |
| `list_firewall_groups` | Address and port groups used as rule sources/destinations |
| `update_firewall_group` | Replace the full member list (IPs/CIDRs) of an address group by `_id` — requires `confirm=true` |
| `list_port_forwards` | All WAN → LAN NAT / port forward rules |
| `create_port_forward` | Create a new port forward rule — requires `confirm=true`; `src="any"` additionally requires `allow_any_src=true` (exposes the forwarded port to the entire internet); `fwd` must be a private RFC1918 address and `dst_port`/`fwd_port` must be valid port/port-range values |
| `update_port_forward` | Update an existing port forward by `_id` — proto, fwd IP, ports, enabled, src, log — requires `confirm=true`; any provided `fwd`/`dst_port`/`fwd_port` is validated the same as `create_port_forward` |
| `delete_port_forward` | Delete a port forward rule by `_id` (permanent) — requires `confirm=true` |

### Network Configuration

| Tool | Description |
|---|---|
| `list_networks` | All VLANs and subnets — name, purpose, subnet, VLAN ID, DHCP range, `firewall_zone_id` (which zone-based firewall zone the network belongs to — cross-reference with `list_firewall_policies` zone IDs to check isolation), mDNS/network-isolation flags |
| `list_switch_port_profiles` | Switch port profiles — native VLAN, trunk mode, PoE, 802.1X config |

### Site

| Tool | Description |
|---|---|
| `get_site_stats` | Site health summary — WAN, LAN, WLAN, VPN subsystem status and client counts |

## Security

All `_id` parameters are validated against a strict `^[a-f0-9]{24}$` pattern (MongoDB ObjectID format) before being interpolated into URL paths. Any value containing path traversal characters (`/`, `..`, `%`, `?`, `#`) or that doesn't match the 24-character hex format is rejected with a `ValueError` before any HTTP request is made.

### Confirmation gates

Every tool that changes live network configuration requires an explicit `confirm: bool = True` argument. Calling it without `confirm=true` raises a `ValueError` describing the action and asking the caller to get explicit user approval before retrying — no request is sent to the controller in that case. Gated tools: `create_firewall_policy`, `update_firewall_policy`, `update_firewall_group`, `create_port_forward`, `update_port_forward`, `delete_port_forward`, `update_wlan`, `block_client`, `restart_device`.

Two tools have a second, narrower gate on top of `confirm` for a specific dangerous value:

- `update_wlan` — passing `security="open"` (disabling all WiFi encryption on that SSID) also requires `allow_open_security=true`.
- `create_port_forward` — passing `src="any"` (exposing the forwarded port to the entire internet, not just a specific source) also requires `allow_any_src=true`.

### Port forward input validation

`create_port_forward` and `update_port_forward` validate two additional fields before any request is sent:

- `fwd` (the internal target) must be a private, non-loopback, non-link-local IPv4 address (RFC1918) — a public IP here would misconfigure the forward.
- `dst_port` / `fwd_port` must be a single port or a `start-end` range, each in 1–65535.

Invalid values raise a `ValueError` naming the offending field.

### Read-only vs. destructive tools

Tools not listed above (`list_*`, `get_*`, `add_dhcp_reservation`, `remove_dhcp_reservation`, `unblock_client`, `set_firewall_policy_logging`, `set_block_rules_logging`) are unblocked by design — they're either read-only or low-risk/reversible operations that don't warrant a confirmation gate.

## API notes

- Uses the `X-API-KEY` header (UniFi OS 3+). Cookie-based session auth is not supported.
- Firewall policies use the v2 API (`/proxy/network/v2/api/site/{site}/firewall-policies`). The legacy `/rest/firewallrule` endpoint returns empty on zone-based firewall setups (UCG and newer).
- `list_firewall_policies` returns custom rules only by default (`include_predefined=False`). Pass `include_predefined=True` to include all 100+ UniFi-managed built-in rules.
- `update_firewall_group` replaces the entire member list — fetch current members with `list_firewall_groups` first and include all IPs you want to keep.
- Event/alarm log endpoints return 404 on current UCG firmware — not supported via this API path.
- Bandwidth report endpoints (`/stat/report/hourly.site`) respond 200 but return only stub data — not implemented.
- `restart_device` takes effect immediately and causes a device outage of approximately 30–90 seconds. Restarting an AP disconnects all wireless clients on that AP.
- There is no dedicated firewall-zone-listing endpoint (`/v2/api/site/{site}/firewall/zones` and similar paths all 404 on UCG Ultra 5.1.19). Zone names are rendered client-side in the UI from a static list and aren't fetchable via API. To check whether two networks share a zone (and therefore share the same intra-zone allow/deny default), compare `firewall_zone_id` from `list_networks` — matching IDs mean matching zones, even without a human-readable name.

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-07-14 | Doug Pearson | Documented confirm-gate security hardening (create/update/delete firewall policies and port forwards, update_wlan, block_client, restart_device) and RFC1918/port-range input validation |
