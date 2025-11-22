# Model Context Protocol (MCP) - Comprehensive Technical Reference

## Summary

The Model Context Protocol (MCP) is an open-source standard created by Anthropic and released on November 25, 2024, designed to connect AI assistants to external data sources, tools, and systems. Often described as "the USB-C port for AI," MCP provides a standardized way to connect LLM applications to context providers, replacing fragmented custom integrations with a universal protocol. The protocol uses JSON-RPC 2.0 for message encoding and supports multiple transport mechanisms including stdio for local processes and Streamable HTTP for remote servers. Since its launch, MCP has seen rapid adoption, with OpenAI officially adopting the standard in March 2025, and estimates suggesting over 30,000 MCP servers have been built across various directories.

---

## 1. What is MCP (Model Context Protocol)?

### Official Definition and Purpose

MCP is an open protocol that provides a standardized way to connect AI assistants to data sources, tools, and systems where data lives. The protocol enables AI applications to access contextual information from content repositories, business management tools, development environments, and other external systems.

**Key purposes:**
- Replace fragmented, custom integrations with a unified protocol
- Enable AI systems to produce better, more relevant responses through access to real-world data
- Provide a secure, standardized method for context exchange between AI models and external systems

### Creators

The protocol was created at Anthropic by developers **David Soria Parra** and **Justin Spahr-Summers**. It was publicly announced on November 25, 2024.

### The Problem It Solves

AI systems have been "trapped behind information silos and legacy systems." Before MCP, connecting an AI model to each new data source required building and maintaining custom implementations. This led to:
- Duplicated effort across the industry
- Inconsistent integration quality
- Security vulnerabilities from varied approaches
- Limited context available to AI models

MCP addresses these challenges by providing a single, well-defined protocol that any AI application can use to connect to any compatible data source or tool.

---

## 2. MCP Architecture

### Client-Host-Server Model

MCP follows a **client-host-server architecture** where each host can run multiple client instances:

| Component | Description |
|-----------|-------------|
| **MCP Host** | The AI application (e.g., Claude Desktop, VS Code) that coordinates and manages one or multiple MCP clients |
| **MCP Client** | A component that maintains a 1:1 connection with an MCP server and obtains context from it |
| **MCP Server** | A program that provides context (tools, resources, prompts) to MCP clients |

### Two-Layer Architecture

**Data Layer**: Implements a JSON-RPC 2.0 based exchange protocol defining:
- Message structure and semantics
- Lifecycle management
- Server features (tools, resources, prompts)
- Client features (sampling, elicitation, logging)
- Notifications

**Transport Layer**: Manages communication channels and authentication

### Transport Protocols

#### stdio (Standard Input/Output)
- Client launches MCP server as a subprocess
- Messages flow via stdin/stdout as newline-delimited JSON-RPC
- Messages MUST NOT contain embedded newlines
- Server MAY write to stderr for logging
- Best suited for local, subprocess-based deployments

**Example use case**: Local file system access, Git operations, database queries on the same machine

#### Streamable HTTP Transport
- Server operates as independent process handling multiple client connections
- Uses HTTP POST for sending messages, optional GET for SSE streams
- Client MUST include `Accept` header listing both `application/json` and `text/event-stream`
- Supports session management via `Mcp-Session-Id` header
- Clients MUST include `MCP-Protocol-Version` header on all requests
- **Replaces the HTTP+SSE transport from protocol version 2024-11-05**

**Session Management Features**:
- Servers assign unique session IDs during initialization
- Sessions terminate via HTTP 404 responses
- Clients may explicitly close sessions using HTTP DELETE
- Resumability supported via `Last-Event-ID` header

#### Custom Transports
Implementations may develop custom transport mechanisms that preserve JSON-RPC format and MCP lifecycle requirements.

### Message Format (JSON-RPC 2.0)

All MCP messages follow JSON-RPC 2.0 specification with three message types:

**1. Requests** - Initiate operations (require string or integer ID, ID MUST NOT be null)
```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "mcp-client",
      "version": "1.0.0"
    }
  }
}
```

**2. Responses** - Return results for requests
```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "serverInfo": {
      "name": "my-server",
      "version": "1.0.0"
    }
  }
}
```

**3. Notifications** - One-way messages (no ID field, no response expected)

**Standard Error Codes**:
- PARSE_ERROR (-32700)
- INVALID_REQUEST (-32600)
- METHOD_NOT_FOUND (-32601)
- INVALID_PARAMS (-32602)
- INTERNAL_ERROR (-32603)

---

## 3. Core MCP Concepts

