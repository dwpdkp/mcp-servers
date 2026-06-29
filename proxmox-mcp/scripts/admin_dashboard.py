#!/usr/bin/env python3
"""Live infrastructure overview dashboard."""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from typing import Any, Dict
from proxmox_mcp.models import (
    ProxmoxNodeListResponse,
    ProxmoxLXCListResponse,
    ProxmoxVMListResponse,
    ProxmoxStorageListResponse,
)


async def get_data(client: httpx.AsyncClient, url: str, model_class: Any, headers: Dict[str, str]):
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return model_class(**response.json()).data
    except Exception as e:
        print(f"  Warning: Failed to fetch {url}: {e}")
        return []


def format_size(bytes_val: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


async def show_dashboard():
    load_dotenv()
    prox_url = os.getenv("PROXMOX_URL")
    token_name = os.getenv("PROXMOX_TOKEN_NAME")
    token_value = os.getenv("PROXMOX_TOKEN_VALUE")
    verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() == "true"

    if not all([prox_url, token_name, token_value]):
        print("Error: Missing Proxmox credentials in .env")
        return

    headers = {"Authorization": f"PVEAPIToken={token_name}={token_value}"}

    print("\n" + "=" * 60)
    print("      PROXMOX MCP - ADMIN DASHBOARD")
    print("=" * 60)

    async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
        nodes = await get_data(client, f"{prox_url}/nodes", ProxmoxNodeListResponse, headers)

        for node in nodes:
            name = node.node
            status_icon = "[ON]" if node.status == "online" else "[OFF]"
            cpu_pct = (node.cpu or 0) * 100
            mem_pct = (node.mem / node.maxmem * 100) if node.maxmem else 0

            print(f"\n{status_icon} NODE: {name.upper()}")
            print(f"   CPU: {cpu_pct:.1f}% ({node.maxcpu} cores) | MEM: {mem_pct:.1f}% ({format_size(node.mem or 0)} / {format_size(node.maxmem)})")

            lxcs = await get_data(client, f"{prox_url}/nodes/{name}/lxc", ProxmoxLXCListResponse, headers)
            vms = await get_data(client, f"{prox_url}/nodes/{name}/qemu", ProxmoxVMListResponse, headers)

            print(f"   GUESTS: {len(lxcs)} Containers, {len(vms)} VMs")
            for guest in lxcs + vms:
                g_type = "LXC" if guest in lxcs else " VM"
                g_icon = ">" if guest.status == "running" else "-"
                print(f"      {g_icon} [{guest.vmid}] {g_type}: {guest.name or 'N/A'}")

            storage = await get_data(client, f"{prox_url}/nodes/{name}/storage", ProxmoxStorageListResponse, headers)
            print(f"   STORAGE:")
            for s in storage:
                if s.total:
                    s_pct = (s.used / s.total * 100) if s.total else 0
                    bar_len = 20
                    filled = int(s_pct / 100 * bar_len)
                    bar = "#" * filled + "." * (bar_len - filled)
                    print(f"      - {s.storage:<12} [{bar}] {s_pct:4.1f}% ({format_size(s.used or 0)} / {format_size(s.total)})")

    print("\n" + "=" * 60)
    print(f"Dashboard generated successfully.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(show_dashboard())
