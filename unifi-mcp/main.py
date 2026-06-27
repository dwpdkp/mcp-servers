"""UniFi local controller MCP server — X-API-KEY auth for UCG/UDM (UniFi OS 3+)."""

import os
from typing import Any

import httpx
from fastmcp import FastMCP

UNIFI_URL = os.getenv("UNIFI_URL", "https://10.0.1.1")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY", "")
UNIFI_SITE = os.getenv("UNIFI_SITE", "default")
VERIFY_SSL = os.getenv("UNIFI_VERIFY_SSL", "false").lower() == "true"

mcp = FastMCP("UniFi")

# Site ID for the integrations API (auto-populated on first call)
_site_id: str = ""


def _headers() -> dict[str, str]:
    return {"X-API-KEY": UNIFI_API_KEY}


def _api(path: str) -> str:
    return f"{UNIFI_URL}/proxy/network/api/s/{UNIFI_SITE}{path}"


def _v2(path: str) -> str:
    return f"{UNIFI_URL}/proxy/network/v2/api/site/{UNIFI_SITE}{path}"


async def _get_site_id() -> str:
    global _site_id
    if _site_id:
        return _site_id
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(f"{UNIFI_URL}/proxy/network/integrations/v1/sites", headers=_headers())
        r.raise_for_status()
        sites = r.json().get("data", [])
        for s in sites:
            if s.get("internalReference") == UNIFI_SITE:
                _site_id = s["id"]
                return _site_id
        if sites:
            _site_id = sites[0]["id"]
    return _site_id


def _summarize_policy(p: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, readable summary of a firewall policy."""
    src = p.get("source", {})
    dst = p.get("destination", {})
    return {
        "_id": p.get("_id"),
        "name": p.get("name"),
        "action": p.get("action"),
        "enabled": p.get("enabled", True),
        "logging": p.get("logging", False),
        "predefined": p.get("predefined", False),
        "index": p.get("index"),
        "protocol": p.get("protocol", "all"),
        "ip_version": p.get("ip_version", "BOTH"),
        "connection_state_type": p.get("connection_state_type", "ALL"),
        "src_zone_id": src.get("zone_id"),
        "src_ips": src.get("ips", []),
        "src_target": src.get("matching_target", "ANY"),
        "dst_zone_id": dst.get("zone_id"),
        "dst_ips": dst.get("ips", []),
        "dst_target": dst.get("matching_target", "ANY"),
        "schedule": p.get("schedule", {}).get("mode", "ALWAYS"),
    }


@mcp.tool()
async def list_clients(active_only: bool = True) -> list[dict[str, Any]]:
    """List network clients. active_only=True returns currently connected clients only."""
    endpoint = _api("/stat/sta") if active_only else _api("/rest/user")
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(endpoint, headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    fields = ["mac", "ip", "hostname", "name", "oui", "is_wired", "essid", "uptime", "fixed_ip", "use_fixedip"]
    return [{k: v for k, v in d.items() if k in fields} for d in data]


@mcp.tool()
async def list_devices() -> list[dict[str, Any]]:
    """List all UniFi network devices (APs, switches, gateways)."""
    site_id = await _get_site_id()
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(
            f"{UNIFI_URL}/proxy/network/integrations/v1/sites/{site_id}/devices",
            headers=_headers(),
        )
        r.raise_for_status()
    return r.json().get("data", [])


@mcp.tool()
async def list_dhcp_reservations() -> list[dict[str, Any]]:
    """List all clients with fixed/reserved DHCP IP addresses."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/user"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    reservations = [d for d in data if d.get("use_fixedip") and d.get("fixed_ip")]
    return [{"mac": d.get("mac"), "ip": d.get("fixed_ip"), "name": d.get("name") or d.get("hostname", ""), "_id": d.get("_id")} for d in reservations]


@mcp.tool()
async def add_dhcp_reservation(mac: str, ip: str, name: str = "") -> dict[str, Any]:
    """Add or update a DHCP reservation (fixed IP) for a client by MAC address."""
    mac = mac.lower()
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/user"), headers=_headers(), params={"mac": mac})
        r.raise_for_status()
        users = r.json().get("data", [])
        payload: dict[str, Any] = {"use_fixedip": True, "fixed_ip": ip}
        if name:
            payload["name"] = name
        if users:
            user_id = users[0]["_id"]
            r2 = await c.put(_api(f"/rest/user/{user_id}"), headers=_headers(), json=payload)
            r2.raise_for_status()
            return {"status": "updated", "mac": mac, "ip": ip}
        payload["mac"] = mac
        r2 = await c.post(_api("/rest/user"), headers=_headers(), json=payload)
        r2.raise_for_status()
        return {"status": "created", "mac": mac, "ip": ip}


@mcp.tool()
async def remove_dhcp_reservation(mac: str) -> dict[str, Any]:
    """Remove a DHCP reservation for a client by MAC address."""
    mac = mac.lower()
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/user"), headers=_headers(), params={"mac": mac})
        r.raise_for_status()
        users = r.json().get("data", [])
        if not users:
            return {"status": "not_found", "mac": mac}
        user_id = users[0]["_id"]
        r2 = await c.put(_api(f"/rest/user/{user_id}"), headers=_headers(), json={"use_fixedip": False})
        r2.raise_for_status()
    return {"status": "removed", "mac": mac}


@mcp.tool()
async def list_wlans() -> list[dict[str, Any]]:
    """List all configured WiFi networks (SSIDs)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/wlanconf"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    return [{"name": d.get("name"), "enabled": d.get("enabled"), "security": d.get("security"), "vlan": d.get("vlan")} for d in data]


@mcp.tool()
async def get_site_stats() -> list[dict[str, Any]]:
    """Get site health and statistics summary."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/stat/health"), headers=_headers())
        r.raise_for_status()
    return r.json().get("data", [])


# ── Firewall ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_firewall_policies(
    include_predefined: bool = False,
    action_filter: str = "",
) -> list[dict[str, Any]]:
    """List firewall policies (zone-based rules, UniFi OS 3+ / UCG).

    Args:
        include_predefined: Include UniFi-managed built-in rules (default False — custom rules only).
        action_filter: Optional filter by action: "ALLOW", "BLOCK", or "" for all.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2("/firewall-policies"), headers=_headers())
        r.raise_for_status()
    policies = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
    if not include_predefined:
        policies = [p for p in policies if not p.get("predefined", False)]
    if action_filter:
        policies = [p for p in policies if p.get("action", "").upper() == action_filter.upper()]
    return [_summarize_policy(p) for p in policies]


@mcp.tool()
async def get_firewall_policy(policy_id: str) -> dict[str, Any]:
    """Get a single firewall policy by its _id (returns full raw object)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2(f"/firewall-policies/{policy_id}"), headers=_headers())
        r.raise_for_status()
    return r.json()


@mcp.tool()
async def update_firewall_policy(
    policy_id: str,
    name: str | None = None,
    action: str | None = None,
    enabled: bool | None = None,
    logging: bool | None = None,
    protocol: str | None = None,
    ip_version: str | None = None,
) -> dict[str, Any]:
    """Update an existing firewall policy by its _id.

    Only the fields you provide are changed — all others keep their current values.
    Use list_firewall_policies or get_firewall_policy to find the _id first.

    Args:
        policy_id: The _id of the firewall policy to update.
        name: Display name for the rule.
        action: "ALLOW" or "BLOCK".
        enabled: Enable or disable the rule.
        logging: Enable or disable logging for matched traffic.
        protocol: Protocol to match — "all", "tcp", "udp", "tcp_udp", "icmp", "icmpv6".
        ip_version: "IPV4", "IPV6", or "BOTH".
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2(f"/firewall-policies/{policy_id}"), headers=_headers())
        r.raise_for_status()
        policy = r.json()

        if name is not None:
            policy["name"] = name
        if action is not None:
            policy["action"] = action.upper()
        if enabled is not None:
            policy["enabled"] = enabled
        if logging is not None:
            policy["logging"] = logging
        if protocol is not None:
            policy["protocol"] = protocol
        if ip_version is not None:
            policy["ip_version"] = ip_version.upper()

        r2 = await c.put(_v2(f"/firewall-policies/{policy_id}"), headers=_headers(), json=policy)
        r2.raise_for_status()
        updated = r2.json()
    return _summarize_policy(updated if isinstance(updated, dict) else policy)


@mcp.tool()
async def set_firewall_policy_logging(policy_id: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable logging on a specific firewall policy by its _id.

    Fetch the policy first with get_firewall_policy to confirm the _id, then call this
    to toggle logging. Returns the updated policy summary.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2(f"/firewall-policies/{policy_id}"), headers=_headers())
        r.raise_for_status()
        policy = r.json()
        policy["logging"] = enabled
        r2 = await c.put(_v2(f"/firewall-policies/{policy_id}"), headers=_headers(), json=policy)
        r2.raise_for_status()
        updated = r2.json()
    return _summarize_policy(updated if isinstance(updated, dict) else policy)


@mcp.tool()
async def set_block_rules_logging(enabled: bool = True) -> dict[str, Any]:
    """Bulk enable or disable logging on all BLOCK firewall policies (custom rules only).

    This is a convenience tool to implement the security recommendation of logging
    all denied traffic. Returns a summary of how many rules were updated.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2("/firewall-policies"), headers=_headers())
        r.raise_for_status()
        policies = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        block_custom = [
            p for p in policies
            if p.get("action", "").upper() == "BLOCK" and not p.get("predefined", False)
        ]
        updated = []
        skipped = []
        for p in block_custom:
            if p.get("logging") == enabled:
                skipped.append(p.get("name"))
                continue
            p["logging"] = enabled
            r2 = await c.put(_v2(f"/firewall-policies/{p['_id']}"), headers=_headers(), json=p)
            if r2.status_code < 300:
                updated.append(p.get("name"))
            else:
                skipped.append(f"{p.get('name')} (error {r2.status_code})")
    return {
        "logging_set_to": enabled,
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "updated": updated,
        "skipped": skipped,
    }


