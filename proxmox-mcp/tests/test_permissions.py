"""Tests for permission mapping in proxmox_mcp.api.permissions."""

import pytest
from proxmox_mcp.api.permissions import get_required_permission


BASE_URL = "https://proxmox.example.com:8006/api2/json"


class TestGetRequiredPermission:
    def test_get_nodes(self):
        url = f"{BASE_URL}/nodes"
        assert get_required_permission("GET", url, BASE_URL) == "Sys.Audit"

    def test_get_lxc_list(self):
        url = f"{BASE_URL}/nodes/pve1/lxc"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_get_qemu_list(self):
        url = f"{BASE_URL}/nodes/pve1/qemu"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_get_lxc_config(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/config"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_get_qemu_config(self):
        url = f"{BASE_URL}/nodes/pve1/qemu/200/config"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_get_lxc_interfaces(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/interfaces"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_post_lxc_power(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/status/start"
        assert get_required_permission("POST", url, BASE_URL) == "VM.PowerMgmt"

    def test_post_qemu_power(self):
        url = f"{BASE_URL}/nodes/pve1/qemu/200/status/stop"
        assert get_required_permission("POST", url, BASE_URL) == "VM.PowerMgmt"

    def test_get_storage(self):
        url = f"{BASE_URL}/nodes/pve1/storage"
        assert get_required_permission("GET", url, BASE_URL) == "Datastore.Audit"

    def test_get_storage_content(self):
        url = f"{BASE_URL}/nodes/pve1/storage/local/content"
        assert get_required_permission("GET", url, BASE_URL) == "Datastore.Audit"

    def test_get_task_status(self):
        url = f"{BASE_URL}/nodes/pve1/tasks/UPID123/status"
        assert get_required_permission("GET", url, BASE_URL) == "Sys.Audit"

    def test_get_task_log(self):
        url = f"{BASE_URL}/nodes/pve1/tasks/UPID123/log"
        assert get_required_permission("GET", url, BASE_URL) == "Sys.Audit"

    def test_post_create_lxc(self):
        url = f"{BASE_URL}/nodes/pve1/lxc"
        assert get_required_permission("POST", url, BASE_URL) == "VM.Allocate, Datastore.AllocateSpace"

    def test_post_create_qemu(self):
        url = f"{BASE_URL}/nodes/pve1/qemu"
        assert get_required_permission("POST", url, BASE_URL) == "VM.Allocate, Datastore.AllocateSpace"

    def test_post_lxc_exec(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/exec"
        assert get_required_permission("POST", url, BASE_URL) == "VM.Console"

    def test_put_cloudinit(self):
        url = f"{BASE_URL}/nodes/pve1/qemu/200/config"
        assert get_required_permission("PUT", url, BASE_URL) == "VM.Config.Cloudinit"

    def test_get_lxc_snapshots(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/snapshot"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_post_create_snapshot(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/snapshot"
        assert get_required_permission("POST", url, BASE_URL) == "VM.Snapshot"

    def test_post_rollback_snapshot(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/snapshot/snap1/rollback"
        assert get_required_permission("POST", url, BASE_URL) == "VM.Snapshot"

    def test_get_rrddata(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100/rrddata"
        assert get_required_permission("GET", url, BASE_URL) == "VM.Audit"

    def test_delete_lxc(self):
        url = f"{BASE_URL}/nodes/pve1/lxc/100"
        assert get_required_permission("DELETE", url, BASE_URL) == "VM.Allocate"

    def test_delete_qemu(self):
        url = f"{BASE_URL}/nodes/pve1/qemu/200"
        assert get_required_permission("DELETE", url, BASE_URL) == "VM.Allocate"

    def test_unknown_endpoint(self):
        url = f"{BASE_URL}/unknown/path"
        result = get_required_permission("GET", url, BASE_URL)
        assert "Unknown endpoint" in result

    def test_wrong_method_for_endpoint(self):
        url = f"{BASE_URL}/nodes"
        result = get_required_permission("DELETE", url, BASE_URL)
        assert "Unknown endpoint" in result
