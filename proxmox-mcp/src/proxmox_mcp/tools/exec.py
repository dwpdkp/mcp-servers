"""Exec tools — run commands inside LXC containers, or directly on a node,
via SSH.

The Proxmox REST API has no /exec endpoint for LXC containers, no QEMU
guest-agent passthrough, and no generic node shell. These tools SSH to the
Proxmox node and run the command there. Requires:
  - SSH access from the MCP server host to the Proxmox node hostname
  - PROXMOX_SSH_USER env var (default: ansible)
  - The node hostname must be resolvable / reachable via SSH
"""

from __future__ import annotations

import asyncio
import re
import shlex

from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.config import PROXMOX_SSH_USER
from proxmox_mcp.core.sanitization import sanitize_identifier, sanitize_vmid
from proxmox_mcp.server import mcp
from proxmox_mcp.tools import safety_checked

# node_exec is capped to read-only diagnostics — no qm/pct set, no destroy,
# no shutdown. Mutating changes go through update_instance_config or
# power_control instead, which carry their own safety tiers. Patterns are
# anchored so e.g. "qm config 115; rm -rf /" doesn't sneak past the "qm
# config" match (shlex.split below also blocks shell metacharacters entirely).
NODE_EXEC_ALLOWED_PATTERNS = [
    r"^qm\s+(status|config|list)\b",
    r"^qm\s+agent\s+\d+\s+ping$",
    r"^pct\s+(status|config|list)\b",
    r"^pvesm\s+status\b",
    r"^zpool\s+(status|list)\b",
    r"^df\s",
    r"^free\s",
    r"^uptime$",
    r"^uname\s",
]


@mcp.tool()
@safety_checked
async def execute_lxc_command(node: str, vmid: int, command: str, confirmed: bool = False) -> dict:
    """Run a shell command inside an LXC container.

    SSHes to the Proxmox node and runs `pct exec <vmid> -- <command>`.
    Requires SSH access to the node as PROXMOX_SSH_USER (default: ansible).
    """
    safe_node = sanitize_identifier(node)
    safe_vmid = sanitize_vmid(vmid)
    cmd_parts = shlex.split(command)
    # Shell-quote every token and join into a single string so SSH passes it
    # to the remote shell as one argument — prevents metacharacter injection
    # when SSH concatenates multi-arg remote commands via /bin/sh -c.
    remote_cmd = " ".join(
        shlex.quote(p) for p in ["sudo", "pct", "exec", str(safe_vmid), "--", *cmd_parts]
    )
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        f"{PROXMOX_SSH_USER}@{safe_node}",
        remote_cmd,
    ]

    proc = await asyncio.create_subprocess_exec(
        *ssh_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

    return {
        "vmid": safe_vmid,
        "node": safe_node,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }


@mcp.tool()
@safety_checked
async def node_exec(node: str, command: str) -> dict:
    """Run a read-only diagnostic command directly on a Proxmox node.

    SSHes to the node as PROXMOX_SSH_USER (sudo) and runs the command as-is
    (no pct/qm exec wrapper — this targets the HOST, not a guest). Restricted
    to an allowlist of read-only diagnostics (qm/pct status|config|list, qm
    agent ping, pvesm status, zpool status|list, df, free, uptime, uname) —
    there is no `confirmed=true` override, because this tool is for
    debugging/monitoring, not for making changes. Use update_instance_config
    or power_control for anything that mutates state.
    """
    for pattern in NODE_EXEC_ALLOWED_PATTERNS:
        if re.match(pattern, command.strip()):
            break
    else:
        raise ToolError(
            f"node_exec only allows read-only diagnostic commands. "
            f"'{command}' didn't match the allowlist "
            f"({', '.join(NODE_EXEC_ALLOWED_PATTERNS)}). "
            "For anything else, SSH to the node directly or use a purpose-built tool."
        )

    safe_node = sanitize_identifier(node)
    cmd_parts = shlex.split(command)
    remote_cmd = " ".join(shlex.quote(p) for p in ["sudo", *cmd_parts])
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        f"{PROXMOX_SSH_USER}@{safe_node}",
        remote_cmd,
    ]

    proc = await asyncio.create_subprocess_exec(
        *ssh_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

    return {
        "node": safe_node,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }
