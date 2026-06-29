# Proxmox MCP Architecture

This project uses the Model Context Protocol (MCP) to bridge AI agents with a Proxmox VE server.

## System Components

1. **AI Client (MCP Host):** Claude Desktop, Claude Code, or any MCP-compatible client.
2. **MCP Server (Local):** A Python service running on the management machine. It translates tool calls into Proxmox API requests.
3. **Transport Layer:** Standard Input/Output (stdio). The AI client starts the MCP server as a subprocess and communicates via JSON-RPC.
4. **Proxmox VE API:** The target server. The MCP server makes HTTPS requests to the Proxmox REST API (`https://<ip>:8006/api2/json`).

## Data Flow

1. **User Request:** "List all running containers on Proxmox."
2. **AI Reasoning:** The AI identifies that it has a tool named `list_lxc_containers`.
3. **Tool Call:** The AI sends a JSON-RPC request to the local MCP server.
4. **API Execution:** The MCP server authenticates via API Token and fetches data from Proxmox.
5. **Contract Validation:** The response is validated against a Pydantic model. Mismatches return `API_CONTRACT_DIVERGENCE`.
6. **Context Injection:** The MCP server returns the validated data to the AI.
7. **Natural Language Response:** The AI formats the data for the user.

## Security Model

- **Local Only:** The MCP server runs locally; it is not exposed to the internet.
- **Token Based:** Authentication uses Proxmox API Tokens (User@Realm!TokenID) with restricted permissions.
- **Safety Tiers:** All 20 tools are classified as safe, restricted, or critical. Destructive operations require explicit confirmation and/or an environment flag.
- **Input Sanitization:** All identifiers and shell commands are validated before reaching the Proxmox API.
- **Sensitive Data Redaction:** Passwords, tokens, and SSH keys are masked in logs.
