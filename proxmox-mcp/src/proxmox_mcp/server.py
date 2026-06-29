"""MCP server — FastMCP instance and entry point."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("proxmox-mcp")

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
