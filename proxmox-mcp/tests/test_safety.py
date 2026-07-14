import pytest
from mcp.server.fastmcp.exceptions import ToolError
from proxmox_mcp.core.safety import check_safety


def test_safe_tool_passes(safety_policy):
    check_safety("list_nodes", {}, False, safety_policy, False)


def test_restricted_tool_blocked_without_confirmation(safety_policy):
    with pytest.raises(ToolError, match="restricted"):
        check_safety("power_control", {"node": "pve"}, False, safety_policy, False)


def test_restricted_tool_passes_with_confirmation(safety_policy):
    check_safety("power_control", {"node": "pve"}, True, safety_policy, False)


def test_allow_danger_bypasses_restricted_tools(safety_policy):
    check_safety("power_control", {"node": "pve"}, False, safety_policy, True)


def test_critical_tool_blocked_with_allow_danger_only(safety_policy):
    """allow_danger=True alone must NOT bypass a critical-tier tool (S-C1)."""
    with pytest.raises(ToolError, match="critical-tier"):
        check_safety("delete_instance", {"vmid": 100}, False, safety_policy, True)


def test_critical_tool_blocked_with_confirmed_only(safety_policy):
    """confirmed=True alone must NOT bypass a critical-tier tool (S-C1)."""
    with pytest.raises(ToolError, match="critical-tier"):
        check_safety("delete_instance", {"vmid": 100}, True, safety_policy, False)


def test_critical_tool_passes_with_both(safety_policy):
    check_safety("delete_instance", {"vmid": 100}, True, safety_policy, True)


def test_safe_command_pattern_passes(safety_policy):
    check_safety("execute_lxc_command", {"command": "ls -la"}, False, safety_policy, False)


def test_unsafe_command_blocked(safety_policy):
    with pytest.raises(ToolError):
        check_safety("execute_lxc_command", {"command": "rm -rf /"}, False, safety_policy, False)
