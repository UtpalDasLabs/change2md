from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.datastructures import UploadFile

from .conversion import (
    MAX_FILE_BYTES,
    MAX_MARKDOWN_CHARS,
    _safe_suffix,
    convert_path,
    download_to_temp,
)


def _response(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        payload,
        status_code=status_code,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Cache-Control": "no-store",
        },
    )


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
        return _response({"error": "The source could not be downloaded."}, status_code=502)
    return _response({"error": str(exc)}, status_code=400)


async def convert_url_api(request: Request) -> JSONResponse:
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
        suffix = _safe_suffix(urlparse(url).path, "text/html")
        path = await asyncio.to_thread(download_to_temp, url, suffix or ".html")
        result = await convert_path(path, offset=offset, max_chars=max_chars)
        return _response({**result.as_dict(), "source_url": url})
    except (ValueError, requests.RequestException) as exc:
        return _error(exc)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


async def convert_file_api(request: Request) -> JSONResponse:
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
        suffix = _safe_suffix(upload.filename, upload.content_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            path = Path(handle.name)
            size = 0
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise ValueError("The file exceeds the 25 MB limit.")
                handle.write(chunk)
        result = await convert_path(path, offset=offset, max_chars=max_chars)
        return _response({**result.as_dict(), "file_name": upload.filename})
    except (ValueError, requests.RequestException) as exc:
        return _error(exc)
    finally:
        if upload is not None:
            await upload.close()
        if path is not None:
            path.unlink(missing_ok=True)
