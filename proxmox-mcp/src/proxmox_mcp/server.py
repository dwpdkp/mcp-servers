"""MCP server — FastMCP instance and entry point."""

import os
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

# Two instances of this server usually run side by side (e.g. work + homelab).
# PROXMOX_ENV labels which one this is so tool search and the model can tell them apart.
_env = os.environ.get("PROXMOX_ENV") or urlparse(os.environ.get("PROXMOX_URL", "")).hostname or "unknown"

mcp = FastMCP(
    "proxmox-mcp",
    instructions=(
        f"Proxmox VE management for the {_env} environment. Lists nodes, VMs (QEMU) and LXC "
        "containers, reads configs, storage, tasks and metrics, and manages snapshots, power, "
        "cloud-init and instance creation. Destructive tools require confirmed=true."
    ),
)

# Import tool modules to trigger @mcp.tool() registration.
# These must come after mcp is defined to avoid circular imports.
import proxmox_mcp.tools.discovery  # noqa: E402, F401
import proxmox_mcp.tools.lifecycle  # noqa: E402, F401
import proxmox_mcp.tools.snapshots  # noqa: E402, F401
import proxmox_mcp.tools.cloudinit  # noqa: E402, F401
import proxmox_mcp.tools.exec  # noqa: E402, F401
import proxmox_mcp.tools.metrics  # noqa: E402, F401


def main():
    """Entry point for `python -m proxmox_mcp` and the `proxmox-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
