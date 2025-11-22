# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Repository Overview

This repository contains multiple Model Context Protocol (MCP) server projects for AI assistant tool integration:

- **fastmcp/** - Comprehensive Python framework for building MCP servers and clients (Python ≥3.10)
- **mcp_youtube_dlp/** - YouTube video/audio download MCP server (Python 3.13+)
- **weather/** - Weather MCP server
- **MCP-Builder-Stuff/** - Reference materials and SDK documentation

## Common Commands

### Package Management
All projects use `uv` as the package manager. **NEVER use pip directly.**

```bash
uv sync                              # Install dependencies
uv pip install -e .                  # Install package in editable mode
```

### FastMCP Development Workflow
**Run all three before committing:**

```bash
cd fastmcp
uv sync                              # Install dependencies
uv run pre-commit run --all-files    # Ruff + Prettier + ty
uv run pytest                        # Run full test suite
```

### Testing

```bash
# FastMCP
uv run pytest                                    # All tests
uv run pytest tests/path/to/test_file.py        # Single file
uv run pytest tests/path/to/test_file.py::test_name  # Single test
uv run pytest -m "integration"                  # Integration tests only
uv run pytest -m "not integration"              # Exclude integration tests

# mcp_youtube_dlp
python main.py                                  # Run server
```

### Linting and Type Checking

```bash
uv run ruff check                    # Linting
uv run ruff check --fix              # Auto-fix lint issues
uv run ty check                      # Type checking
```

### CLI Usage

```bash
uv run fastmcp run server.py         # Run a FastMCP server
uv run fastmcp inspect server.py     # Inspect server capabilities
```

## Architecture

### FastMCP Structure

| Path | Purpose |
|------|---------|
| `src/fastmcp/server/` | Server implementation, FastMCP class, auth, networking |
| `src/fastmcp/client/` | High-level client SDK + transports |
| `src/fastmcp/tools/` | Tool implementations + ToolManager |
| `src/fastmcp/resources/` | Resources, templates + ResourceManager |
| `src/fastmcp/prompts/` | Prompt templates + PromptManager |
| `src/fastmcp/cli/` | CLI commands (run, dev, install) |

Core MCP objects that typically need parallel changes: Tools, Resources, Resource Templates, Prompts.

### mcp_youtube_dlp

Environment variables:
- `YT_DLP_PATH` - Path to yt-dlp executable (default: `/usr/local/bin/yt-dlp`)
- `DEFAULT_DOWNLOAD_DIR` - Download directory (default: `~/Downloads/youtube_downloads`)

## Development Standards

### Testing (FastMCP)

- Use in-memory transport for tests (pass FastMCP server directly to Client)
- NEVER add `@pytest.mark.asyncio` - asyncio_mode is set globally
- Put imports at top of file, not in test body
- Use `# type: ignore[attr-defined]` for MCP results in tests

```python
mcp = FastMCP("TestServer")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

async with Client(mcp) as client:
    result = await client.call_tool("greet", {"name": "World"})
```

### Code Standards

- Python ≥3.10 with full type annotations
- Never use bare `except` - be specific with exception types
- Prioritize readable code over clever solutions
- Each feature needs corresponding tests
- A feature doesn't exist unless it is documented

### Git & Commits

- Run pre-commit hooks before committing
- Never amend commits to fix pre-commit failures
- Keep commit messages brief (headlines, not essays)
- Agents must identify themselves in commits/PRs
