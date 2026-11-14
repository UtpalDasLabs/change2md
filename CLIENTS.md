# AI client setup

Change2MD works with AI **clients and harnesses**, not with a particular model. Any client that can call the MCP tools can use the resulting Markdown with its selected model.

Choose **Local** when files should stay on your computer, or **Cloud** when the client supports remote MCP servers and the file or public URL can be processed by the hosted service.

## Local MCP

Requirements: Python is not required, but [`uv`](https://docs.astral.sh/uv/getting-started/installation/) must be on your `PATH`.

### Claude Desktop, Cursor and Cline

Open the client's MCP settings JSON and merge in:

```json
{
  "mcpServers": {
    "change2md-local": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--prerelease=allow",
        "--from",
        "markitdown-mcp==0.0.1a8",
        "markitdown-mcp"
      ]
    }
  }
}
```

- **Claude Desktop:** use the local MCP configuration file from the developer settings, then restart the app.
- **Cursor:** use `.cursor/mcp.json` for one project or your global Cursor MCP configuration.
- **Cline:** open its MCP settings and add the same `mcpServers` entry.

### VS Code

Add this to `.vscode/mcp.json`:

```json
{
  "servers": {
    "change2md-local": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--prerelease=allow",
        "--from",
        "markitdown-mcp==0.0.1a8",
        "markitdown-mcp"
      ]
    }
  }
}
```

Reload the window and confirm that the `convert_to_markdown` tool from Microsoft's `markitdown-mcp` server is available.

## Cloud MCP

The remote server is:

```text
https://change2md.vercel.app/mcp
```

For clients using the common `mcpServers` format:

```json
{
  "mcpServers": {
    "change2md": {
      "type": "streamable-http",
      "url": "https://change2md.vercel.app/mcp"
    }
  }
}
```

For VS Code remote MCP configuration, use `"type": "http"` inside its top-level `servers` object instead.

Cloud conversion accepts a generic public HTTPS `download_url` with optional `file_name` and `mime_type`. ChatGPT's file identifier is optional and is not required by other MCP clients. A remote server cannot read a path on your computer; use the Local edition for local paths.

## Verify the connection

Ask the client:

```text
Convert https://example.com to Markdown using Change2MD.
```

Client capabilities and configuration locations can change. These examples cover standard MCP STDIO and Streamable HTTP configurations; consult the client's current documentation if its settings differ.

## Other applications

- The hosted web converter is available at `https://change2md.vercel.app/convert`.
- The REST API accepts public URLs at `POST /api/convert` and file uploads at `POST /api/convert/file`.
- The CLI, Python SDK and TypeScript SDK are included for non-MCP workflows.

## Security

Local conversion runs with your user permissions. Cloud conversion accepts only credential-free public HTTPS destinations, blocks private and loopback networks, limits file and output sizes, and deletes temporary files after conversion. Do not expose the Local STDIO server as a network service.
