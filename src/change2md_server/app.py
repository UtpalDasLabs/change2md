from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

from .api import convert_file_api, convert_url_api
from .web import WEB_APP_HTML
from .conversion import (
    MAX_MARKDOWN_CHARS,
    _is_public_address,
    _safe_suffix,
    _validate_url_shape,
    convert_path,
    download_to_temp,
)


class FileReference(BaseModel):
    """A client-neutral file reference; ChatGPT may additionally supply file_id."""

    model_config = ConfigDict(extra="allow")

    download_url: str = Field(description="Public or client-authorized HTTPS download URL.")
    file_id: str | None = Field(default=None, description="Optional client file identifier.")
    mime_type: str | None = Field(default=None, description="File MIME type when available.")
    file_name: str | None = Field(default=None, description="Original file name when available.")


mcp = MCPServer(
    "change2md",
    title="Change2MD",
    description="Convert user-supplied files and public webpages to Markdown.",
    instructions=(
        "Use these read-only tools only when the user asks to convert an attached file "
        "or a public webpage to Markdown. Never infer unrelated files or URLs. For large "
        "results, request smaller chunks with offset and max_chars."
    ),
    version="0.2.0",
)


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
async def convert_file_to_markdown(
    file: FileReference,
    offset: int = 0,
    max_chars: int = MAX_MARKDOWN_CHARS,
) -> str:
    suffix = _safe_suffix(file.file_name, file.mime_type)
    path = await asyncio.to_thread(download_to_temp, file.download_url, suffix)
    try:
        result = await convert_path(path, offset=offset, max_chars=max_chars)
        return result.markdown
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
async def convert_webpage_to_markdown(
    url: str,
    offset: int = 0,
    max_chars: int = MAX_MARKDOWN_CHARS,
) -> str:
    suffix = _safe_suffix(urlparse(url).path, "text/html")
    path = await asyncio.to_thread(download_to_temp, url, suffix or ".html")
    try:
        result = await convert_path(path, offset=offset, max_chars=max_chars)
        return result.markdown
    finally:
        path.unlink(missing_ok=True)


@mcp.custom_route("/api/convert", methods=["POST", "OPTIONS"])
async def api_convert_url(request: Request) -> JSONResponse:
    return await convert_url_api(request)


@mcp.custom_route("/api/convert/file", methods=["POST", "OPTIONS"])
async def api_convert_file(request: Request) -> JSONResponse:
    return await convert_file_api(request)


@mcp.custom_route("/convert", methods=["GET"])
async def web_converter(_: Request) -> HTMLResponse:
    return HTMLResponse(WEB_APP_HTML)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "change2md", "version": "0.2.0"})


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
    transport_security=TransportSecuritySettings(
        allowed_hosts=_allowed_hosts(),
        allowed_origins=_allowed_origins(),
    ),
)
