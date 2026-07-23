from pydantic import BaseModel, Field, ValidationError
from typing import Any, Dict, List, Optional


class ProxmoxNode(BaseModel):
    """
    Contract for the Proxmox Node response.
    Based on docs/api_manifest.md
    """
    node: str = Field(..., description="The hostname of the node")
    status: str = Field(..., description="online/offline")
    cpu: Optional[float] = Field(None, description="Current CPU usage (0.0 - 1.0)")
    maxcpu: int = Field(..., description="Total available CPU cores")
    mem: Optional[int] = Field(None, description="Current memory usage (bytes)")
    maxmem: int = Field(..., description="Total available memory (bytes)")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")


class ProxmoxNodeListResponse(BaseModel):
    data: List[ProxmoxNode]


class ProxmoxLXC(BaseModel):
    """
    Contract for the Proxmox LXC response.
    Based on docs/api_manifest.md
    """
    vmid: int = Field(..., description="The unique ID of the container")
    name: Optional[str] = Field(None, description="The hostname/name of the LXC")
    status: str = Field(..., description="running/stopped")
    cpus: Optional[int] = Field(None, description="Configured CPU cores")
    maxmem: Optional[int] = Field(None, description="Configured memory (bytes)")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")


class ProxmoxLXCListResponse(BaseModel):
    data: List[ProxmoxLXC]


class ProxmoxVM(BaseModel):
    """
    Contract for the Proxmox QEMU VM response.
    Based on docs/api_manifest.md
    """
    vmid: int = Field(..., description="The unique ID of the VM")
    name: Optional[str] = Field(None, description="The hostname/name of the VM")
    status: str = Field(..., description="running/stopped")
    cpus: Optional[int] = Field(None, description="Configured CPU cores")
    maxmem: Optional[int] = Field(None, description="Configured memory (bytes)")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")


class ProxmoxVMListResponse(BaseModel):
    data: List[ProxmoxVM]


class ProxmoxInterface(BaseModel):
    """
    Contract for Proxmox LXC Network Interface.
    Based on docs/api_manifest.md
    """
    name: str = Field(..., description="Interface name (e.g., eth0)")
    hwaddr: str = Field(..., description="MAC address")
    inet: Optional[str] = Field(None, description="IPv4 address with CIDR")
    inet6: Optional[str] = Field(None, description="IPv6 address with CIDR")


class ProxmoxInterfaceListResponse(BaseModel):
    data: List[ProxmoxInterface]


class ProxmoxTaskResponse(BaseModel):
    data: str = Field(..., description="The UPID (Unique Process ID) of the task")


class ProxmoxUpdateConfigResponse(BaseModel):
    """PUT .../config returns null on a synchronous change, or a UPID when the
    change (e.g. a disk resize) requires an async task."""
    data: Optional[str] = Field(None, description="UPID if the change was async, else null")


class ProxmoxStorage(BaseModel):
    """
    Contract for Proxmox Storage.
    Based on docs/api_manifest.md
    """
    storage: str = Field(..., description="ID of the storage")
    type: str = Field(..., description="Storage type (zfs, nfs, dir, etc.)")
    status: Optional[str] = Field(None, description="available/unavailable")
    avail: Optional[int] = Field(None, description="Available space (bytes)")
    total: Optional[int] = Field(None, description="Total space (bytes)")
    used: Optional[int] = Field(None, description="Used space (bytes)")
    content: str = Field(..., description="Allowed content types (comma-separated)")


class ProxmoxStorageListResponse(BaseModel):
    data: List[ProxmoxStorage]


class ProxmoxStorageContent(BaseModel):
    """
    Contract for Proxmox Storage Content (ISOs/Templates).
    Based on docs/api_manifest.md
    """
    volid: str = Field(..., description="Unique volume ID")
    format: str = Field(..., description="File format")
    size: int = Field(..., description="Size in bytes")
    content: str = Field(..., description="Content type (vztmpl, iso, etc.)")


class ProxmoxStorageContentListResponse(BaseModel):
    data: List[ProxmoxStorageContent]


class ProxmoxTaskStatus(BaseModel):
    status: str = Field(..., description="Task status (running/stopped)")
    exitstatus: Optional[str] = Field(None, description="'OK' on success, or error message")


class ProxmoxTaskStatusResponse(BaseModel):
    data: ProxmoxTaskStatus


class ProxmoxConfigResponse(BaseModel):
    """Generic configuration for LXC or QEMU. Config keys vary, so we use a dict."""
    data: Dict[str, Any]


class ProxmoxTaskLogLine(BaseModel):
    n: int = Field(..., description="Line number")
    t: str = Field(..., description="Log message text")


class ProxmoxTaskLogResponse(BaseModel):
    data: List[ProxmoxTaskLogLine]


class ProxmoxSnapshot(BaseModel):
    name: str = Field(..., description="Unique name of the snapshot")
    description: Optional[str] = Field(None, description="Snapshot description")
    snaptime: Optional[int] = Field(None, description="Snapshot creation time (timestamp)")
    parent: Optional[str] = Field(None, description="Parent snapshot name")


class ProxmoxSnapshotListResponse(BaseModel):
    data: List[ProxmoxSnapshot]


class ProxmoxResourceUsageLine(BaseModel):
    time: int = Field(..., description="Timestamp of the data point")
    cpu: Optional[float] = Field(None, description="CPU usage (0.0 - 1.0)")
    mem: Optional[float] = Field(None, description="Memory usage (bytes)")
    netin: Optional[float] = Field(None, description="Network input (bytes/s)")
    netout: Optional[float] = Field(None, description="Network output (bytes/s)")


class ProxmoxResourceUsageResponse(BaseModel):
    data: List[ProxmoxResourceUsageLine]


class ProxmoxExecResponse(BaseModel):
    data: Dict[str, Any]  # Contains PID and UPID