@mcp.tool()
async def list_firewall_groups() -> list[dict[str, Any]]:
    """List firewall address and port groups (used as sources/destinations in rules)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/firewallgroup"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    return [
        {
            "_id": g.get("_id"),
            "name": g.get("name"),
            "group_type": g.get("group_type"),
            "group_members": g.get("group_members", []),
        }
        for g in data
    ]


@mcp.tool()
async def list_port_forwards() -> list[dict[str, Any]]:
    """List all port forward rules (WAN → LAN NAT rules)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/portforward"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    return [
        {
            "_id": pf.get("_id"),
            "name": pf.get("name"),
            "enabled": pf.get("enabled", True),
            "interface": pf.get("pfwd_interface"),
            "proto": pf.get("proto"),
            "dst_port": pf.get("dst_port"),
            "fwd": pf.get("fwd"),
            "fwd_port": pf.get("fwd_port"),
            "src": pf.get("src", "any"),
            "log": pf.get("log", False),
        }
        for pf in data
    ]


@mcp.tool()
async def update_port_forward(
    port_forward_id: str,
    name: str | None = None,
    enabled: bool | None = None,
    proto: str | None = None,
    dst_port: str | None = None,
    fwd: str | None = None,
    fwd_port: str | None = None,
    src: str | None = None,
    log: bool | None = None,
) -> dict[str, Any]:
    """Update an existing port forward rule by its _id.

    Only the fields you provide are changed — all others keep their current values.
    Use list_port_forwards to find the _id and current values before calling this.

    Args:
        port_forward_id: The _id of the port forward rule to update.
        name: Display name for the rule.
        enabled: Enable or disable the rule.
        proto: Protocol — "tcp", "udp", or "tcp_udp".
        dst_port: Destination port or range on the WAN side (e.g. "80", "8000-8080").
        fwd: LAN IP address to forward traffic to.
        fwd_port: Port or range on the LAN destination (e.g. "80", "8000-8080").
        src: Source IP restriction — "any" or a specific IP/CIDR.
        log: Enable or disable logging for this rule.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api(f"/rest/portforward/{port_forward_id}"), headers=_headers())
        r.raise_for_status()
        rule = r.json().get("data", [{}])[0]

        if name is not None:
            rule["name"] = name
        if enabled is not None:
            rule["enabled"] = enabled
        if proto is not None:
            rule["proto"] = proto
        if dst_port is not None:
            rule["dst_port"] = dst_port
        if fwd is not None:
            rule["fwd"] = fwd
        if fwd_port is not None:
            rule["fwd_port"] = fwd_port
        if src is not None:
            rule["src"] = src
        if log is not None:
            rule["log"] = log

        r2 = await c.put(_api(f"/rest/portforward/{port_forward_id}"), headers=_headers(), json=rule)
        r2.raise_for_status()
        updated = r2.json().get("data", [{}])[0]

    return {
        "_id": updated.get("_id"),
        "name": updated.get("name"),
        "enabled": updated.get("enabled", True),
        "interface": updated.get("pfwd_interface"),
        "proto": updated.get("proto"),
        "dst_port": updated.get("dst_port"),
        "fwd": updated.get("fwd"),
        "fwd_port": updated.get("fwd_port"),
        "src": updated.get("src", "any"),
        "log": updated.get("log", False),
    }


@mcp.tool()
async def list_networks() -> list[dict[str, Any]]:
    """List all configured network segments (VLANs, subnets, purposes)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/networkconf"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    return [
        {
            "_id": n.get("_id"),
            "name": n.get("name"),
            "purpose": n.get("purpose"),
            "ip_subnet": n.get("ip_subnet"),
            "vlan": n.get("vlan"),
            "dhcpd_enabled": n.get("dhcpd_enabled", False),
            "dhcpd_start": n.get("dhcpd_start"),
            "dhcpd_stop": n.get("dhcpd_stop"),
            "domain_name": n.get("domain_name"),
            "igmp_snooping": n.get("igmp_snooping", False),
        }
        for n in data
    ]