MCP has six core features, divided between server-side and client-side primitives:

### Server-Side Primitives

#### Tools (Callable Functions)
Executable functions that AI applications can invoke to perform actions.

**Characteristics**:
- Similar to POST endpoints - execute code or produce side effects
- Exposed via `tools/list` method, invoked via `tools/call`
- Can return text, images, audio content
- May include progress reporting for long-running operations

**Example**:
```python
@mcp.tool()
def search_database(query: str, limit: int = 10) -> list:
    """Search the database for matching records"""
    return db.search(query, limit)
```

#### Resources (Data/Content)
Data sources that provide contextual information to AI applications.

**Characteristics**:
- Similar to GET endpoints - load information into LLM context
- Each resource uniquely identified by a URI
- Ideal for static or semi-static information
- Examples: files, database schemas, application-specific information

**Example**:
```python
@mcp.resource("config://settings/{category}")
def get_settings(category: str) -> str:
    return json.dumps(load_settings(category))
```

#### Prompts (Templates)
Reusable templates that help structure interactions with language models.

**Characteristics**:
- Standardize how models perform common tasks
- Can accept arguments for customization
- Ensure consistency and best practices
- Discovered via `prompts/list`, retrieved via `prompts/get`

**Example**:
```python
@mcp.prompt()
def code_review(code: str, language: str) -> str:
    return f"Review the following {language} code for issues:\n\n{code}"
```

### Client-Side Primitives

#### Sampling (LLM Interactions)
Allows servers to request LLM completions from the client.

**Flow**:
1. Server sends `sampling/createMessage` request to client
2. Client reviews the request
3. Client samples from the LLM
4. Client returns results to server

**Key benefit**: Enables agentic behaviors where MCP servers can make requests of an LLM, reversing the typical workflow.

**Example use case**: A server can define a prompt, call tools to gather data, then request the LLM to synthesize results.

#### Roots
Define the directories that an MCP server can access.

**Characteristics**:
- Declared by the client as a sandbox boundary
- Ensures AI only interacts with approved directories
- Keeps local data private and AI safely contained
- Permissions still handled client-side with user approvals

#### Elicitation
Allows servers to request additional information from users during interactions.

**Characteristics**:
- Servers request structured data with JSON schemas
- Schemas limited to flat objects with primitive properties
- Three response actions: accept, decline, cancel
- Newly introduced in the 2025-06-18 specification version

**Security requirement**: Servers MUST NOT use elicitation to request sensitive information.

---

## 4. MCP Server Implementation

### Official SDKs

The Model Context Protocol organization maintains SDKs for multiple languages:

| SDK | Stars | Notes |
|-----|-------|-------|
| **Python SDK** | 20.2k | Most popular; available at `github.com/modelcontextprotocol/python-sdk` |
| **TypeScript SDK** | 10.8k | npm package `@modelcontextprotocol/sdk` (16,900+ dependent projects) |
| **Java SDK** | -- | Official implementation |
| **Kotlin SDK** | -- | Kotlin language support |
| **C# SDK** | -- | Developed with Microsoft |
| **Go SDK** | -- | Built with Google |
| **Ruby SDK** | -- | Maintained with Shopify |
| **Rust SDK** | -- | Rust implementation |
| **Swift SDK** | -- | Apple platforms |
| **PHP SDK** | -- | PHP implementation |

### FastMCP Framework

FastMCP is the standard high-level framework for building MCP applications:

**Python Version**:
```bash
pip install fastmcp
```

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

**TypeScript Version**:
```bash
npm install fastmcp
```

```typescript
import { FastMCP } from "fastmcp";
import { z } from "zod";

const server = new FastMCP({
  name: "My Server",
  version: "1.0.0"
});

server.addTool({
  name: "add",
  description: "Add two numbers",
  parameters: z.object({
    a: z.number(),
    b: z.number()
  }),
  execute: async (args) => String(args.a + args.b)
});

server.start({ transportType: "stdio" });
```

**Key FastMCP Features**:
- Decorator-based API with minimal boilerplate
- Multiple transport protocols (STDIO, HTTP, SSE)
- Authentication and OpenAPI generation
- Server composition
- Structured output support with Pydantic models

**Note**: FastMCP 1.0 was incorporated into the official MCP SDK in 2024. FastMCP 2.0 is the actively maintained version with extended capabilities.

### Authentication and Security

#### OAuth 2.1 Requirements

MCP implementations MUST follow OAuth 2.1 security best practices:

**Core Requirements**:
- Token audience validation is mandatory
- Short-lived access tokens recommended
- PKCE required for all clients
- All authorization server endpoints MUST use HTTPS
- Refresh token rotation required for public clients

