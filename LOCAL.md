# Change2MD Local Edition

Use this edition when document contents should stay on your computer. It runs
Microsoft's official `markitdown-mcp` package as a local STDIO process.

## Requirements

- macOS, Windows, or Linux
- A desktop MCP client that supports local STDIO servers or Agent Plugins
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) on your `PATH`

It does **not** run in ChatGPT web or mobile because those products cannot start
a process on your computer.

## Install

1. Install `uv` using its official instructions.
2. Download the `change2md-local` ZIP from the latest GitHub release, or clone
   this repository and use the `local-plugin/` directory.
3. Add that package through your desktop client's local Agent Plugin flow.
   If the client accepts raw MCP configuration, use `local-plugin/mcp.json`.
4. Restart or reload the client. Confirm that the `convert_to_markdown` tool is
   available.
5. Ask naturally: `Convert this supplied PDF to Markdown.` The client may invoke
   Change2MD Local automatically; no `@Change2MD` mention is required.

The first run downloads the pinned `markitdown-mcp` package and its dependencies.
Later runs use the local `uv` cache.

## What stays local

- Local file contents are read and converted by the process on your computer.
- No Change2MD cloud service receives those local files.
- Output is returned to the MCP client that requested the conversion.

Network access still occurs when you explicitly convert an `http:` or `https:`
URL. Your MCP client may also send prompts, tool arguments, or results to its own
model provider under that provider's terms.

## Security boundary

The local server runs with your user permissions and can read files you can read.
Only convert files or URLs you explicitly selected. Do not expose the server to
the network; the included package uses STDIO and does not open a listening port.

## Manual MCP configuration

Clients that do not ingest Agent Plugin packages can use this server definition:

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

## Verify

Run this harmless check in the MCP client:

`Convert https://example.com to Markdown using the local edition.`

Microsoft documents the same default STDIO server and its security model in the
[`markitdown-mcp` README](https://github.com/microsoft/markitdown/tree/main/packages/markitdown-mcp).
