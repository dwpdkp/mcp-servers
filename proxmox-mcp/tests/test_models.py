"""Tests for Pydantic model validation in proxmox_mcp.models."""

import pytest
from pydantic import ValidationError

from proxmox_mcp.models import (
    ProxmoxNode,
    ProxmoxNodeListResponse,
    ProxmoxLXC,
    ProxmoxLXCListResponse,
    ProxmoxVM,
    ProxmoxVMListResponse,
    ProxmoxInterface,
    ProxmoxInterfaceListResponse,
    ProxmoxTaskResponse,
    ProxmoxStorage,
    ProxmoxStorageListResponse,
    ProxmoxStorageContent,
    ProxmoxStorageContentListResponse,
    ProxmoxTaskStatus,
    ProxmoxTaskStatusResponse,
    ProxmoxConfigResponse,
    ProxmoxTaskLogLine,
    ProxmoxTaskLogResponse,
    ProxmoxSnapshot,
    ProxmoxSnapshotListResponse,
    ProxmoxResourceUsageLine,
    ProxmoxResourceUsageResponse,
    ProxmoxExecResponse,
)


# --- ProxmoxNode / ProxmoxNodeListResponse ---

class TestProxmoxNode:
    def test_valid_minimal(self):
        node = ProxmoxNode(node="pve1", status="online", maxcpu=4, maxmem=8_000_000)
        assert node.node == "pve1"
        assert node.cpu is None
        assert node.mem is None
        assert node.uptime is None

    def test_valid_full(self):
        node = ProxmoxNode(
            node="pve1", status="online", cpu=0.42, maxcpu=8,
            mem=4_000_000, maxmem=16_000_000, uptime=86400,
        )
        assert node.cpu == 0.42
        assert node.uptime == 86400

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ProxmoxNode(node="pve1", status="online")  # missing maxcpu, maxmem

    def test_list_response(self):
        resp = ProxmoxNodeListResponse(data=[
            {"node": "pve1", "status": "online", "maxcpu": 4, "maxmem": 8_000_000},
        ])
        assert len(resp.data) == 1

    def test_list_response_empty(self):
        resp = ProxmoxNodeListResponse(data=[])
        assert resp.data == []


# --- ProxmoxLXC / ProxmoxLXCListResponse ---

class TestProxmoxLXC:
    def test_valid_minimal(self):
        lxc = ProxmoxLXC(vmid=100, status="running")
        assert lxc.vmid == 100
        assert lxc.name is None

    def test_valid_full(self):
        lxc = ProxmoxLXC(vmid=100, name="web01", status="running", cpus=2, maxmem=1024, uptime=3600)
        assert lxc.name == "web01"

    def test_missing_status(self):
        with pytest.raises(ValidationError):
            ProxmoxLXC(vmid=100)

    def test_list_response(self):
        resp = ProxmoxLXCListResponse(data=[{"vmid": 100, "status": "stopped"}])
        assert resp.data[0].vmid == 100


# --- ProxmoxVM / ProxmoxVMListResponse ---

class TestProxmoxVM:
    def test_valid_minimal(self):
        vm = ProxmoxVM(vmid=200, status="stopped")
        assert vm.name is None

    def test_valid_full(self):
        vm = ProxmoxVM(vmid=200, name="db01", status="running", cpus=4, maxmem=4096, uptime=7200)
        assert vm.cpus == 4

    def test_missing_vmid(self):
        with pytest.raises(ValidationError):
            ProxmoxVM(status="running")

    def test_list_response(self):
        resp = ProxmoxVMListResponse(data=[{"vmid": 200, "status": "running"}])
        assert len(resp.data) == 1


# --- ProxmoxInterface / ProxmoxInterfaceListResponse ---

class TestProxmoxInterface:
    def test_valid_minimal(self):
        iface = ProxmoxInterface(name="eth0", hwaddr="AA:BB:CC:DD:EE:FF")
        assert iface.inet is None

    def test_valid_full(self):
        iface = ProxmoxInterface(
            name="eth0", hwaddr="AA:BB:CC:DD:EE:FF",
            inet="10.0.0.2/24", inet6="fe80::1/64",
        )
        assert iface.inet == "10.0.0.2/24"

    def test_missing_hwaddr(self):
        with pytest.raises(ValidationError):
            ProxmoxInterface(name="eth0")

    def test_list_response(self):
        resp = ProxmoxInterfaceListResponse(data=[
            {"name": "eth0", "hwaddr": "AA:BB:CC:DD:EE:FF"},
        ])
        assert resp.data[0].name == "eth0"


# --- ProxmoxStorage / ProxmoxStorageListResponse ---

