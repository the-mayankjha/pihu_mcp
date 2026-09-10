# Pihu — MCP-native upgrade

This version removes the custom `server.py` / `servers/system.py` dependency from the agent.

It loads MCP servers from `mcp.json` and discovers their tools dynamically with the official MCP Python client.

## Included prebuilt MCPs

- Filesystem: `@modelcontextprotocol/server-filesystem`
- Memory: `@modelcontextprotocol/server-memory`
- Fetch: `mcp-server-fetch`
- Time: `mcp-server-time`

These are reference servers from the MCP ecosystem. The filesystem server is sandboxed to the Pihu project directory through `${PROJECT_ROOT}`.

## Requirements

You already have Python, the MCP Python SDK, Rich, and Gemini set up.

You also need:

```bash
node --version
npm --version
uv --version
```

If `node`/`npm` are missing, install Node.js. If `uv` is missing, install uv.

## Run

From the project directory:

```bash
python agent.py
```

The first run may take longer because `npx`/`uvx` may download the MCP server packages. Later starts are normally faster because the package managers can reuse their caches.

## What changed

The agent no longer has a hard-coded list like:

```python
SERVER_PATHS = [
    BASE_DIR / "servers" / "system.py",
    BASE_DIR / "server.py",
]
```

Instead:

```text
mcp.json
   ↓
MCP loader
   ↓
list_tools()
   ↓
Gemini function tools
   ↓
MCP tool execution
```

Add/remove MCP servers by editing `mcp.json`, not `agent.py`.

## Commands

```text
/tools      show every discovered MCP tool
/servers    show connected MCP servers
/clear      clear Gemini interaction context
/exit       quit
```

## Security

The filesystem MCP is intentionally restricted to the Pihu project directory.

Do not add your whole home directory to the filesystem MCP unless you intentionally want the agent to have access to it.

For additional MCPs, review the server's permissions, credentials, and source before enabling it.
