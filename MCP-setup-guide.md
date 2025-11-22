# MCP Setup Guide for Claude Code

A practical guide for configuring and using MCP servers with Claude Code CLI.

## Quick Setup

### Option 1: Add via CLI

```bash
# HTTP transport (cloud services)
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Stdio transport (local processes)
claude mcp add --transport stdio youtube -- python /path/to/mcp_youtube_dlp/main.py

# SSE transport (deprecated)
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

### Option 2: Configuration File

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/path/to/mcp_youtube_dlp/main.py"],
      "env": {
        "YT_DLP_PATH": "/usr/local/bin/yt-dlp",
        "DEFAULT_DOWNLOAD_DIR": "~/Downloads/youtube_downloads"
      }
    },
    "weather": {
      "command": "python",
      "args": ["/path/to/weather/src/weather/server.py"]
    }
  }
}
```

## Configuration Locations

| Scope | Location | Use Case |
|-------|----------|----------|
| **Project** | `.mcp.json` in project root | Team-shareable, version controlled |
| **User** | `~/.claude.json` | Personal settings for all projects |
| **Local** | CLI only (not persisted) | Temporary testing |

### Scope Priority

When servers with the same name exist at multiple scopes:
1. Local-scoped (highest priority)
2. Project-scoped
3. User-scoped

## Configuration Format

```json
{
  "mcpServers": {
    "server-name": {
      "command": "executable-or-npx",
      "args": ["argument1", "argument2"],
      "env": {
        "ENV_VAR": "value",
        "API_KEY": "${API_KEY_ENV_VAR}",
        "PATH": "${HOME}/path/to/config"
      }
    }
  }
}
```

### Environment Variables

Use `${VAR}` syntax for secrets (never hardcode them):

```json
"env": {
  "API_KEY": "${MY_API_KEY}",
  "DATABASE_URL": "${POSTGRES_URL}",
  "CONFIG_PATH": "${HOME}/.config/myapp"
}
```

Default values: `${VAR:-default}` uses "default" if VAR is not set.

## Management Commands

```bash
# View all connected MCP servers
claude mcp list

# Get details about a specific server
claude mcp get <server-name>

# Remove a server configuration
claude mcp remove <server-name>

# Reset project approval choices
claude mcp reset-project-choices
```

## Using MCP Servers in Claude Code

### Check Status

Type `/mcp` inside Claude Code to:
- View all connected servers
- Check server status
- Handle OAuth 2.0 authentication
- See available tools and resources

### Reference Resources

Use `@resource-name` syntax to reference MCP resources in your conversations.

## Example Configurations

### Multiple Tools

```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "notion-mcp-server"],
      "env": {
        "NOTION_API_KEY": "${NOTION_API_KEY}"
      }
    },
    "postgresql": {
      "command": "npx",
      "args": ["-y", "postgresql-mcp-server"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    },
    "figma": {
      "command": "npx",
      "args": ["-y", "figma-mcp-server"],
      "env": {
        "FIGMA_TOKEN": "${FIGMA_TOKEN}"
      }
    }
  }
}
```

### Local MCP Servers (This Repository)

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/Users/you/MCP-Servers/mcp_youtube_dlp/main.py"],
      "env": {
        "YT_DLP_PATH": "/usr/local/bin/yt-dlp",
        "DEFAULT_DOWNLOAD_DIR": "~/Downloads/youtube_downloads"
      }
    },
    "weather": {
      "command": "python",
      "args": ["/Users/you/MCP-Servers/weather/src/weather/server.py"]
    }
  }
}
```

## Security Best Practices

1. **Trust sources** - Only install MCP servers from trusted sources
2. **Use environment variables** - Never hardcode API keys or secrets
3. **Project approval** - Claude Code prompts for approval before using project-scoped servers
4. **Version control** - Safe to commit `.mcp.json`; never commit actual secrets

## Quick Setup Checklist

- [ ] Create `.mcp.json` in project root (or edit `~/.claude.json`)
- [ ] Define MCP servers with `command`, `args`, and `env`
- [ ] Set environment variables for secrets
- [ ] Run `claude mcp list` to verify
- [ ] Use `/mcp` in Claude Code to authenticate if needed
- [ ] Test with `@resource-name` references

## Resources

- [Claude Code MCP Documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