**Token Binding**:
- Clients MUST include `resource` parameter in authorization requests
- Tokens bound to specific MCP server addresses via audience claim
- Prevents token reuse across services

**Best Practices**:
- Use centralized Authorization Servers for enterprise SSO
- Implement OAuth 2.0 Dynamic Client Registration (RFC7591)
- Support Authorization Server Metadata (RFC8414)
- Consider JWT-based assertions (RFC7523) over client secrets

#### Security Architecture

```
┌─────────────────────────────────────────┐
│        Authorization Server             │
│  (Keycloak, Auth0, Okta, etc.)         │
└──────────────┬──────────────────────────┘
               │ Access Tokens
               ▼
┌─────────────────────────────────────────┐
│           MCP Server                    │
│  - Validate audience claim              │
│  - Verify token scope                   │
│  - Enforce RBAC                         │
└─────────────────────────────────────────┘
```

---

## 5. MCP Ecosystem

### AI Assistant Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Claude Desktop** | Native support since launch (Nov 2024) | Supports local and remote servers via HTTP or stdio |
| **OpenAI/ChatGPT** | Adopted March 2025 | Supports via Responses API; developer mode provides full MCP client support |
| **VS Code** | Supported | Full support for tools, prompts, resources, elicitation, sampling, auth, roots |
| **Cursor** | Supported | IDE integration |
| **Zed** | Working integration | -- |
| **Replit** | Working integration | -- |

### Popular Pre-built MCP Servers

Anthropic maintains reference implementations for:
- **Google Drive** - File access and search
- **Slack** - Messaging integration
- **GitHub** - Repository operations
- **Git** - Version control
- **Postgres** - Database queries
- **Puppeteer** - Browser automation

**Enterprise Adoptions**:
- **Terraform MCP Server** (HashiCorp) - Registry data for code generation
- **Block** - Internal systems integration
- **Apollo** - Systems integration
- **Salesforce, Notion, Slack** - Building MCP servers for their platforms

### MCP Server Registries

| Registry | Description |
|----------|-------------|
| **Official MCP Registry** | `github.com/modelcontextprotocol/registry` - Community-driven, preview launched September 2025 |
| **Smithery.ai** | Registry and management platform with hosted and local deployment options |
| **mcp.run** | Hosted registry and control plane for secure, portable MCP servers |
| **PulseMCP** | Community hub and weekly newsletter |

**Statistics**: Over 30,000 MCP servers have been built across various directories as of 2025.

---

## 6. Best Practices

### Design Patterns

#### Single Responsibility Principle
Each MCP server should have one clear, well-defined purpose.

**Organization Patterns**:
- **By product area**: `core-mcp-server`, `analytics-mcp-server`, `billing-mcp-server`
- **By permissions**: `read-mcp-server` for safe operations, `write-mcp-server` for mutations
- **By performance**: `fast-mcp-server` for quick lookups, `batch-mcp-server` for heavy processing

#### Domain-Driven Design (DDD)
Organize code by business capabilities rather than technical concerns. Separate HTTP communication, JSON parsing, error handling, and response formatting from business logic.

#### Tool Design Best Practices
- Map tools to user goals, not API operations
- Group related tasks into higher-level functions
- Avoid overloading the toolset (manage "Tool Budget")
- Make tool calls idempotent
- Use pagination for list operations

### Performance Considerations

#### Token Efficiency
Every token returned consumes the AI model's context window. Optimization strategies:
- Trim JSON responses to essential elements
- Return handles/URIs for large payloads instead of inline data
- Use notification debouncing for bulk updates

#### Connection Lifecycle
Create connections per tool call, not on server start:
```python
@mcp.tool()
def query_database(query: str) -> str:
    # Create connection here, not in server initialization
    with database.connect() as conn:
        return conn.execute(query)
```

This trades latency for improved usability and reliability.

#### Transport Selection
- **Streamable HTTP**: For remotely deployed servers; handles streaming and request/response patterns
- **stdio**: For local processes; optimal performance with no network overhead

#### Horizontal Scaling
- Use stateless designs where possible
- Implement geographic distribution for latency-sensitive applications
- Consider ML-driven load balancing

### Security Best Practices

1. **Use established OAuth providers** - Handle security updates and compliance
2. **Implement proper scoping** - Grant minimum permissions needed
3. **Monitor access** - Track AI agent activities
4. **Regular token rotation** - Ensure tokens expire and refresh properly
5. **Secure storage** - Never hardcode credentials or tokens
6. **Validate all inputs** - Protect against injection attacks
7. **Use TLS for HTTP transport** - Protect data in transit

