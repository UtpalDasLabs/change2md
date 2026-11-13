---
name: convert-to-markdown
description: Use automatically when the user asks to convert an attached supported file or a public HTTPS webpage to Markdown, even when they do not name Change2MD.
---

# Convert to Markdown

Use Change2MD when the user's intent is to turn an attached supported file or a
specific public HTTPS webpage into Markdown. Natural requests such as “convert
this PDF to Markdown,” “turn this workbook into Markdown tables,” or “make this
page Markdown” should trigger the appropriate tool without requiring the user to
name or mention the plugin.

For an attachment, call `convert_file_to_markdown` with the exact attached file.
For one public HTTPS URL, call `convert_webpage_to_markdown` with that URL.

Do not invoke Change2MD merely because a file or URL appears in the conversation.
Do not use it for private or login-protected pages, private-network URLs,
recursive crawling, OCR, image captioning, or audio transcription. Explain those
limits plainly. Never ask for credentials. Return the converted Markdown without
claiming unsupported extraction fidelity.
