"""Snapshot tools — list, create, and rollback snapshots."""

from __future__ import annotations

from typing import Literal, Optional

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client
from proxmox_mcp.models import ProxmoxSnapshotListResponse, ProxmoxTaskResponse


@mcp.tool()
@safety_checked
async def list_snapshots(node: str, vmid: int, type: Literal["lxc", "qemu"]) -> dict:
    """List snapshots for a VM or LXC container."""
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/snapshot",
        ProxmoxSnapshotListResponse,
    )


@mcp.tool()
@safety_checked
async def create_snapshot(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    snapname: str,
    description: Optional[str] = None,
    confirmed: bool = False,
) -> dict:
    """Create a snapshot of a VM or LXC container.

    Args:
        node: Node name
        vmid: Instance ID
        type: Instance type
        snapname: Unique name for the snapshot
        description: Optional description
    """
    params: dict = {"snapname": snapname}
    if description:
        params["description"] = description
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/snapshot",
        ProxmoxTaskResponse, method="POST", params=params,
    )


@mcp.tool()
@safety_checked
async def rollback_snapshot(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    snapname: str,
    confirmed: bool = False,
) -> dict:
    """Rollback a VM or LXC container to a snapshot."""
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/snapshot/{snapname}/rollback",
        ProxmoxTaskResponse, method="POST",
    )
