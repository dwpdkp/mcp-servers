# Proxmox API Manifest

This document tracks the "Contract" between this MCP server and the Proxmox VE REST API. Every tool implemented in the MCP server must be registered here.

## Verified Proxmox Versions
| Version | Last Tested | Status |
| :--- | :--- | :--- |
| `pve-manager/8.1.4` | 2024-04-06 | Initial Target |

---

## Tool: `list_nodes`
**MCP Tool Name:** `list_nodes`  
**Proxmox Endpoint:** `GET /api2/json/nodes`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `node` | `string` | The hostname of the node | Yes |
| `status` | `string` | online/offline | Yes |
| `cpu` | `number` | Current CPU usage (0.0 - 1.0) | No |
| `maxcpu` | `integer` | Total available CPU cores | Yes |
| `mem` | `integer` | Current memory usage (bytes) | No |
| `maxmem` | `integer` | Total available memory (bytes) | Yes |
| `uptime` | `integer` | Uptime in seconds | No |

### Validation Logic
- **Success:** Returns a list of node objects.
- **Contract Violation:** If `node` or `status` is missing, the tool must report a `API_CONTRACT_DIVERGENCE` error to the AI.

---

## Tool: `list_lxc_containers`
**MCP Tool Name:** `list_lxc_containers`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/lxc`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `vmid` | `integer` | The unique ID of the container | Yes |
| `name` | `string` | The hostname/name of the LXC | No |
| `status` | `string` | running/stopped | Yes |
| `cpus` | `integer` | Configured CPU cores | No |
| `maxmem` | `integer` | Configured memory (bytes) | No |
| `uptime` | `integer` | Uptime in seconds | No |

### Validation Logic
- **Success:** Returns a list of LXC objects for a specific node.
- **Contract Violation:** If `vmid` or `status` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `list_vms`
**MCP Tool Name:** `list_vms`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/qemu`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `vmid` | `integer` | The unique ID of the VM | Yes |
| `name` | `string` | The hostname/name of the VM | No |
| `status` | `string` | running/stopped | Yes |
| `cpus` | `integer` | Configured CPU cores | No |
| `maxmem` | `integer` | Configured memory (bytes) | No |
| `uptime` | `integer` | Uptime in seconds | No |

### Validation Logic
- **Success:** Returns a list of QEMU VM objects for a specific node.
- **Contract Violation:** If `vmid` or `status` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `get_lxc_interfaces`
**MCP Tool Name:** `get_lxc_interfaces`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/lxc/{vmid}/interfaces`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `name` | `string` | Interface name (e.g., eth0) | Yes |
| `hwaddr` | `string` | MAC address | Yes |
| `inet` | `string` | IPv4 address with CIDR | No |
| `inet6` | `string` | IPv6 address with CIDR | No |

### Validation Logic
- **Success:** Returns the network interface list for an LXC.
- **Contract Violation:** If `name` or `hwaddr` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `power_control`
**MCP Tool Name:** `power_control`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/{type}/{vmid}/status/{action}`

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `node` | `string` | The node name |
| `vmid` | `integer` | The ID of the instance |
| `type` | `string` | `lxc` or `qemu` |
| `action` | `string` | `start`, `stop`, `shutdown`, `reboot` |

### Expected Response Schema
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `data` | `string` | The Task ID (UPID) for the operation | Yes |

### Validation Logic
- **Success:** Returns the UPID of the background task.
- **Contract Violation:** If `data` (UPID) is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `list_storage`
**MCP Tool Name:** `list_storage`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/storage`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `storage` | `string` | ID of the storage | Yes |
| `type` | `string` | Storage type (zfs, nfs, dir, etc.) | Yes |
| `status` | `string` | available/unavailable | No |
| `avail` | `integer` | Available space (bytes) | No |
| `total` | `integer` | Total space (bytes) | No |
| `used` | `integer` | Used space (bytes) | No |
| `content` | `string` | Allowed content types (comma-separated) | Yes |

### Validation Logic
- **Success:** Returns a list of storage units on a node.
- **Contract Violation:** If `storage` or `type` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `list_storage_content`
**MCP Tool Name:** `list_storage_content`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/storage/{storage}/content`

### Expected Response Schema (Data Array)
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `volid` | `string` | Unique volume ID (e.g., local:vztmpl/ubuntu...) | Yes |
| `format` | `string` | File format | Yes |
| `size` | `integer` | Size in bytes | Yes |
| `content` | `string` | Content type (vztmpl, iso, etc.) | Yes |

### Validation Logic
- **Success:** Returns a list of files (templates/ISOs) in a specific storage.
- **Contract Violation:** If `volid` or `content` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `get_task_status`
**MCP Tool Name:** `get_task_status`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/tasks/{upid}/status`

### Expected Response Schema
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `status` | `string` | Task status (running/stopped) | Yes |
| `exitstatus` | `string` | "OK" on success, or error message | No |

### Validation Logic
- **Success:** Returns the current lifecycle status of a background task.
- **Contract Violation:** If `status` is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `create_lxc`
**MCP Tool Name:** `create_lxc`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/lxc`