# ── Monitoring & Visibility ───────────────────────────────────────────────────

@mcp.tool()
async def get_system_info() -> dict[str, Any]:
    """Get gateway system info: firmware version, uptime, hostname, timezone."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/stat/sysinfo"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [{}])[0]
    fields = [
        "version", "build", "hostname", "name", "timezone",
        "uptime", "wan_ip", "wan_netmask", "architecture",
        "kernel_version", "ntp_servers",
    ]
    return {k: data[k] for k in fields if k in data}


@mcp.tool()
async def list_rogue_aps(rogue_only: bool = False) -> list[dict[str, Any]]:
    """List nearby WiFi access points detected by your APs.

    Args:
        rogue_only: If True, return only APs flagged as rogue by UniFi (default False = all nearby APs).

    Useful for RF environment monitoring and detecting unauthorized APs near your network.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/stat/rogueap"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    if rogue_only:
        data = [ap for ap in data if ap.get("is_rogue")]
    return [
        {
            "essid": ap.get("essid", ""),
            "bssid": ap.get("bssid"),
            "channel": ap.get("channel"),
            "band": ap.get("band"),
            "security": ap.get("security"),
            "signal": ap.get("signal"),
            "rssi": ap.get("rssi"),
            "is_rogue": ap.get("is_rogue", False),
            "is_ubnt": ap.get("is_ubnt", False),
            "last_seen": ap.get("last_seen"),
            "ap_name": ap.get("ap_name"),
            "oui": ap.get("oui"),
        }
        for ap in data
    ]


@mcp.tool()
async def get_client_history() -> list[dict[str, Any]]:
    """List historical client records (all clients ever seen, not just currently active).

    Returns connection history including last seen time, last IP, last network, and device type.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_v2("/clients/history"), headers=_headers())
        r.raise_for_status()
    data = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
    return [
        {
            "id": c.get("id") or c.get("user_id"),
            "mac": c.get("mac"),
            "display_name": c.get("display_name") or c.get("name") or c.get("hostname", ""),
            "type": c.get("type"),
            "last_seen": c.get("last_seen"),
            "last_ip": c.get("last_ip"),
            "last_connection_network_name": c.get("last_connection_network_name"),
            "fixed_ip": c.get("fixed_ip"),
            "use_fixedip": c.get("use_fixedip", False),
            "is_guest": c.get("is_guest", False),
            "blocked": c.get("blocked", False),
            "oui": c.get("oui"),
        }
        for c in data
    ]


@mcp.tool()
async def list_switch_port_profiles() -> list[dict[str, Any]]:
    """List switch port profiles (VLAN and trunk configurations applied to switch ports)."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/rest/portconf"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    return [
        {
            "_id": p.get("_id"),
            "name": p.get("name"),
            "op_mode": p.get("op_mode"),
            "native_networkconf_id": p.get("native_networkconf_id"),
            "tagged_vlan_mgmt": p.get("tagged_vlan_mgmt"),
            "voice_networkconf_id": p.get("voice_networkconf_id"),
            "poe_mode": p.get("poe_mode"),
            "isolation": p.get("isolation", False),
            "dot1x_ctrl": p.get("dot1x_ctrl"),
            "stp_port_mode": p.get("stp_port_mode", True),
            "port_security_enabled": p.get("port_security_enabled", False),
        }
        for p in data
    ]


