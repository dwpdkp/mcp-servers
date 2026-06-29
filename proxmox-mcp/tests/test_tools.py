"""Tests for tool functions with mocked ProxmoxClient.

All tools follow the same pattern: call get_client().fetch_and_validate(endpoint, Model).
We patch get_client to return an AsyncMock and verify the correct endpoint, model class,
method, and params are passed.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.models import (
    ProxmoxNodeListResponse,
    ProxmoxLXCListResponse,
    ProxmoxVMListResponse,
    ProxmoxConfigResponse,
    ProxmoxInterfaceListResponse,
    ProxmoxStorageListResponse,
    ProxmoxStorageContentListResponse,
    ProxmoxTaskStatusResponse,
    ProxmoxTaskLogResponse,
    ProxmoxTaskResponse,
    ProxmoxSnapshotListResponse,
    ProxmoxResourceUsageResponse,
    ProxmoxExecResponse,
)


@pytest.fixture
def mock_client():
    """Mock fetch_and_validate at the class level so all client instances use it."""
    mock_fav = AsyncMock(return_value={"data": []})
    with patch("proxmox_mcp.api.client.ProxmoxClient.fetch_and_validate", mock_fav):
        yield mock_fav


# We also need to patch safety-related imports so tools don't hit real config.
# The safety_checked decorator reads SAFETY_POLICY and PROXMOX_ALLOW_DANGER from config.
# We patch them to allow all tools through.
@pytest.fixture(autouse=True)
def _bypass_safety():
    with patch("proxmox_mcp.tools.PROXMOX_ALLOW_DANGER", True):
        yield


# --- Discovery tools ---

class TestDiscoveryTools:
    async def test_list_nodes(self, mock_client):
        from proxmox_mcp.tools.discovery import list_nodes
        await list_nodes()
        mock_client.assert_called_once_with(
            "/nodes", ProxmoxNodeListResponse,
        )

    async def test_list_lxc_containers(self, mock_client):
        from proxmox_mcp.tools.discovery import list_lxc_containers
        await list_lxc_containers(node="pve1")
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc", ProxmoxLXCListResponse,
        )

    async def test_list_vms(self, mock_client):
        from proxmox_mcp.tools.discovery import list_vms
        await list_vms(node="pve1")
        mock_client.assert_called_once_with(
            "/nodes/pve1/qemu", ProxmoxVMListResponse,
        )

    async def test_get_instance_config_lxc(self, mock_client):
        from proxmox_mcp.tools.discovery import get_instance_config
        await get_instance_config(node="pve1", vmid=100, type="lxc")
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100/config", ProxmoxConfigResponse,
        )

    async def test_get_instance_config_qemu(self, mock_client):
        from proxmox_mcp.tools.discovery import get_instance_config
        await get_instance_config(node="pve1", vmid=200, type="qemu")
        mock_client.assert_called_once_with(
            "/nodes/pve1/qemu/200/config", ProxmoxConfigResponse,
        )

    async def test_get_lxc_interfaces(self, mock_client):
        from proxmox_mcp.tools.discovery import get_lxc_interfaces
        await get_lxc_interfaces(node="pve1", vmid=100)
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100/interfaces", ProxmoxInterfaceListResponse,
        )

    async def test_list_storage(self, mock_client):
        from proxmox_mcp.tools.discovery import list_storage
        await list_storage(node="pve1")
        mock_client.assert_called_once_with(
            "/nodes/pve1/storage", ProxmoxStorageListResponse,
        )

    async def test_list_storage_content(self, mock_client):
        from proxmox_mcp.tools.discovery import list_storage_content
        await list_storage_content(node="pve1", storage="local")
        mock_client.assert_called_once_with(
            "/nodes/pve1/storage/local/content", ProxmoxStorageContentListResponse,
        )

    async def test_get_task_status(self, mock_client):
        from proxmox_mcp.tools.discovery import get_task_status
        await get_task_status(node="pve1", upid="UPID:pve1:00001234")
        mock_client.assert_called_once_with(
            "/nodes/pve1/tasks/UPID:pve1:00001234/status", ProxmoxTaskStatusResponse,
        )

    async def test_get_task_log(self, mock_client):
        from proxmox_mcp.tools.discovery import get_task_log
        await get_task_log(node="pve1", upid="UPID:pve1:00001234")
        mock_client.assert_called_once_with(
            "/nodes/pve1/tasks/UPID:pve1:00001234/log", ProxmoxTaskLogResponse,
        )


# --- Lifecycle tools ---

class TestLifecycleTools:
    async def test_power_control(self, mock_client):
        from proxmox_mcp.tools.lifecycle import power_control
        await power_control(node="pve1", vmid=100, type="lxc", action="start", confirmed=True)
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100/status/start",
            ProxmoxTaskResponse, method="POST",
        )

    async def test_create_lxc_minimal(self, mock_client):
        from proxmox_mcp.tools.lifecycle import create_lxc
        await create_lxc(
            node="pve1", vmid=100, ostemplate="local:vztmpl/ubuntu.tar.gz",
            storage="local-lvm", password="secret", net0="name=eth0,bridge=vmbr0",
            confirmed=True,
        )
        call_args = mock_client.call_args
        assert call_args[0][0] == "/nodes/pve1/lxc"
        assert call_args[1]["method"] == "POST"
        params = call_args[1]["params"]
        assert params["vmid"] == 100
        assert params["ostemplate"] == "local:vztmpl/ubuntu.tar.gz"
        assert params["rootfs"] == "local-lvm:8"  # default disk=8
        assert "hostname" not in params  # not provided

    async def test_create_lxc_with_optionals(self, mock_client):
        from proxmox_mcp.tools.lifecycle import create_lxc
        await create_lxc(
            node="pve1", vmid=100, ostemplate="local:vztmpl/ubuntu.tar.gz",
            storage="local-lvm", password="secret", net0="name=eth0,bridge=vmbr0",
            hostname="web01", ssh_public_keys="ssh-rsa AAAA...", confirmed=True,
        )
        params = mock_client.call_args[1]["params"]
        assert params["hostname"] == "web01"
        assert params["ssh-public-keys"] == "ssh-rsa AAAA..."

    async def test_create_vm_minimal(self, mock_client):
        from proxmox_mcp.tools.lifecycle import create_vm
        await create_vm(node="pve1", vmid=200, name="db01", confirmed=True)
        call_args = mock_client.call_args
        params = call_args[1]["params"]
        assert params == {"vmid": 200, "name": "db01"}

    async def test_create_vm_with_optionals(self, mock_client):
        from proxmox_mcp.tools.lifecycle import create_vm
        await create_vm(
            node="pve1", vmid=200, name="db01",
            memory=4096, net0="model=virtio,bridge=vmbr0",
            scsi0="local-lvm:32", onboot=True, confirmed=True,
        )
        params = mock_client.call_args[1]["params"]
        assert params["memory"] == 4096
        assert params["onboot"] is True

    async def test_delete_instance_vmid_mismatch(self, mock_client):
        from proxmox_mcp.tools.lifecycle import delete_instance
        with pytest.raises(ToolError, match="VMID mismatch"):
            await delete_instance(node="pve1", vmid=100, type="lxc", confirm_vmid=999, confirmed=True)

    async def test_delete_instance_success(self, mock_client):
        from proxmox_mcp.tools.lifecycle import delete_instance
        await delete_instance(node="pve1", vmid=100, type="lxc", confirm_vmid=100, confirmed=True)
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100",
            ProxmoxTaskResponse, method="DELETE",
        )


# --- Snapshot tools ---

class TestSnapshotTools:
    async def test_list_snapshots(self, mock_client):
        from proxmox_mcp.tools.snapshots import list_snapshots
        await list_snapshots(node="pve1", vmid=100, type="lxc")
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100/snapshot",
            ProxmoxSnapshotListResponse,
        )

    async def test_create_snapshot_minimal(self, mock_client):
        from proxmox_mcp.tools.snapshots import create_snapshot
        await create_snapshot(node="pve1", vmid=100, type="lxc", snapname="snap1", confirmed=True)
        call_args = mock_client.call_args
        assert call_args[1]["params"] == {"snapname": "snap1"}

    async def test_create_snapshot_with_description(self, mock_client):
        from proxmox_mcp.tools.snapshots import create_snapshot
        await create_snapshot(
            node="pve1", vmid=100, type="lxc", snapname="snap1",
            description="before upgrade", confirmed=True,
        )
        params = mock_client.call_args[1]["params"]
        assert params["description"] == "before upgrade"

    async def test_rollback_snapshot(self, mock_client):
        from proxmox_mcp.tools.snapshots import rollback_snapshot
        await rollback_snapshot(node="pve1", vmid=100, type="lxc", snapname="snap1", confirmed=True)
        mock_client.assert_called_once_with(
            "/nodes/pve1/lxc/100/snapshot/snap1/rollback",
            ProxmoxTaskResponse, method="POST",
        )


# --- Cloud-init tools ---

class TestCloudinitTools:
    async def test_set_vm_cloudinit_minimal(self, mock_client):
        from proxmox_mcp.tools.cloudinit import set_vm_cloudinit
        await set_vm_cloudinit(node="pve1", vmid=200, ciuser="root", confirmed=True)
        params = mock_client.call_args[1]["params"]
        assert params == {"ciuser": "root"}

    async def test_set_vm_cloudinit_all_params(self, mock_client):
        from proxmox_mcp.tools.cloudinit import set_vm_cloudinit
        await set_vm_cloudinit(
            node="pve1", vmid=200, ciuser="root", cipassword="pass",
            sshkeys="ssh-rsa AAA", ipconfig0="ip=dhcp", confirmed=True,
        )
        params = mock_client.call_args[1]["params"]
        assert params["cipassword"] == "pass"
        assert params["sshkeys"] == "ssh-rsa AAA"
        assert params["ipconfig0"] == "ip=dhcp"

    async def test_set_vm_cloudinit_none_excluded(self, mock_client):
        from proxmox_mcp.tools.cloudinit import set_vm_cloudinit
        await set_vm_cloudinit(node="pve1", vmid=200, confirmed=True)
        params = mock_client.call_args[1]["params"]
        assert params == {}


# --- Exec tools ---

class TestExecTools:
    async def test_execute_lxc_command(self, mock_client):
        from proxmox_mcp.tools.exec import execute_lxc_command
        await execute_lxc_command(node="pve1", vmid=100, command="ls -la", confirmed=True)
        call_args = mock_client.call_args
        assert call_args[0][0] == "/nodes/pve1/lxc/100/exec"
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["params"]["command"] == "ls -la"


# --- Metrics tools ---

class TestMetricsTools:
    async def test_get_resource_usage(self, mock_client):
        from proxmox_mcp.tools.metrics import get_resource_usage
        await get_resource_usage(node="pve1", vmid=100, type="lxc", timeframe="hour")
        call_args = mock_client.call_args
        assert call_args[0][0] == "/nodes/pve1/lxc/100/rrddata"
        assert call_args[1]["params"] == {"timeframe": "hour"}
