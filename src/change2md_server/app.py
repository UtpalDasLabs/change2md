from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from markitdown import MarkItDown
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(25 * 1024 * 1024)))
MAX_MARKDOWN_CHARS = int(os.getenv("MAX_MARKDOWN_CHARS", "500000"))
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 45.0
_conversions = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_CONVERSIONS", "4")))


class OpenAIFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    download_url: str = Field(description="Temporary ChatGPT-authorized HTTPS download URL.")
    file_id: str = Field(description="ChatGPT file identifier.")
    mime_type: str | None = Field(default=None, description="File MIME type when available.")
    file_name: str | None = Field(default=None, description="Original file name when available.")


mcp = MCPServer(
    "change2md",
    title="Change2MD",
    description="Convert user-supplied files and public webpages to Markdown.",
    instructions=(
        "Use these read-only tools only when the user asks to convert an attached file "
        "or a public webpage to Markdown. Never infer unrelated files or URLs."
    ),
    version="0.1.0",
)


def _is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global and not any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


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
    return {
        "application/pdf": ".pdf",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/csv": ".csv",
        "text/html": ".html",
        "text/plain": ".txt",
    }.get((mime_type or "").split(";", 1)[0].lower(), "")


def _download(url: str, suffix: str = "") -> Path:
    current = url
    temp_path: Path | None = None
    headers = {
        "User-Agent": "Change2MD/0.1 (+https://github.com/UtpalDasLabs/change2md)"
    }

    try:
        with requests.Session() as client:
            client.headers.update(headers)
            for _ in range(MAX_REDIRECTS + 1):
                _validate_public_https_url(current)
                with client.get(
                    current,
                    allow_redirects=False,
                    stream=True,
                    timeout=REQUEST_TIMEOUT,
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("The download redirected without a destination.")
                        current = urljoin(current, location)
                        continue

                    response.raise_for_status()
                    declared_size = int(response.headers.get("content-length", "0") or "0")
                    if declared_size > MAX_FILE_BYTES:
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


async def _convert_path(path: Path) -> str:
    async with _conversions:
        markdown = await asyncio.to_thread(
            lambda: MarkItDown(enable_plugins=False).convert_local(path).markdown
        )
    if len(markdown) > MAX_MARKDOWN_CHARS:
        raise ValueError("The converted Markdown is too large for one ChatGPT response.")
    return markdown


@mcp.tool(
    title="Convert file to Markdown",
    description=(
        "Use when the user asks to convert an attached PDF, Word, PowerPoint, Excel, "
        "Outlook, HTML, CSV, JSON, XML, EPUB, ZIP, image, or text file to Markdown. "
        "The file is processed temporarily and deleted after conversion."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    meta={
        "openai/fileParams": ["file"],
        "openai/toolInvocation/invoking": "Converting file…",
        "openai/toolInvocation/invoked": "Markdown ready",
    },
    structured_output=False,
)
async def convert_file_to_markdown(file: OpenAIFile) -> str:
    suffix = _safe_suffix(file.file_name, file.mime_type)
    path = await asyncio.to_thread(_download, file.download_url, suffix)
    try:
        return await _convert_path(path)
    finally:
        path.unlink(missing_ok=True)


@mcp.tool(
    title="Convert webpage to Markdown",
    description=(
        "Use when the user asks to convert one public HTTPS webpage or directly linked "
        "public file to Markdown. Login-protected, local, private-network, and recursively "
        "crawled sites are not supported."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    meta={
        "openai/toolInvocation/invoking": "Converting webpage…",
        "openai/toolInvocation/invoked": "Markdown ready",
    },
    structured_output=False,
)
async def convert_webpage_to_markdown(url: str) -> str:
    suffix = _safe_suffix(urlparse(url).path, "text/html")
    path = await asyncio.to_thread(_download, url, suffix or ".html")
    try:
        return await _convert_path(path)
    finally:
        path.unlink(missing_ok=True)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "change2md"})


@mcp.custom_route("/.well-known/openai-apps-challenge", methods=["GET"])
async def openai_apps_challenge(_: Request) -> PlainTextResponse:
    token = os.getenv("OPENAI_APPS_CHALLENGE")
    if not token:
        return PlainTextResponse("Not configured", status_code=404)
    return PlainTextResponse(token)


def _allowed_hosts(environment: Mapping[str, str] = os.environ) -> list[str]:
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    for name in ("PUBLIC_HOST", "VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        if value := environment.get(name):
            if value not in hosts:
                hosts.append(value)
    return hosts

app = mcp.streamable_http_app(
    host="0.0.0.0",
    json_response=True,
    stateless_http=True,
    max_request_body_size=1024 * 1024,
    transport_security=TransportSecuritySettings(
        allowed_hosts=_allowed_hosts(),
        allowed_origins=["https://chatgpt.com", "https://chat.openai.com"],
    ),
)