### Parameters
| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `node` | `string` | Target node name | Yes |
| `vmid` | `integer` | Unique ID for the new LXC | Yes |
| `ostemplate` | `string` | Path to template (e.g., local:vztmpl/ubuntu...) | Yes |
| `storage` | `string` | Target storage for rootfs (e.g., local-lvm) | Yes |
| `disk` | `integer` | Disk size in GB (default 8) | No |
| `memory` | `integer` | Memory in MB (default 512) | No |
| `cores` | `integer` | CPU cores (default 1) | No |
| `hostname` | `string` | Hostname for the container | No |
| `password` | `string` | Root password | Yes |
| `ssh-public-keys` | `string` | Public SSH keys (newline separated) | No |
| `net0` | `string` | Network config | Yes |

### Expected Response Schema
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `data` | `string` | The Task ID (UPID) for the creation process | Yes |

### Validation Logic
- **Success:** Returns the UPID of the creation task.
- **Contract Violation:** If `data` (UPID) is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `execute_lxc_command`
**MCP Tool Name:** `execute_lxc_command`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/lxc/{vmid}/exec`

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `command` | `string` | The shell command to run |

### Expected Response Schema
Returns a `PID` of the execution task.

---

## Tool: `get_instance_config`
**MCP Tool Name:** `get_instance_config`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/{type}/{vmid}/config`

### Expected Response Schema
Returns the current configuration (CPU, RAM, Network, etc.) of the specific instance.

---

## Tool: `get_task_log`
**MCP Tool Name:** `get_task_log`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/tasks/{upid}/log`

### Expected Response Schema
Returns a list of log lines from the background task execution.

---

## Tool: `delete_instance` (DESTRUCTIVE)
**MCP Tool Name:** `delete_instance`  
**Proxmox Endpoint:** `DELETE /api2/json/nodes/{node}/{type}/{vmid}`

### Security Layer: "YOLO Mode"
- **Default State:** This tool will return an error and refuse to execute unless the environment variable `PROXMOX_ALLOW_DANGER` is set to `true`.
- **Prompt Injection Protection:** Even if enabled, the tool requires a `confirm_vmid` parameter that MUST match the `vmid` to be deleted.

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `node` | `string` | Node name |
| `vmid` | `integer` | ID to delete |
| `type` | `string` | lxc/qemu |
| `confirm_vmid` | `integer` | Must match `vmid` to confirm intent |

---

## Tool: `create_vm`
**MCP Tool Name:** `create_vm`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/qemu`

### Parameters
| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `node` | `string` | Target node name | Yes |
| `vmid` | `integer` | Unique ID for the new VM | Yes |
| `name` | `string` | VM name | Yes |
| `memory` | `integer` | Memory in MB | No |
| `net0` | `string` | Network config (e.g. model=virtio,bridge=vmbr0) | No |
| `scsi0` | `string` | Disk config (e.g. local-lvm:32) | No |
| `onboot` | `boolean` | Start at boot | No |

### Expected Response Schema
| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `data` | `string` | The Task ID (UPID) for the creation process | Yes |

### Validation Logic
- **Success:** Returns the UPID of the creation task.
- **Contract Violation:** If `data` (UPID) is missing, report `API_CONTRACT_DIVERGENCE`.

---

## Tool: `set_vm_cloudinit`
**MCP Tool Name:** `set_vm_cloudinit`  
**Proxmox Endpoint:** `PUT /api2/json/nodes/{node}/qemu/{vmid}/config`

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `ciuser` | `string` | Cloud-init user |
| `cipassword` | `string` | Cloud-init password |
| `sshkeys` | `string` | URL-encoded public keys |
| `ipconfig0` | `string` | IPv4/v6 config (e.g. `ip=dhcp`) |

---

## Tool: `list_snapshots`
**MCP Tool Name:** `list_snapshots`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/{type}/{vmid}/snapshot`

---

## Tool: `create_snapshot`
**MCP Tool Name:** `create_snapshot`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/{type}/{vmid}/snapshot`

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `snapname` | `string` | Unique name for the snapshot |
| `description` | `string` | Optional description |

---

## Tool: `rollback_snapshot`
**MCP Tool Name:** `rollback_snapshot`  
**Proxmox Endpoint:** `POST /api2/json/nodes/{node}/{type}/{vmid}/snapshot/{snapname}/rollback`

---

## Tool: `get_resource_usage`
**MCP Tool Name:** `get_resource_usage`  
**Proxmox Endpoint:** `GET /api2/json/nodes/{node}/{type}/{vmid}/rrddata`

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `timeframe` | `string` | `hour`, `day`, `week`, `month`, `year` |

---

## Tool: `get_mcp_logs`
**MCP Tool Name:** `get_mcp_logs`  
**Description:** Fetches the internal execution logs of the MCP server itself. Use this to diagnose connection issues, contract violations, or internal errors.

### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `lines` | `integer` | Number of recent log lines to fetch (default 50) |

### Validation Logic
- **Success:** Returns the last N lines of the `proxmox-mcp.log` file.
