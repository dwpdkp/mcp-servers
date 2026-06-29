# Proxmox MCP Requirements

## 1. Functional Requirements

- **Authentication:** Proxmox API Tokens for stateless, secure communication.
- **Resource Discovery:** List nodes, VMs (QEMU), containers (LXC), storage pools, templates, and network interfaces.
- **Instance Lifecycle:** Start, stop, shutdown, reboot, create, and delete VMs and containers.
- **Snapshots:** Create, list, and rollback snapshots for VMs and containers.
- **Cloud-init:** Configure user, SSH keys, and network settings on VMs.
- **Command Execution:** Run shell commands inside LXC containers.
- **Metrics:** Retrieve CPU, memory, network, and disk usage.
- **Task Monitoring:** Check status and logs of background Proxmox operations.

## 2. Technical Requirements

- **Language:** Python 3.10+.
- **Framework:** FastMCP (MCP SDK for Python).
- **Transport:** Standard I/O (stdio) for local CLI compatibility.
- **Validation:** Pydantic models for all API responses. Divergence returns `API_CONTRACT_DIVERGENCE`.
- **Error Handling:** Clear, actionable error messages (e.g., "Node 'pve2' is offline").
- **No-Sudo:** Runs as a standard user, no elevated privileges required.

## 3. Security Requirements

- **Safety Tiers:** Tools classified as safe, restricted, or critical with appropriate confirmation gates.
- **Input Sanitization:** All identifiers validated against strict patterns; shell commands parsed via `shlex`.
- **Log Redaction:** Passwords, tokens, SSH keys, and network configs masked in all log output.
