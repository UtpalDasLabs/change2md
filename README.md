# Change2MD

Convert files and public webpages to portable Markdown for **any AI model**, using MCP, a web converter, a REST API, a CLI, or Python and TypeScript SDKs.

Change2MD uses [Microsoft MarkItDown](https://github.com/microsoft/markitdown). It is an independent project and is not affiliated with or endorsed by Microsoft or OpenAI.

## Choose an interface

| Interface | Best for | Conversion location |
| --- | --- | --- |
| **Local MCP** | Sensitive files and desktop MCP clients | On the user's computer |
| **Cloud MCP** | ChatGPT, Codex and remote MCP clients | Temporarily on hosted Vercel infrastructure |
| **Web converter** | Any AI chat window, including those without tool support | Hosted cloud service |
| **REST API** | Applications and harnesses without MCP | Hosted or self-hosted service |
| **CLI** | Terminal work, scripts and local files | Local by default; hosted with `--cloud` |
| **Python / TypeScript SDKs** | Application integrations | Hosted or self-hosted API |
| **Browser extension** | Converting the current public webpage | Hosted cloud service |

The model does not need a Change2MD-specific integration. Its host application calls a tool or the user supplies the converted Markdown.

## Supported inputs

- PDF
- Word (`.docx`)
- PowerPoint (`.pptx`)
- Excel (`.xlsx`, `.xls`)
- Outlook messages
- HTML and public HTTPS webpages
- CSV, JSON, XML, EPUB, ZIP and plain text
- Image metadata where supported by MarkItDown

Scanned-document OCR, image captioning, audio transcription, login-protected pages, recursive crawling and private-network URLs are intentionally excluded.

## MCP clients

See **[AI client setup](CLIENTS.md)** for local and remote configuration examples for Claude Desktop, Cursor, VS Code, Cline and other MCP-compatible clients.

The hosted MCP endpoint is:

```text
https://change2md.vercel.app/mcp
```

The Cloud file tool accepts a generic `download_url`, optional `file_name` and optional `mime_type`. ChatGPT's `file_id` remains supported but is not required. Large results can be requested with `offset` and `max_chars`.

The Local edition uses Microsoft's official `markitdown-mcp` server over STDIO. See **[Local Edition setup](LOCAL.md)**.

## Universal web converter

Open **https://change2md.vercel.app/convert**, choose a file or enter a public HTTPS URL, then copy or download the Markdown. This works as a fallback for AI chat windows that cannot call external tools.

## REST API

Convert a public URL:

```bash
curl -X POST https://change2md.vercel.app/api/convert \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","offset":0,"max_chars":100000}'
```

Upload a file:

```bash
curl -X POST https://change2md.vercel.app/api/convert/file \
  -F 'file=@document.pdf' \
  -F 'offset=0' \
  -F 'max_chars=100000'
```

Responses include `markdown`, `total_chars`, `offset`, `next_offset` and `has_more`. Pass `next_offset` as the next request's `offset` to resume a large conversion. Chunk boundaries prefer newlines when practical.

## CLI

Install this package, then convert locally:

```bash
change2md document.pdf -o document.md
change2md https://example.com
```

Use the hosted API instead:

```bash
change2md document.pdf --cloud -o document.md
```

Resume a chunk with `--offset` and control its size with `--max-chars`.

## Python SDK

```python
from change2md_server.client import Change2MD

with Change2MD() as client:
    result = client.convert_url("https://example.com", max_chars=100000)
    print(result.markdown)

    if result.has_more:
        next_result = client.convert_url(
            "https://example.com",
            offset=result.next_offset,
            max_chars=100000,
        )
```

Use `client.convert_file("document.pdf")` for uploads.

## TypeScript SDK

The package source is in [`sdk/typescript/`](sdk/typescript/):

```ts
import { Change2MD } from "@utpaldaslabs/change2md";

const client = new Change2MD();
const result = await client.convertUrl("https://example.com", { maxChars: 100000 });
console.log(result.markdown);
```

## Browser extension

Load [`browser-extension/`](browser-extension/) as an unpacked Manifest V3 extension in a compatible Chromium browser. The popup sends only the active page's public URL; it does not read page content. See its README for installation and limitations.

## Security and limits

- Cloud files are downloaded to temporary storage and deleted after conversion.
- No user accounts or permanent document storage are provided.
- File size is capped at 25 MB and a Markdown chunk at 500,000 characters.
- Only credential-free public HTTPS downloads are allowed.
- Private, loopback, link-local, metadata and non-public destinations are blocked.
- Conversions are read-only and bounded by time and concurrency limits.
- Public API responses allow cross-origin browser use without credentials. Production deployments should add edge-level rate limiting.

## Develop locally

```bash
uv venv
uv pip install -e .
PUBLIC_HOST=localhost:8000 .venv/bin/uvicorn change2md_server.app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/convert`. The MCP endpoint is `http://localhost:8000/mcp`; health is available at `http://localhost:8000/health`.

Run tests:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The Dockerfile remains available for self-hosting. Set `ALLOWED_ORIGINS` to a comma-separated list for additional browser-based MCP clients.

## License

MIT. Microsoft MarkItDown remains subject to its own MIT license and trademark guidance.
