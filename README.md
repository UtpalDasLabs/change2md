# Change2MD

A privacy-minded remote MCP server that converts user-supplied files and public
webpages to Markdown inside ChatGPT and Codex.

This is the public-service edition of a local workflow built on
[Microsoft MarkItDown](https://github.com/microsoft/markitdown). It is an
independent project and is not affiliated with or endorsed by Microsoft or
OpenAI.

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

## Privacy and safety

- Files are downloaded to temporary storage and deleted after conversion.
- The service has no user accounts or permanent document storage.
- File size is capped at 25 MB and Markdown output at 500,000 characters.
- Only HTTPS downloads are allowed; private, loopback, link-local, metadata,
  credential-bearing, and non-public destinations are blocked.
- Conversions are read-only and bounded by time and concurrency limits.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
PUBLIC_HOST=localhost:8000 uvicorn change2md_server.app:app --host 0.0.0.0 --port 8000
```

The MCP endpoint is `http://localhost:8000/mcp`; health is available at
`http://localhost:8000/health`.

## Deploy

Build the included Dockerfile on any container host. Set `PUBLIC_HOST` to the
exact public hostname before starting the service. A free Render blueprint is
included for development and review; production should use an always-on plan
with resource and abuse controls sized for actual traffic.

## License

MIT. Microsoft MarkItDown remains subject to its own MIT license and trademark
guidelines.

