"""Lifecycle tools — create, destroy, and power-manage instances."""

from __future__ import annotations

from typing import Literal, Optional

from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked, get_client
from proxmox_mcp.models import (
    ProxmoxClusterStatusResponse,
    ProxmoxTaskResponse,
    ProxmoxUpdateConfigResponse,
)


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
async def update_instance_config(
    node: str,
    vmid: int,
    type: Literal["lxc", "qemu"],
    key: str,
    value: str,
    confirmed: bool = False,
) -> dict:
    """Set a single config key on a VM or LXC — equivalent to `qm set`/`pct set`.

    Use for things create_vm/create_lxc don't cover post-creation: memory,
    cores, agent, onboot, boot order, disk attach, etc. One key/value pair
    per call (Proxmox's config PUT accepts many keys at once, but scoping
    this tool to one avoids building a free-form params dict from tool input).

    Examples: key="memory" value="3072", key="agent" value="enabled=1",
    key="onboot" value="1", key="boot" value="order=sata0".
    """
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/{type}/{vmid}/config",
        ProxmoxUpdateConfigResponse, method="PUT", params={key: value},
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


@mcp.tool()
@safety_checked
async def reboot_node(node: str, confirm_node: str, confirmed: bool = False) -> dict:
    """Reboot a Proxmox HOST node (every guest on it goes down with it).

    confirm_node must repeat the node name. Refuses unless the cluster is quorate
    and every other member node is online, so one reboot can't drop quorum.
    Confirm the reboot afterwards by the node's uptime resetting (list_nodes).
    """
    if confirm_node != node:
        raise ToolError(f"confirm_node '{confirm_node}' does not match node '{node}'")
    status = (await get_client().fetch_and_validate(
        "/cluster/status", ProxmoxClusterStatusResponse))["data"]
    cluster = next((e for e in status if e.get("type") == "cluster"), None)
    members = [e for e in status if e.get("type") == "node"]
    if not any(m.get("name") == node for m in members):
        raise ToolError(f"node '{node}' is not a cluster member")
    if cluster is not None:
        if not cluster.get("quorate"):
            raise ToolError("cluster is not quorate; refusing to reboot a node")
        down = [m["name"] for m in members if m.get("name") != node and not m.get("online")]
        if down:
            raise ToolError(f"other node(s) offline: {', '.join(down)}; reboot would risk quorum")
    return await get_client().fetch_and_validate(
        f"/nodes/{node}/status", ProxmoxUpdateConfigResponse,
        method="POST", params={"command": "reboot"},
    )
