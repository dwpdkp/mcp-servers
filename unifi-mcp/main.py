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


if __name__ == "__main__":
    mcp.run()
