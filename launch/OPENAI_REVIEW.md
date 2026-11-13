# OpenAI review preparation

Status: implementation tested locally; public name, hosted endpoint, public URLs,
fixtures, demo recording, identity verification, and portal submission pending.

## Positive cases

1. **PDF attachment**
   - Prompt: `Convert the attached PDF to Markdown.`
   - Tool: `convert_file_to_markdown`
   - Expected: the attached PDF is passed as `file`; the response contains its
     extracted headings, paragraphs, lists, and tables as Markdown.
2. **Word attachment**
   - Prompt: `Turn this Word document into Markdown.`
   - Tool: `convert_file_to_markdown`
   - Expected: the attached `.docx` is converted and its document structure is
     preserved in Markdown where MarkItDown supports it.
3. **Spreadsheet attachment**
   - Prompt: `Convert this Excel workbook to Markdown tables.`
   - Tool: `convert_file_to_markdown`
   - Expected: the attached workbook is converted into Markdown with sheet and
     table content represented in the tool result.
4. **Structured text attachment**
   - Prompt: `Convert this JSON file into readable Markdown.`
   - Tool: `convert_file_to_markdown`
   - Expected: the attached JSON is represented as Markdown without modifying
     the source file.
5. **Public webpage**
   - Prompt: `Convert https://example.com to Markdown.`
   - Tool: `convert_webpage_to_markdown`
   - Expected: the public HTTPS page is fetched once and returned as Markdown.

## Negative cases

1. **Private-network target**
   - Prompt: `Convert https://127.0.0.1/admin to Markdown.`
   - Expected: reject the target as local/private; do not fetch it.
2. **Unsupported authenticated page**
   - Prompt: `Convert my private company dashboard to Markdown.`
   - Expected: explain that login-protected pages are unsupported; do not ask
     for credentials or claim success.
3. **Unsupported OCR/transcription request**
   - Prompt: `Transcribe this scanned image and audio recording to Markdown.`
   - Expected: explain that OCR, image captioning, and audio transcription are
     outside the first release; do not fabricate content.

## Demo outline

1. Install the development plugin in ChatGPT.
2. Attach a small PDF and ask for Markdown without naming the plugin.
3. Attach an XLSX workbook and show the automatic tool selection and table output.
4. Convert `https://example.com` and show the result.
5. Try a localhost URL and show the safe rejection.

Record only after the hosted endpoint and public plugin package are final. Use
sample files with no personal or customer data.

