"""Cloud-init tools — configure cloud-init on VMs."""

from __future__ import annotations

from typing import Optional

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client
from proxmox_mcp.models import ProxmoxConfigResponse


@mcp.tool()
@safety_checked
async def set_vm_cloudinit(
    node: str,
    vmid: int,
    ciuser: Optional[str] = None,
    cipassword: Optional[str] = None,
    sshkeys: Optional[str] = None,
    ipconfig0: Optional[str] = None,
    confirmed: bool = False,
) -> dict:
    """Update Cloud-init configuration for a QEMU VM.

    Args:
        node: Node name
        vmid: VM ID
        ciuser: Cloud-init user
        cipassword: Cloud-init password
        sshkeys: SSH public keys
        ipconfig0: IP configuration (e.g. ip=dhcp or ip=10.0.0.2/24,gw=10.0.0.1)
    """
    params: dict = {}
    if ciuser is not None:
        params["ciuser"] = ciuser
    if cipassword is not None:
        params["cipassword"] = cipassword
    if sshkeys is not None:
        params["sshkeys"] = sshkeys
    if ipconfig0 is not None:
        params["ipconfig0"] = ipconfig0
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/qemu/{vmid}/config",
        ProxmoxConfigResponse, method="PUT", params=params,
    )
