"""Tests for the safety_checked decorator from proxmox_mcp.tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp.server.fastmcp.exceptions import ToolError  # used in safety check tests


# We test the decorator in isolation by applying it to dummy async functions,
# without @mcp.tool(). We need to patch the config-level imports.


@pytest.fixture(autouse=True)
def _patch_config():
    """Patch config imports used by the decorator."""
    policy = {
        "safe_tools": ["safe_tool"],
        "safe_command_patterns": ["^ls($| )", "^pwd$"],
        "restricted_tools": ["restricted_tool"],
    }
    with (
        patch("proxmox_mcp.tools.SAFETY_POLICY", policy),
        patch("proxmox_mcp.tools.PROXMOX_ALLOW_DANGER", False),
        patch("proxmox_mcp.tools.logger", MagicMock()),
    ):
        yield


class TestSafetyCheckedDecorator:
    async def test_confirmed_is_popped(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(confirmed=True, node="pve1")
        # confirmed should not be passed to the inner function
        inner.assert_called_once()
        call_kwargs = inner.call_args[1]
        assert "confirmed" not in call_kwargs
        assert call_kwargs["node"] == "pve1"

    async def test_node_sanitized(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(node="pve1")
        assert inner.call_args[1]["node"] == "pve1"

    async def test_node_rejects_injection(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock()
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        with pytest.raises(ValueError, match="Invalid identifier"):
            await wrapped(node="pve1; rm -rf /")

    async def test_vmid_sanitized(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(vmid=100)
        assert inner.call_args[1]["vmid"] == 100

    async def test_vmid_rejects_invalid(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock()
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        with pytest.raises(ValueError, match="Invalid VMID"):
            await wrapped(vmid=-1)

    async def test_storage_sanitized(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(storage="local-lvm")
        assert inner.call_args[1]["storage"] == "local-lvm"

    async def test_upid_allows_colons(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(upid="UPID:pve1:00001234")
        assert inner.call_args[1]["upid"] == "UPID:pve1:00001234"

    async def test_snapname_sanitized(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "safe_tool"
        wrapped = safety_checked(inner)

        await wrapped(snapname="snap1")
        assert inner.call_args[1]["snapname"] == "snap1"

    async def test_restricted_tool_blocked_without_confirmation(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock()
        inner.__name__ = "restricted_tool"
        wrapped = safety_checked(inner)

        with pytest.raises(ToolError, match="SECURITY ALERT"):
            await wrapped()

    async def test_restricted_tool_passes_with_confirmation(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "restricted_tool"
        wrapped = safety_checked(inner)

        result = await wrapped(confirmed=True)
        assert result == "ok"

    async def test_shlex_hardening_on_execute_lxc_command(self):
        from proxmox_mcp.tools import safety_checked

        inner = AsyncMock(return_value="ok")
        inner.__name__ = "execute_lxc_command"
        wrapped = safety_checked(inner)

        # shlex.split + shlex.join normalizes the command
        await wrapped(command="ls   -la   /tmp", confirmed=True)
        assert inner.call_args[1]["command"] == "ls -la /tmp"
