from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from markitdown import MarkItDown

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

    def as_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "markdown": self.markdown,
            "total_chars": self.total_chars,
            "offset": self.offset,
            "next_offset": self.next_offset,
            "has_more": self.has_more,
        }


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


def download_to_temp(url: str, suffix: str = "") -> Path:
    current = url
    temp_path: Path | None = None
    headers = {
        "User-Agent": "Change2MD/0.2 (+https://github.com/UtpalDasLabs/change2md)"
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


def chunk_markdown(
    markdown: str,
    offset: int = 0,
    max_chars: int = MAX_MARKDOWN_CHARS,
) -> ConversionChunk:
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
    return ConversionChunk(
        markdown=markdown[offset:end],
        total_chars=len(markdown),
        offset=offset,
        next_offset=end if has_more else None,
        has_more=has_more,
    )


async def convert_path(
    path: Path,
    offset: int = 0,
    max_chars: int = MAX_MARKDOWN_CHARS,
) -> ConversionChunk:
    async with _conversions:
        markdown = await asyncio.to_thread(
            lambda: MarkItDown(enable_plugins=False).convert_local(path).markdown
        )
    return chunk_markdown(markdown, offset=offset, max_chars=max_chars)