@mcp.tool()
async def get_device_stats() -> list[dict[str, Any]]:
    """Get detailed stats for all UniFi devices (APs, switches, gateway) including CPU, memory, uptime, and port status."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api("/stat/device"), headers=_headers())
        r.raise_for_status()
    data = r.json().get("data", [])
    results = []
    for d in data:
        entry: dict[str, Any] = {
            "mac": d.get("mac"),
            "name": d.get("name"),
            "model": d.get("model"),
            "type": d.get("type"),
            "version": d.get("version"),
            "ip": d.get("ip"),
            "uptime": d.get("uptime"),
            "state": d.get("state"),
            "adopted": d.get("adopted"),
            "cpu_usage": d.get("system-stats", {}).get("cpu"),
            "mem_usage": d.get("system-stats", {}).get("mem"),
            "satisfaction": d.get("satisfaction"),
            "num_sta": d.get("num_sta"),
            "num_client": d.get("num_client"),
            "tx_bytes": d.get("tx_bytes"),
            "rx_bytes": d.get("rx_bytes"),
        }
        # Include port table for switches/gateways
        if d.get("port_table"):
            entry["ports"] = [
                {
                    "name": p.get("name"),
                    "port_idx": p.get("port_idx"),
                    "up": p.get("up"),
                    "speed": p.get("speed"),
                    "poe_enable": p.get("poe_enable"),
                    "tx_bytes": p.get("tx_bytes"),
                    "rx_bytes": p.get("rx_bytes"),
                }
                for p in d.get("port_table", [])
                if p.get("port_idx") is not None
            ]
        results.append(entry)
    return results


# ── Write Operations ──────────────────────────────────────────────────────────

@mcp.tool()
async def create_port_forward(
    name: str,
    fwd: str,
    dst_port: str,
    fwd_port: str,
    proto: str = "tcp",
    src: str = "any",
    enabled: bool = True,
    log: bool = False,
) -> dict[str, Any]:
    """Create a new port forward (WAN → LAN NAT) rule.

    Args:
        name: Display name for the rule.
        fwd: LAN IP address to forward traffic to.
        dst_port: WAN-side port or range to listen on (e.g. "8080", "8000-8090").
        fwd_port: LAN-side port or range to forward to (e.g. "80", "8000-8090").
        proto: Protocol — "tcp", "udp", or "tcp_udp" (default "tcp").
        src: Source IP restriction — "any" or a specific IP/CIDR (default "any").
        enabled: Whether the rule is active (default True).
        log: Enable logging for this rule (default False).
    """
    payload: dict[str, Any] = {
        "pfwd_interface": "wan",
        "name": name,
        "proto": proto,
        "dst_port": dst_port,
        "fwd": fwd,
        "fwd_port": fwd_port,
        "src": src,
        "enabled": enabled,
        "log": log,
        "destination_ip": "any",
        "destination_ips": [],
    }
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.post(_api("/rest/portforward"), headers=_headers(), json=payload)
        r.raise_for_status()
    created = r.json().get("data", [{}])[0]
    return {
        "_id": created.get("_id"),
        "name": created.get("name"),
        "enabled": created.get("enabled", True),
        "interface": created.get("pfwd_interface"),
        "proto": created.get("proto"),
        "dst_port": created.get("dst_port"),
        "fwd": created.get("fwd"),
        "fwd_port": created.get("fwd_port"),
        "src": created.get("src", "any"),
        "log": created.get("log", False),
    }


@mcp.tool()
async def delete_port_forward(port_forward_id: str) -> dict[str, Any]:
    """Delete a port forward rule by its _id.

    Use list_port_forwards to find the _id before calling this. This is permanent.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.delete(_api(f"/rest/portforward/{port_forward_id}"), headers=_headers())
        r.raise_for_status()
    return {"status": "deleted", "_id": port_forward_id}


