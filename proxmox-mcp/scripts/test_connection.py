#!/usr/bin/env python3
"""Manual connectivity check against Proxmox API."""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from proxmox_mcp.models import (
    ProxmoxNodeListResponse,
    ProxmoxLXCListResponse,
    ProxmoxVMListResponse,
    ProxmoxInterfaceListResponse,
)


async def test_all_tools():
    load_dotenv()

    url = os.getenv("PROXMOX_URL")
    token_name = os.getenv("PROXMOX_TOKEN_NAME")
    token_value = os.getenv("PROXMOX_TOKEN_VALUE")
    verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() == "true"

    if not all([url, token_name, token_value]):
        print("Error: Missing environment variables in .env.")
        return

    headers = {"Authorization": f"PVEAPIToken={token_name}={token_value}"}

    async with httpx.AsyncClient(verify=verify_ssl) as client:
        try:
            print("\n--- Testing: list_nodes ---")
            res = await client.get(f"{url}/nodes", headers=headers)
            res.raise_for_status()
            nodes = ProxmoxNodeListResponse(**res.json())
            print(f"Success! Found {len(nodes.data)} nodes.")

            if not nodes.data:
                print("No nodes found. Stopping tests.")
                return

            target_node = nodes.data[0].node
            print(f"Using node: '{target_node}' for further tests.")

            print(f"\n--- Testing: list_lxc_containers on '{target_node}' ---")
            res = await client.get(f"{url}/nodes/{target_node}/lxc", headers=headers)
            res.raise_for_status()
            lxcs = ProxmoxLXCListResponse(**res.json())
            print(f"Success! Found {len(lxcs.data)} LXC containers.")

            print(f"\n--- Testing: list_vms on '{target_node}' ---")
            res = await client.get(f"{url}/nodes/{target_node}/qemu", headers=headers)
            res.raise_for_status()
            vms = ProxmoxVMListResponse(**res.json())
            print(f"Success! Found {len(vms.data)} QEMU VMs.")

            if lxcs.data:
                target_lxc = lxcs.data[0]
                print(f"\n--- Testing: get_lxc_interfaces for LXC {target_lxc.vmid} ('{target_lxc.name}') ---")
                res = await client.get(f"{url}/nodes/{target_node}/lxc/{target_lxc.vmid}/interfaces", headers=headers)
                res.raise_for_status()
                if res.status_code == 200:
                    interfaces = ProxmoxInterfaceListResponse(**res.json())
                    print(f"Success! Found {len(interfaces.data)} interfaces.")
                    for iface in interfaces.data:
                        print(f"   - {iface.name}: IP={iface.inet or 'N/A'}, MAC={iface.hwaddr}")
                else:
                    print(f"Could not fetch interfaces (Status: {res.status_code})")
            else:
                print("\nSkipping get_lxc_interfaces (No LXC containers found on this node).")

        except Exception as e:
            print(f"Error during testing: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_all_tools())
