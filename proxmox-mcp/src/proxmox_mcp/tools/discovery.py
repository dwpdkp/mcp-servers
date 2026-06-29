"""Discovery tools — read-only queries against Proxmox."""

from __future__ import annotations

import os
from typing import Optional

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client, get_project_root
from proxmox_mcp.models import (
    ProxmoxNodeListResponse,
    ProxmoxLXCListResponse,
    ProxmoxVMListResponse,
    ProxmoxConfigResponse,
    ProxmoxInterfaceListResponse,
    ProxmoxStorageListResponse,
    ProxmoxStorageContentListResponse,
    ProxmoxTaskStatusResponse,
    ProxmoxTaskLogResponse,
)


@mcp.tool()
@safety_checked
async def list_nodes() -> dict:
    """List all physical nodes in the Proxmox cluster."""
    return await get_client().fetch_and_validate("/nodes", ProxmoxNodeListResponse)


@mcp.tool()
@safety_checked
async def list_lxc_containers(node: str) -> dict:
    """List LXC containers on a node."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/lxc", ProxmoxLXCListResponse)


@mcp.tool()
@safety_checked
async def list_vms(node: str) -> dict:
    """List VMs on a node."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/qemu", ProxmoxVMListResponse)


@mcp.tool()
@safety_checked
async def get_instance_config(node: str, vmid: int, type: str) -> dict:
    """Get instance configuration. Type must be 'lxc' or 'qemu'."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/{type}/{vmid}/config", ProxmoxConfigResponse)


@mcp.tool()
@safety_checked
async def get_lxc_interfaces(node: str, vmid: int) -> dict:
    """Get LXC network interfaces."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/lxc/{vmid}/interfaces", ProxmoxInterfaceListResponse)


@mcp.tool()
@safety_checked
async def list_storage(node: str) -> dict:
    """List storage on a node."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/storage", ProxmoxStorageListResponse)


@mcp.tool()
@safety_checked
async def list_storage_content(node: str, storage: str) -> dict:
    """List files in a storage."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/storage/{storage}/content", ProxmoxStorageContentListResponse)


@mcp.tool()
@safety_checked
async def get_task_status(node: str, upid: str) -> dict:
    """Check background task status."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/tasks/{upid}/status", ProxmoxTaskStatusResponse)


@mcp.tool()
@safety_checked
async def get_task_log(node: str, upid: str) -> dict:
    """Get execution log of a task."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/tasks/{upid}/log", ProxmoxTaskLogResponse)


@mcp.tool()
@safety_checked
async def get_mcp_logs(lines: int = 50) -> str:
    """Fetch MCP server logs."""
    log_file = os.path.join(get_project_root(), "proxmox-mcp.log")
    try:
        with open(log_file, "r") as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"
