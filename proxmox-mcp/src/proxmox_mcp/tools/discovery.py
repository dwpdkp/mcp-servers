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
    """List all physical nodes (hypervisor hosts) in the Proxmox VE cluster with status, CPU and memory."""
    return await get_client().fetch_and_validate("/nodes", ProxmoxNodeListResponse)


@mcp.tool()
@safety_checked
async def list_lxc_containers(node: str) -> dict:
    """List LXC containers (CTs) on a Proxmox node with VMID, name, status and resources."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/lxc", ProxmoxLXCListResponse)


@mcp.tool()
@safety_checked
async def list_vms(node: str) -> dict:
    """List QEMU virtual machines on a Proxmox node with VMID, name, status and resources."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/qemu", ProxmoxVMListResponse)


@mcp.tool()
@safety_checked
async def get_instance_config(node: str, vmid: int, type: str) -> dict:
    """Get the full config of a Proxmox VM or LXC (cores, memory, disks, network, mounts, onboot). Type must be 'lxc' or 'qemu'."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/{type}/{vmid}/config", ProxmoxConfigResponse)


@mcp.tool()
@safety_checked
async def get_lxc_interfaces(node: str, vmid: int) -> dict:
    """Get network interfaces and IP addresses of a Proxmox LXC container."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/lxc/{vmid}/interfaces", ProxmoxInterfaceListResponse)


@mcp.tool()
@safety_checked
async def list_storage(node: str) -> dict:
    """List Proxmox storage pools on a node (local, ZFS, NFS, CIFS, PBS) with usage and free space."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/storage", ProxmoxStorageListResponse)


@mcp.tool()
@safety_checked
async def list_storage_content(node: str, storage: str) -> dict:
    """List contents of a Proxmox storage: ISOs, container templates, VM disk images and vzdump/PBS backups."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/storage/{storage}/content", ProxmoxStorageContentListResponse)


@mcp.tool()
@safety_checked
async def get_task_status(node: str, upid: str) -> dict:
    """Check the status of a Proxmox background task (by UPID), e.g. a start, backup, migration or snapshot job."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/tasks/{upid}/status", ProxmoxTaskStatusResponse)


@mcp.tool()
@safety_checked
async def get_task_log(node: str, upid: str) -> dict:
    """Get the log output of a Proxmox background task (by UPID), to see why a job failed."""
    return await get_client().fetch_and_validate(f"/nodes/{node}/tasks/{upid}/log", ProxmoxTaskLogResponse)


@mcp.tool()
@safety_checked
async def get_mcp_logs(lines: int = 50) -> str:
    """Fetch this proxmox-mcp server's own logs, for debugging failed MCP tool calls."""
    log_file = os.path.join(get_project_root(), "proxmox-mcp.log")
    try:
        with open(log_file, "r") as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"
