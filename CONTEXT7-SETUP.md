# Context7 MCP Server Setup

## Overview
Context7 MCP server has been configured for this project to provide up-to-date code documentation and suggestions directly in Claude Code.

## Configuration
The MCP server configuration is stored in `.mcp.json`:

```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@upstash/context7-mcp@latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Windows-Specific Configuration
- Uses `cmd /c` wrapper for proper npx execution on Windows
- Automatically downloads latest version via `@upstash/context7-mcp@latest`
- No API keys or credentials required

## Prerequisites
✅ Node.js v22.15.0 (installed - exceeds minimum v18 requirement)
✅ npx v10.9.2 (installed)
✅ Claude Code (current environment)

## Usage
Context7 will automatically start when Claude Code loads the `.mcp.json` configuration. It provides:
- Up-to-date documentation fetching
- Version-specific code examples
- Direct integration with development workflow

## Testing
The Context7 MCP server has been tested and is ready for use. The server will be automatically started by Claude Code when needed.

## References
- [Context7 GitHub Repository](https://github.com/upstash/context7)
- [MCP Documentation](https://modelcontextprotocol.io/introduction)