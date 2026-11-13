# Change2MD

Convert files and public webpages to Markdown inside ChatGPT, Codex, and other
MCP clients. Change2MD is available in two clearly separated editions:

| Edition | Best for | Where conversion happens | Installation |
| --- | --- | --- | --- |
| **Cloud** | Simple ChatGPT web, desktop, and mobile use | Temporarily on Change2MD's hosted Vercel service | Install once from the ChatGPT Plugin Directory, then ask naturally |
| **Local** | Sensitive files and desktop workflows | On the user's own computer | Install `uv`, then add the included local plugin to a desktop MCP client |

Both editions use [Microsoft MarkItDown](https://github.com/microsoft/markitdown).
Change2MD is an independent project and is not affiliated with or endorsed by
Microsoft or OpenAI.

## Supported inputs

- PDF
- Word (`.docx`)
- PowerPoint (`.pptx`)
- Excel (`.xlsx`, `.xls`)
- Outlook messages
- HTML and public HTTPS webpages
- CSV, JSON, XML, EPUB, ZIP, and plain text
- Image metadata where supported by MarkItDown

Scanned-document OCR, image captioning, audio transcription, login-protected
pages, recursive crawling, and private-network URLs are intentionally excluded
from the first public release.

## Cloud Edition

- Works in ChatGPT without installing Python or a desktop application.
- Files are downloaded to temporary hosted storage and deleted after conversion.
- The service has no user accounts or permanent document storage.
- File size is capped at 25 MB and Markdown output at 500,000 characters.
- Only HTTPS downloads are allowed; private, loopback, link-local, metadata,
  credential-bearing, and non-public destinations are blocked.
- Conversions are read-only and bounded by time and concurrency limits.

The cloud plugin package is in [`plugin/`](plugin/). Its hosted endpoint runs on
Vercel. The public listing, support, privacy, and terms pages are under
[`docs/`](docs/).

## Local Edition

The Local Edition uses Microsoft's official `markitdown-mcp` server over STDIO.
Document contents stay on the computer, except when the user explicitly converts
a web URL or uses another network-backed MarkItDown feature. The local process
runs with the user's permissions, so it can read files that user can access.

See **[Local Edition setup](LOCAL.md)**. The installable local Agent Plugin is in
[`local-plugin/`](local-plugin/). It is intended for desktop MCP clients; it is
not available inside ChatGPT web or mobile.

## Develop the Cloud Edition locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
PUBLIC_HOST=localhost:8000 uvicorn change2md_server.app:app --host 0.0.0.0 --port 8000
```

The MCP endpoint is `http://localhost:8000/mcp`; health is available at
`http://localhost:8000/health`. The Dockerfile remains available for self-hosting;
the public cloud deployment uses Vercel's Python runtime.

## License

MIT. Microsoft MarkItDown remains subject to its own MIT license and trademark
guidelines.

