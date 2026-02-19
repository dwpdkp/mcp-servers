# MCP-Servers

A collection of Model Context Protocol (MCP) servers for AI assistant integration.

## Overview

This repository contains multiple MCP server implementations that extend AI assistants with various capabilities:

| Project | Description | Language |
|---------|-------------|----------|
| **fastmcp** | Comprehensive framework for building MCP servers and clients | Python 3.10+ |
| **bacularis-mcp** | Read-only access to Bacula/Bareos backup management via Bacularis API | Python 3.10+ |
| **mcp_youtube_dlp** | YouTube video and audio download tools | Python 3.13+ |
| **weather** | Weather information retrieval | Python |

## What is MCP?

The Model Context Protocol (MCP) is an open standard created by Anthropic that provides a universal way to connect AI assistants to external data sources and tools. It uses JSON-RPC 2.0 for communication and supports multiple transport protocols (stdio, HTTP).

For detailed technical information, see [MCP-web-research.md](./MCP-web-research.md).

## Quick Start

### Prerequisites

- Python 3.10+ (3.13+ for mcp_youtube_dlp)
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/MCP-Servers.git
   cd MCP-Servers
   ```

2. Install dependencies for a specific project:
   ```bash
   cd fastmcp  # or mcp_youtube_dlp, weather
   uv sync
   ```

## Projects

### FastMCP

A comprehensive Python framework for building MCP servers and clients. Includes tools, resources, prompts, authentication, and multiple transport options.

```bash
cd fastmcp
uv sync
uv run fastmcp run examples/echo.py
```

See [fastmcp/AGENTS.md](./fastmcp/AGENTS.md) for development guidelines.

### MCP YouTube-DLP

Download YouTube videos and audio using yt-dlp through MCP tools.

```bash
cd mcp_youtube_dlp
uv pip install -e .
python main.py
```

**Environment Variables:**
- `YT_DLP_PATH` - Path to yt-dlp executable
- `DEFAULT_DOWNLOAD_DIR` - Download directory

### Weather

Weather information MCP server.

```bash
cd weather
uv sync
python src/weather/server.py
```

## MCP Client Configuration

Add servers to your MCP client (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/path/to/mcp_youtube_dlp/main.py"],
      "env": {
        "YT_DLP_PATH": "/usr/local/bin/yt-dlp"
      }
    },
    "weather": {
      "command": "python",
      "args": ["/path/to/weather/src/weather/server.py"]
    }
  }
}
```

## Development

All projects use `uv` as the package manager. **Do not use pip directly.**

```bash
# Install dependencies
uv sync

# Run tests (FastMCP)
uv run pytest

# Lint and format (FastMCP)
uv run pre-commit run --all-files
```

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines.

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Development guidelines for Claude Code
- [MCP-web-research.md](./MCP-web-research.md) - Comprehensive MCP technical reference

## License

- **fastmcp** - MIT License
- **mcp_youtube_dlp** - GPL-2.0 License
- **weather** - See project directory

## Resources

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://gofastmcp.com/)
