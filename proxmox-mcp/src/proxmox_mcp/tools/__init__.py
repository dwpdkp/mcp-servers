"""Tool utilities — safety decorator and client accessor."""

from __future__ import annotations

import functools
import shlex

from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.config import (
    logger, SAFETY_POLICY, PROXMOX_ALLOW_DANGER, proxmox_client, PROJECT_ROOT,
)
from proxmox_mcp.core.logger import redact_arguments
from proxmox_mcp.core.safety import check_safety
from proxmox_mcp.core.sanitization import sanitize_identifier, sanitize_vmid


def get_client():
    """Return the configured ProxmoxClient singleton."""
    return proxmox_client


def get_project_root():
    """Return the project root path."""
    return PROJECT_ROOT


def safety_checked(fn):
    """Decorator that enforces safety checks, input sanitization, and logging.

    Apply below @mcp.tool() so FastMCP sees the original signature for schema
    generation, but calls route through this wrapper at runtime.
    """
    @functools.wraps(fn)
    async def wrapper(**kwargs):
        # 1. Redacted logging
        redacted = redact_arguments(kwargs)
        logger.info(f"Tool Call: {fn.__name__} with args: {redacted}")

        # 2. Safety check (pops confirmed, raises ToolError if blocked)
        confirmed = kwargs.pop("confirmed", False)
        check_safety(fn.__name__, kwargs, confirmed, SAFETY_POLICY, PROXMOX_ALLOW_DANGER)

        # 3. Argument sanitization
        if "node" in kwargs:
            kwargs["node"] = sanitize_identifier(kwargs["node"])
        if "vmid" in kwargs:
            kwargs["vmid"] = sanitize_vmid(kwargs["vmid"])
        if "storage" in kwargs:
            kwargs["storage"] = sanitize_identifier(kwargs["storage"])
        if "upid" in kwargs:
            kwargs["upid"] = sanitize_identifier(kwargs["upid"], allow_colons=True)
        if "snapname" in kwargs:
            kwargs["snapname"] = sanitize_identifier(kwargs["snapname"])
        if "confirm_vmid" in kwargs:
            kwargs["confirm_vmid"] = sanitize_vmid(kwargs["confirm_vmid"])

        # 4. Shell command hardening
        if fn.__name__ == "execute_lxc_command" and "command" in kwargs:
            tokens = shlex.split(kwargs["command"])
            kwargs["command"] = shlex.join(tokens)

        return await fn(**kwargs)
    return wrapper
