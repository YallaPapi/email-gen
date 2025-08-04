# Context7 MCP Server Test

## Server Status
✅ Context7 MCP server is connected and running
- Scope: Project config (shared via .mcp.json)  
- Status: ✓ Connected
- Type: stdio
- Command: cmd /c npx -y @upstash/context7-mcp@latest

## Available Context7 Tools

### 1. resolve-library-id
Resolves a general library name into a Context7-compatible library ID.
- **Parameter**: libraryName (required) - The name of the library to search for

### 2. get-library-docs  
Fetches documentation for a library using a Context7-compatible library ID.
- **Parameters**:
  - context7CompatibleLibraryID (required) - Exact Context7-compatible library ID (e.g., /mongodb/docs, /vercel/next.js)
  - topic (optional) - Focus the docs on a specific topic (e.g., "routing", "hooks")
  - tokens (optional, default 10000) - Max number of tokens to return

## Usage Example

To use Context7 in Claude Code, you can:

1. **Use the /mcp command** to interact with Context7 tools
2. **Reference resources** using @ mentions (if Context7 exposes resources)
3. **Use MCP prompts** as slash commands (format: /mcp__context7__promptname)

## Example Prompts

Here are some example prompts you can use with Context7:

1. "Use Context7 to get FastAPI documentation about file uploads"
2. "Fetch the latest Next.js routing documentation using Context7"
3. "Get MongoDB aggregation pipeline docs via Context7"

## Direct Library ID Usage

If you know the exact library ID, you can request it directly:
- FastAPI: Use library ID `/tiangolo/fastapi` 
- Next.js: Use library ID `/vercel/next.js`
- MongoDB: Use library ID `/mongodb/docs`

This allows Context7 to skip the library-matching step and directly retrieve docs.