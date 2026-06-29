"""Metrics tools — resource usage and performance data."""

from __future__ import annotations

from typing import Literal

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client
from proxmox_mcp.models import ProxmoxResourceUsageResponse


@mcp.tool()
@safety_checked
async def get_resource_usage(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    timeframe: Literal["hour", "day", "week", "month", "year"],
) -> dict:
    """Get performance metrics (CPU, memory, network) for a VM or LXC container."""
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/rrddata",
        ProxmoxResourceUsageResponse,
        params={"timeframe": timeframe},
    )