class TestProxmoxStorage:
    def test_valid_minimal(self):
        s = ProxmoxStorage(storage="local", type="dir", content="iso,vztmpl")
        assert s.status is None

    def test_valid_full(self):
        s = ProxmoxStorage(
            storage="local-lvm", type="lvmthin", status="available",
            avail=50_000_000, total=100_000_000, used=50_000_000, content="rootdir,images",
        )
        assert s.avail == 50_000_000

    def test_missing_content(self):
        with pytest.raises(ValidationError):
            ProxmoxStorage(storage="local", type="dir")

    def test_list_response(self):
        resp = ProxmoxStorageListResponse(data=[
            {"storage": "local", "type": "dir", "content": "iso"},
        ])
        assert len(resp.data) == 1


# --- ProxmoxStorageContent / ProxmoxStorageContentListResponse ---

class TestProxmoxStorageContent:
    def test_valid(self):
        c = ProxmoxStorageContent(volid="local:iso/test.iso", format="iso", size=1024, content="iso")
        assert c.volid == "local:iso/test.iso"

    def test_missing_size(self):
        with pytest.raises(ValidationError):
            ProxmoxStorageContent(volid="local:iso/test.iso", format="iso", content="iso")

    def test_list_response(self):
        resp = ProxmoxStorageContentListResponse(data=[
            {"volid": "local:vztmpl/ubuntu.tar.gz", "format": "tgz", "size": 2048, "content": "vztmpl"},
        ])
        assert resp.data[0].content == "vztmpl"


# --- ProxmoxTaskResponse ---

class TestProxmoxTaskResponse:
    def test_valid(self):
        resp = ProxmoxTaskResponse(data="UPID:pve1:00001234:00000000:12345678:task:100:user@pam:")
        assert "UPID" in resp.data

    def test_missing_data(self):
        with pytest.raises(ValidationError):
            ProxmoxTaskResponse()


# --- ProxmoxTaskStatus / ProxmoxTaskStatusResponse ---

class TestProxmoxTaskStatus:
    def test_valid_running(self):
        ts = ProxmoxTaskStatus(status="running")
        assert ts.exitstatus is None

    def test_valid_stopped_ok(self):
        ts = ProxmoxTaskStatus(status="stopped", exitstatus="OK")
        assert ts.exitstatus == "OK"

    def test_response_wrapper(self):
        resp = ProxmoxTaskStatusResponse(data={"status": "running"})
        assert resp.data.status == "running"


# --- ProxmoxConfigResponse ---

class TestProxmoxConfigResponse:
    def test_valid(self):
        resp = ProxmoxConfigResponse(data={"hostname": "web01", "memory": 512})
        assert resp.data["hostname"] == "web01"

    def test_empty_data(self):
        resp = ProxmoxConfigResponse(data={})
        assert resp.data == {}


# --- ProxmoxTaskLogLine / ProxmoxTaskLogResponse ---

class TestProxmoxTaskLog:
    def test_valid_line(self):
        line = ProxmoxTaskLogLine(n=1, t="Starting task")
        assert line.n == 1

    def test_missing_text(self):
        with pytest.raises(ValidationError):
            ProxmoxTaskLogLine(n=1)

    def test_response(self):
        resp = ProxmoxTaskLogResponse(data=[{"n": 1, "t": "line1"}, {"n": 2, "t": "line2"}])
        assert len(resp.data) == 2


# --- ProxmoxSnapshot / ProxmoxSnapshotListResponse ---

class TestProxmoxSnapshot:
    def test_valid_minimal(self):
        snap = ProxmoxSnapshot(name="snap1", snaptime=1700000000)
        assert snap.description is None
        assert snap.parent is None

    def test_valid_full(self):
        snap = ProxmoxSnapshot(name="snap1", description="before upgrade", snaptime=1700000000, parent="snap0")
        assert snap.parent == "snap0"

    def test_missing_snaptime(self):
        with pytest.raises(ValidationError):
            ProxmoxSnapshot(name="snap1")

    def test_list_response(self):
        resp = ProxmoxSnapshotListResponse(data=[
            {"name": "snap1", "snaptime": 1700000000},
        ])
        assert resp.data[0].name == "snap1"


# --- ProxmoxResourceUsageLine / ProxmoxResourceUsageResponse ---

class TestProxmoxResourceUsage:
    def test_valid_minimal(self):
        line = ProxmoxResourceUsageLine(time=1700000000)
        assert line.cpu is None

    def test_valid_full(self):
        line = ProxmoxResourceUsageLine(time=1700000000, cpu=0.5, mem=1024, netin=100.0, netout=200.0)
        assert line.cpu == 0.5

    def test_missing_time(self):
        with pytest.raises(ValidationError):
            ProxmoxResourceUsageLine()

    def test_response(self):
        resp = ProxmoxResourceUsageResponse(data=[{"time": 1700000000, "cpu": 0.1}])
        assert resp.data[0].cpu == 0.1


# --- ProxmoxExecResponse ---

class TestProxmoxExecResponse:
    def test_valid(self):
        resp = ProxmoxExecResponse(data={"pid": 1234})
        assert resp.data["pid"] == 1234

    def test_missing_data(self):
        with pytest.raises(ValidationError):
            ProxmoxExecResponse()
