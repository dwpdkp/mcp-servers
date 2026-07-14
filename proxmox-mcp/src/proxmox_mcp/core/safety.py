import json
import logging
import os
import re
from typing import Any, Dict, Optional

from mcp.server.fastmcp.exceptions import ToolError

logger = logging.getLogger("proxmox-mcp")


def load_safety_policy(project_root: str) -> Dict[str, Any]:
    """Loads the safety policy from a JSON file."""
    path = os.path.join(project_root, "config", "safety_policy.json")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load safety_policy.json: {e}")
        return {"safe_tools": [], "safe_command_patterns": []}


def check_safety(tool_name: str, args: Optional[Dict[str, Any]], confirmed: bool, policy: Dict[str, Any], allow_danger: bool) -> None:
    """Enforces the safety policy. Raises ToolError if the action is blocked."""
    if tool_name in policy.get("critical_tools", []):
        if allow_danger and confirmed:
            logger.info(f"SECURITY: Critical action '{tool_name}' proceeding with PROXMOX_ALLOW_DANGER and user confirmation.")
            return
        logger.warning(f"SECURITY: Blocked critical action '{tool_name}' (allow_danger={allow_danger}, confirmed={confirmed}).")
        raise ToolError(
            f"SECURITY ALERT: The tool '{tool_name}' is a critical-tier action and requires BOTH "
            "the PROXMOX_ALLOW_DANGER environment variable to be set to 'true' AND explicit user "
            "confirmation ('confirmed=true') to execute. Ask the user for permission first."
        )

    if allow_danger:
        return

    if tool_name in policy.get("safe_tools", []):
        return

    if tool_name == "execute_lxc_command" and args and "command" in args:
        cmd = args["command"]
        for pattern in policy.get("safe_command_patterns", []):
            if re.match(pattern, cmd):
                return

    if confirmed:
        logger.info(f"SECURITY: Action '{tool_name}' proceeding with user confirmation.")
        return

    logger.warning(f"SECURITY: Blocked restricted action '{tool_name}'.")
    raise ToolError(
        f"SECURITY ALERT: The tool '{tool_name}' is restricted by your Safety Policy.\n"
        "To execute this action, you must explicitly confirm your intent to the user.\n"
        "Please ask the user for permission. If they agree, call this tool again with the parameter 'confirmed=true'."
    )