---

## 7. Future of MCP

### Roadmap (November 2025 Release)

**Release Date**: November 25, 2025
**Release Candidate**: November 11, 2025

#### Priority Features

1. **Asynchronous Operations**
   - Handle long-running tasks without blocking
   - Clients can check back later for results
   - Supports operations spanning hours

2. **Enterprise Scalability**
   - Improved horizontal scaling
   - Simplified server startup and session management
   - Focus on SEP-1442

3. **Server Discovery via .well-known URLs**
   - Servers advertise capabilities without connection
   - Enables automatic registry cataloging
   - Working toward common agent card standard

4. **MCP Registry General Availability**
   - Transition from September 2025 preview
   - Stabilizing v0.1 API
   - Support for public and private sub-registries

5. **Official Protocol Extensions**
   - Documented patterns for healthcare, finance, education
   - Curated collection of proven domain patterns

6. **Additional SDKs**
   - Official Ruby and Go SDKs in development
   - Google contributing to Go SDK

7. **Compliance Test Suites**
   - Automated verification of specification compliance
   - Reference client and server implementations

### Recent Developments (June 2025)

The June 18, 2025 specification version added:
- Structured tool outputs
- OAuth-based authorization
- Elicitation for server-initiated user interactions
- Improved security best practices
- MCP servers classified as OAuth Resource Servers

### Community Governance

A formal governance model has been established:
- Defined roles and decision-making mechanisms
- Specification Enhancement Proposal (SEP) process
- Plans for potential independent standards body
- Community input shapes protocol evolution

### Adoption Trends

- **March 2025**: OpenAI officially adopted MCP
- Major supporters: Microsoft, Google, OpenAI, Anthropic
- Estimates suggest 90% of organizations will use MCP by end of 2025
- Described as "the de-facto standard for connecting agents to tools and data"

---

## Verification Status

### Confirmed Across Multiple Sources
- MCP created by Anthropic, announced November 25, 2024
- Creators: David Soria Parra and Justin Spahr-Summers
- Protocol uses JSON-RPC 2.0
- Transport protocols: stdio and Streamable HTTP
- Six core features: Tools, Resources, Prompts, Sampling, Roots, Elicitation
- OpenAI adopted MCP in March 2025
- FastMCP 1.0 incorporated into official SDK in 2024

### Information from Single Sources (Verify if Critical)
- Specific star counts for GitHub repositories (subject to change)
- 90% organizational adoption prediction for 2025
- 30,000+ MCP servers built

### Conflicting/Evolving Information
- The HTTP+SSE transport was replaced by Streamable HTTP in newer protocol versions - ensure you reference the correct specification version for your needs

---

## Sources

1. **Anthropic Official Announcement** (November 25, 2024)
   - URL: https://www.anthropic.com/news/model-context-protocol
   - Credibility: Primary source from protocol creator; official announcement with authoritative details

2. **Model Context Protocol Official Documentation**
   - URL: https://modelcontextprotocol.io/
   - Specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
   - Credibility: Official specification and documentation maintained by Anthropic

3. **GitHub Organization - modelcontextprotocol**
   - URL: https://github.com/modelcontextprotocol
   - Python SDK: https://github.com/modelcontextprotocol/python-sdk
   - TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk
   - Credibility: Official source code repositories with SDKs and reference implementations

4. **MCP Roadmap** (Updated October 31, 2025)
   - URL: https://modelcontextprotocol.io/development/roadmap
   - Credibility: Official roadmap from protocol maintainers

5. **WorkOS MCP Features Guide**
   - URL: https://workos.com/blog/mcp-features-guide
   - Credibility: Technical blog from established identity/auth provider; well-researched technical content

6. **Docker MCP Best Practices**
   - URL: https://www.docker.com/blog/mcp-server-best-practices/
   - Credibility: Technical guidance from Docker, established infrastructure platform

7. **Auth0 MCP Authorization Guide**
   - URL: https://auth0.com/blog/an-introduction-to-mcp-and-authorization/
   - Credibility: Identity/auth industry leader; authoritative on OAuth implementation details

8. **FastMCP Documentation**
   - Python: https://gofastmcp.com/
   - GitHub: https://github.com/jlowin/fastmcp
   - Credibility: Most popular MCP framework; incorporated into official SDK

---

*Document compiled: November 21, 2025*
*Protocol version referenced: 2025-06-18 (latest as of compilation)*
*Next major release: November 25, 2025*
