"""Exec tools — run commands inside LXC containers via SSH + pct exec.

The Proxmox REST API has no /exec endpoint for LXC containers. This tool
SSHes to the Proxmox node and runs `pct exec` instead. Requires:
  - SSH access from the MCP server host to the Proxmox node hostname
  - PROXMOX_SSH_USER env var (default: root)
  - The node hostname must be resolvable / reachable via SSH
"""

from __future__ import annotations

import asyncio
import shlex

from proxmox_mcp.config import PROXMOX_SSH_USER
from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked


@mcp.tool()
@safety_checked
async def execute_lxc_command(node: str, vmid: int, command: str, confirmed: bool = False) -> dict:
    """Run a shell command inside an LXC container.

    SSHes to the Proxmox node and runs `pct exec <vmid> -- <command>`.
    Requires SSH access to the node as PROXMOX_SSH_USER (default: root).
    """
    cmd_parts = shlex.split(command)
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        f"{PROXMOX_SSH_USER}@{node}",
        "sudo", "pct", "exec", str(vmid), "--",
        *cmd_parts,
    ]

    proc = await asyncio.create_subprocess_exec(
        *ssh_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

    return {
        "vmid": vmid,
        "node": node,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }
