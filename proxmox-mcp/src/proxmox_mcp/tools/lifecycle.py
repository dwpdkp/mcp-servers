"""Lifecycle tools — create, destroy, and power-manage instances."""

from __future__ import annotations

from typing import Literal, Optional

from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client
from proxmox_mcp.models import ProxmoxTaskResponse


@mcp.tool()
@safety_checked
async def power_control(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    action: Literal["start", "stop", "shutdown", "reboot"],
    confirmed: bool = False,
) -> dict:
    """Start, stop, shutdown, or reboot a VM or LXC container."""
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/status/{action}",
        ProxmoxTaskResponse, method="POST",
    )


@mcp.tool()
@safety_checked
async def create_lxc(
    node: str,
    vmid: int,
    ostemplate: str,
    storage: str,
    password: str,
    net0: str,
    disk: int = 8,
    memory: int = 512,
    cores: int = 1,
    hostname: Optional[str] = None,
    ssh_public_keys: Optional[str] = None,
    confirmed: bool = False,
) -> dict:
    """Create a new Linux Container (LXC).

    Args:
        node: Target node name
        vmid: Unique ID for the new LXC
        ostemplate: Path to template (e.g., local:vztmpl/ubuntu...)
        storage: Target storage for rootfs (e.g., local-lvm)
        password: Root password
        net0: Network config
        disk: Disk size in GB
        memory: Memory in MB
        cores: CPU cores
        hostname: Hostname for the container
        ssh_public_keys: Public SSH keys (newline separated)
    """
    params: dict = {
        "vmid": vmid,
        "ostemplate": ostemplate,
        "rootfs": f"{storage}:{disk}",
        "memory": memory,
        "cores": cores,
        "password": password,
        "net0": net0,
    }
    if hostname:
        params["hostname"] = hostname
    if ssh_public_keys:
        params["ssh-public-keys"] = ssh_public_keys
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/lxc", ProxmoxTaskResponse, method="POST", params=params,
    )


@mcp.tool()
@safety_checked
async def create_vm(
    node: str,
    vmid: int,
    name: str,
    memory: Optional[int] = None,
    net0: Optional[str] = None,
    scsi0: Optional[str] = None,
    onboot: Optional[bool] = None,
    confirmed: bool = False,
) -> dict:
    """Create a new Virtual Machine (QEMU).

    Args:
        node: Target node name
        vmid: Unique ID for the new VM
        name: VM name
        memory: Memory in MB
        net0: Network bridge config (e.g. model=virtio,bridge=vmbr0)
        scsi0: Disk config (e.g. local-lvm:32)
        onboot: Start at boot
    """
    params: dict = {"vmid": vmid, "name": name}
    if memory is not None:
        params["memory"] = memory
    if net0 is not None:
        params["net0"] = net0
    if scsi0 is not None:
        params["scsi0"] = scsi0
    if onboot is not None:
        params["onboot"] = onboot
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/qemu", ProxmoxTaskResponse, method="POST", params=params,
    )


@mcp.tool()
@safety_checked
async def delete_instance(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    confirm_vmid: int,
    confirmed: bool = False,
) -> dict:
    """DESTRUCTIVE: Permanently delete an LXC container or VM. confirm_vmid must match vmid."""
    if vmid != confirm_vmid:
        raise ToolError("VMID mismatch. confirm_vmid must match vmid.")
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}",
        ProxmoxTaskResponse, method="DELETE",
    )