@mcp.tool()
async def update_wlan(
    wlan_id: str,
    name: str | None = None,
    enabled: bool | None = None,
    passphrase: str | None = None,
    security: str | None = None,
    vlan: int | None = None,
) -> dict[str, Any]:
    """Update a WiFi network (SSID) configuration by its _id.

    Use list_wlans to find the _id and current values first. Only provided fields are changed.

    Args:
        wlan_id: The _id of the WLAN to update.
        name: SSID name (the network name clients see).
        enabled: Enable or disable the SSID.
        passphrase: WiFi password (WPA-PSK networks only).
        security: Security mode — "wpapsk" (WPA2), "wpa3" (WPA3), "open".
        vlan: VLAN ID to tag traffic onto (0 or None for untagged).
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api(f"/rest/wlanconf/{wlan_id}"), headers=_headers())
        r.raise_for_status()
        wlan = r.json().get("data", [{}])[0]

        if name is not None:
            wlan["name"] = name
        if enabled is not None:
            wlan["enabled"] = enabled
        if passphrase is not None:
            wlan["x_passphrase"] = passphrase
        if security is not None:
            wlan["security"] = security
        if vlan is not None:
            wlan["vlan"] = vlan
            wlan["vlan_enabled"] = vlan > 0

        r2 = await c.put(_api(f"/rest/wlanconf/{wlan_id}"), headers=_headers(), json=wlan)
        r2.raise_for_status()
    return {
        "_id": wlan.get("_id"),
        "name": wlan.get("name"),
        "enabled": wlan.get("enabled"),
        "security": wlan.get("security"),
        "vlan": wlan.get("vlan"),
    }


@mcp.tool()
async def update_firewall_group(
    group_id: str,
    members: list[str],
) -> dict[str, Any]:
    """Replace the members of a firewall address group by its _id.

    Provide the full desired member list — this replaces all existing members.
    Use list_firewall_groups to find the _id and current members first.

    Args:
        group_id: The _id of the firewall group to update.
        members: Complete list of IP addresses or CIDRs for the group.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.get(_api(f"/rest/firewallgroup/{group_id}"), headers=_headers())
        r.raise_for_status()
        group = r.json().get("data", [{}])[0]
        group["group_members"] = members
        r2 = await c.put(_api(f"/rest/firewallgroup/{group_id}"), headers=_headers(), json=group)
        r2.raise_for_status()
        updated = r2.json().get("data", [{}])[0]
    return {
        "_id": updated.get("_id"),
        "name": updated.get("name"),
        "group_type": updated.get("group_type"),
        "group_members": updated.get("group_members", []),
    }


@mcp.tool()
async def block_client(mac: str) -> dict[str, Any]:
    """Block a client device from the network by MAC address.

    The device will be disconnected and prevented from reconnecting until unblocked.
    Use unblock_client to reverse this.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.post(
            _api("/cmd/stamgr"),
            headers=_headers(),
            json={"cmd": "block-sta", "mac": mac.lower()},
        )
        r.raise_for_status()
    return {"status": "blocked", "mac": mac.lower()}


@mcp.tool()
async def unblock_client(mac: str) -> dict[str, Any]:
    """Unblock a previously blocked client device by MAC address."""
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.post(
            _api("/cmd/stamgr"),
            headers=_headers(),
            json={"cmd": "unblock-sta", "mac": mac.lower()},
        )
        r.raise_for_status()
    return {"status": "unblocked", "mac": mac.lower()}


@mcp.tool()
async def restart_device(mac: str) -> dict[str, Any]:
    """Reboot a UniFi device (AP, switch, or gateway) by its MAC address.

    The device will be temporarily offline during restart (typically 30-90 seconds).
    Use get_device_stats to find the MAC address of the device to restart.
    """
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=15) as c:
        r = await c.post(
            _api("/cmd/devmgr"),
            headers=_headers(),
            json={"cmd": "restart", "mac": mac.lower()},
        )
        r.raise_for_status()
    return {"status": "restart_initiated", "mac": mac.lower()}


if __name__ == "__main__":
    mcp.run()
