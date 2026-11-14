"""Self-contained Vercel ASGI entrypoint.

Vercel's repository entrypoint loader is kept independent from the local package.
The CLI, SDK and development server use src/change2md_server.
"""
from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from markitdown import MarkItDown
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(25 * 1024 * 1024)))
MAX_MARKDOWN_CHARS = int(os.getenv("MAX_MARKDOWN_CHARS", "500000"))
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 45.0
_conversions = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_CONVERSIONS", "4")))


@dataclass(frozen=True)
class ConversionChunk:
    markdown: str
    total_chars: int
    offset: int
    next_offset: int | None
    has_more: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "markdown": self.markdown,
            "total_chars": self.total_chars,
            "offset": self.offset,
            "next_offset": self.next_offset,
            "has_more": self.has_more,
        }


def _is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global and not any((address.is_private, address.is_loopback, address.is_link_local, address.is_multicast, address.is_reserved, address.is_unspecified))


def _validate_url_shape(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTPS URLs are supported.")
    return parsed.hostname, parsed.port or 443


def _validate_public_https_url(url: str) -> None:
    host, port = _validate_url_shape(url)
    if host.lower() == "localhost":
        raise ValueError("Local and private network URLs are not supported.")
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("The URL host could not be resolved.") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise ValueError("Local and private network URLs are not supported.")


def _safe_suffix(file_name: str | None, mime_type: str | None = None) -> str:
    suffix = Path(file_name or "").suffix.lower()
    if suffix and len(suffix) <= 12 and suffix[1:].isalnum():
        return suffix
    return {"application/pdf": ".pdf", "application/json": ".json", "application/xml": ".xml", "text/csv": ".csv", "text/html": ".html", "text/plain": ".txt"}.get((mime_type or "").split(";", 1)[0].lower(), "")


def download_to_temp(url: str, suffix: str = "") -> Path:
    current = url
    temp_path: Path | None = None
    try:
        with requests.Session() as client:
            client.headers.update({"User-Agent": "Change2MD/0.2 (+https://github.com/UtpalDasLabs/change2md)"})
            for _ in range(MAX_REDIRECTS + 1):
                _validate_public_https_url(current)
                with client.get(current, allow_redirects=False, stream=True, timeout=REQUEST_TIMEOUT) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("The download redirected without a destination.")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    if int(response.headers.get("content-length", "0") or "0") > MAX_FILE_BYTES:
                        raise ValueError("The file exceeds the 25 MB limit.")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                        temp_path = Path(handle.name)
                        size = 0
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            size += len(chunk)
                            if size > MAX_FILE_BYTES:
                                raise ValueError("The file exceeds the 25 MB limit.")
                            handle.write(chunk)
                    return temp_path
            raise ValueError("The download redirected too many times.")
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def chunk_markdown(markdown: str, offset: int = 0, max_chars: int = MAX_MARKDOWN_CHARS) -> ConversionChunk:
    if offset < 0:
        raise ValueError("The offset must be zero or greater.")
    if offset > len(markdown):
        raise ValueError("The offset is beyond the end of the Markdown output.")
    if max_chars < 1 or max_chars > MAX_MARKDOWN_CHARS:
        raise ValueError(f"The chunk size must be between 1 and {MAX_MARKDOWN_CHARS} characters.")
    end = min(offset + max_chars, len(markdown))
    if end < len(markdown):
        preferred_end = markdown.rfind("\n", offset + max_chars // 2, end)
        if preferred_end > offset:
            end = preferred_end + 1
    has_more = end < len(markdown)
    return ConversionChunk(markdown[offset:end], len(markdown), offset, end if has_more else None, has_more)


async def convert_path(path: Path, offset: int = 0, max_chars: int = MAX_MARKDOWN_CHARS) -> ConversionChunk:
    async with _conversions:
        markdown = await asyncio.to_thread(lambda: MarkItDown(enable_plugins=False).convert_local(path).markdown)
    return chunk_markdown(markdown, offset, max_chars)


class FileReference(BaseModel):
    model_config = ConfigDict(extra="allow")
    download_url: str = Field(description="Public or client-authorized HTTPS download URL.")
    file_id: str | None = Field(default=None, description="Optional client file identifier.")
    mime_type: str | None = Field(default=None, description="File MIME type when available.")
    file_name: str | None = Field(default=None, description="Original file name when available.")


mcp = MCPServer(
    "change2md",
    title="Change2MD",
    description="Convert user-supplied files and public webpages to Markdown.",
    instructions="Use these read-only tools only when the user asks to convert an attached file or a public webpage to Markdown. Never infer unrelated files or URLs. For large results, request smaller chunks with offset and max_chars.",
    version="0.2.0",
)


@mcp.tool(
    title="Convert file to Markdown",
    description="Use when the user asks to convert an attached PDF, Word, PowerPoint, Excel, Outlook, HTML, CSV, JSON, XML, EPUB, ZIP, image, or text file to Markdown. The file is processed temporarily and deleted after conversion.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={"openai/fileParams": ["file"], "openai/toolInvocation/invoking": "Converting file…", "openai/toolInvocation/invoked": "Markdown ready"},
    structured_output=False,
)
async def convert_file_to_markdown(file: FileReference, offset: int = 0, max_chars: int = MAX_MARKDOWN_CHARS) -> str:
    path = await asyncio.to_thread(download_to_temp, file.download_url, _safe_suffix(file.file_name, file.mime_type))
    try:
        return (await convert_path(path, offset, max_chars)).markdown
    finally:
        path.unlink(missing_ok=True)


@mcp.tool(
    title="Convert webpage to Markdown",
    description="Use when the user asks to convert one public HTTPS webpage or directly linked public file to Markdown. Login-protected, local, private-network, and recursively crawled sites are not supported.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    meta={"openai/toolInvocation/invoking": "Converting webpage…", "openai/toolInvocation/invoked": "Markdown ready"},
    structured_output=False,
)
async def convert_webpage_to_markdown(url: str, offset: int = 0, max_chars: int = MAX_MARKDOWN_CHARS) -> str:
    path = await asyncio.to_thread(download_to_temp, url, _safe_suffix(urlparse(url).path, "text/html") or ".html")
    try:
        return (await convert_path(path, offset, max_chars)).markdown
    finally:
        path.unlink(missing_ok=True)


def _response(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status_code, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Cache-Control": "no-store"})


def _number(value: Any, name: str, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, requests.RequestException):
        return _response({"error": "The source could not be downloaded."}, 502)
    return _response({"error": str(exc)}, 400)


@mcp.custom_route("/api/convert", methods=["POST", "OPTIONS"])
async def api_convert_url(request: Request) -> JSONResponse:
    if request.method == "OPTIONS":
        return _response({})
    path: Path | None = None
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("url"), str):
            raise ValueError("Provide a public HTTPS URL in the url field.")
        url = payload["url"]
        offset = _number(payload.get("offset"), "offset", 0)
        max_chars = _number(payload.get("max_chars"), "max_chars", MAX_MARKDOWN_CHARS)
        path = await asyncio.to_thread(download_to_temp, url, _safe_suffix(urlparse(url).path, "text/html") or ".html")
        result = await convert_path(path, offset, max_chars)
        return _response({**result.as_dict(), "source_url": url})
    except (ValueError, requests.RequestException) as exc:
        return _error(exc)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


@mcp.custom_route("/api/convert/file", methods=["POST", "OPTIONS"])
async def api_convert_file(request: Request) -> JSONResponse:
    if request.method == "OPTIONS":
        return _response({})
    path: Path | None = None
    upload: UploadFile | None = None
    try:
        form = await request.form()
        candidate = form.get("file")
        if not isinstance(candidate, UploadFile):
            raise ValueError("Choose a file to upload in the file field.")
        upload = candidate
        offset = _number(form.get("offset"), "offset", 0)
        max_chars = _number(form.get("max_chars"), "max_chars", MAX_MARKDOWN_CHARS)
        with tempfile.NamedTemporaryFile(delete=False, suffix=_safe_suffix(upload.filename, upload.content_type)) as handle:
            path = Path(handle.name)
            size = 0
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise ValueError("The file exceeds the 25 MB limit.")
                handle.write(chunk)
        result = await convert_path(path, offset, max_chars)
        return _response({**result.as_dict(), "file_name": upload.filename})
    except (ValueError, requests.RequestException) as exc:
        return _error(exc)
    finally:
        if upload is not None:
            await upload.close()
        if path is not None:
            path.unlink(missing_ok=True)


WEB_APP_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Change2MD — Convert to Markdown</title><style>
:root{--bg:#f5f3ed;--surface:#fffdf8;--ink:#20211f;--muted:#686b64;--line:#d8d6cc;--accent:#536b45}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{width:min(880px,calc(100% - 32px));margin:auto;padding:48px 0}header{display:flex;justify-content:space-between;margin-bottom:48px}header a{color:var(--ink);text-decoration:none;font-weight:650}.eyebrow{font:12px ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}h1{font:700 clamp(36px,7vw,64px)/1.03 Georgia,serif;letter-spacing:-.035em;margin:12px 0}.lede{color:var(--muted);font-size:18px}form,section.output{background:var(--surface);border:1px solid var(--line);padding:24px;margin-top:28px}label{display:block;font-weight:650;margin:20px 0 8px}input{width:100%;min-height:48px;border:1px solid var(--line);background:#fff;padding:12px;font:inherit}input:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.hint{color:var(--muted);font-size:14px}.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}button{min-height:46px;border:1px solid var(--accent);background:var(--accent);color:#fff;padding:10px 18px;font-weight:650;cursor:pointer}button.secondary{background:transparent;color:var(--accent)}button:disabled{opacity:.5}#status{margin-top:16px;color:var(--accent)}#status.error{color:#a13d35}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto;background:#f0eee7;padding:20px;font:14px/1.6 ui-monospace,monospace}[hidden]{display:none!important}@media(max-width:520px){main{padding:28px 0}form,section.output{padding:18px}}</style></head><body><main>
<header><a href="/convert">Change2MD</a><a href="https://github.com/UtpalDasLabs/change2md">GitHub</a></header><p class="eyebrow">Universal AI input converter</p><h1>Turn a file or webpage into Markdown.</h1><p class="lede">Use it with any AI chat, harness or model. Choose one source, then copy or download the result.</p>
<form id="form"><label for="file">Upload a file</label><input id="file" type="file"><p class="hint">Supported MarkItDown inputs. Maximum 25 MB.</p><label for="url">Or convert a public webpage</label><input id="url" type="url" placeholder="https://example.com"><p class="hint">Public HTTPS only; private and login-protected pages are not supported.</p><div class="actions"><button id="submit" type="submit">Convert to Markdown</button></div><p id="status" role="status" aria-live="polite"></p></form>
<section class="output" id="section" hidden><h2>Markdown</h2><pre id="output" tabindex="0"></pre><div class="actions"><button id="copy" class="secondary" type="button">Copy Markdown</button><button id="download" class="secondary" type="button">Download Markdown</button><button id="next" class="secondary" type="button" hidden>Load next chunk</button></div><p id="info" class="hint"></p></section>
<footer class="hint">Cloud files are temporary and deleted after conversion. For sensitive documents, use the Local edition.</footer></main><script>
const form=document.getElementById('form'),file=document.getElementById('file'),url=document.getElementById('url'),submit=document.getElementById('submit'),next=document.getElementById('next'),status=document.getElementById('status'),section=document.getElementById('section'),output=document.getElementById('output'),info=document.getElementById('info');let nextOffset=0,sourceUrl='';
function busy(v){submit.disabled=v;next.disabled=v;submit.textContent=v?'Converting…':'Convert to Markdown'}function fail(m){status.textContent=m;status.className='error';busy(false)}
async function convert(append=false){const selected=file.files[0],entered=url.value.trim();if(!append&&!selected&&!entered)return fail('Choose a file or enter a public HTTPS URL.');if(!append&&selected&&entered)return fail('Choose either a file or a URL, not both.');busy(true);status.className='';status.textContent='Converting…';try{const offset=append?nextOffset:0;let response;if(selected){const data=new FormData();data.append('file',selected);data.append('offset',offset);data.append('max_chars','200000');response=await fetch('/api/convert/file',{method:'POST',body:data})}else{sourceUrl=entered||sourceUrl;response=await fetch('/api/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:sourceUrl,offset,max_chars:200000})})}const data=await response.json();if(!response.ok)throw new Error(data.error||'Conversion failed.');output.textContent=append?output.textContent+'\n'+data.markdown:data.markdown;nextOffset=data.next_offset||0;next.hidden=!data.has_more;section.hidden=false;info.textContent=`${data.total_chars.toLocaleString()} total characters${data.has_more?'; more chunks available':''}.`;status.textContent='Markdown ready.'}catch(error){fail(error.message||'Conversion failed.')}finally{busy(false)}}
form.addEventListener('submit',e=>{e.preventDefault();convert(false)});next.addEventListener('click',()=>convert(true));document.getElementById('copy').addEventListener('click',async()=>{await navigator.clipboard.writeText(output.textContent);status.textContent='Markdown copied.'});document.getElementById('download').addEventListener('click',()=>{const blob=new Blob([output.textContent],{type:'text/markdown'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(file.files[0]?.name.replace(/\.[^.]+$/,'')||'change2md')+'.md';a.click();URL.revokeObjectURL(a.href)});
</script></body></html>'''


@mcp.custom_route("/convert", methods=["GET"])
async def web_converter(_: Request) -> HTMLResponse:
    return HTMLResponse(WEB_APP_HTML)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "change2md", "version": "0.2.0"})


@mcp.custom_route("/.well-known/openai-apps-challenge", methods=["GET"])
async def openai_apps_challenge(_: Request) -> PlainTextResponse:
    token = os.getenv("OPENAI_APPS_CHALLENGE")
    return PlainTextResponse(token) if token else PlainTextResponse("Not configured", status_code=404)


def _allowed_hosts(environment: Mapping[str, str] = os.environ) -> list[str]:
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    for name in ("PUBLIC_HOST", "VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        if value := environment.get(name):
            if value not in hosts:
                hosts.append(value)
    return hosts


def _allowed_origins(environment: Mapping[str, str] = os.environ) -> list[str]:
    origins = ["https://chatgpt.com", "https://chat.openai.com"]
    for origin in environment.get("ALLOWED_ORIGINS", "").split(","):
        origin = origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app = mcp.streamable_http_app(
    host="0.0.0.0",
    json_response=True,
    stateless_http=True,
    max_request_body_size=1024 * 1024,
    transport_security=TransportSecuritySettings(allowed_hosts=_allowed_hosts(), allowed_origins=_allowed_origins()),
)
