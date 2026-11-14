from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "https://change2md.vercel.app"


class Change2MDError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConversionResponse:
    markdown: str
    total_chars: int
    offset: int
    next_offset: int | None
    has_more: bool
    source_url: str | None = None
    file_name: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConversionResponse":
        return cls(
            markdown=payload["markdown"],
            total_chars=payload["total_chars"],
            offset=payload["offset"],
            next_offset=payload.get("next_offset"),
            has_more=payload["has_more"],
            source_url=payload.get("source_url"),
            file_name=payload.get("file_name"),
        )


class Change2MD:
    """Small synchronous client for the hosted Change2MD REST API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def __enter__(self) -> "Change2MD":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.session.close()

    def _parse(self, response: requests.Response) -> ConversionResponse:
        try:
            payload = response.json()
        except ValueError as exc:
            raise Change2MDError(f"Change2MD returned HTTP {response.status_code}.") from exc
        if not response.ok:
            raise Change2MDError(payload.get("error", f"HTTP {response.status_code}."))
        return ConversionResponse.from_dict(payload)

    def convert_url(
        self,
        url: str,
        offset: int = 0,
        max_chars: int = 500000,
    ) -> ConversionResponse:
        response = self.session.post(
            f"{self.base_url}/api/convert",
            json={"url": url, "offset": offset, "max_chars": max_chars},
            timeout=self.timeout,
        )
        return self._parse(response)

    def convert_file(
        self,
        path: str | Path,
        offset: int = 0,
        max_chars: int = 500000,
    ) -> ConversionResponse:
        file_path = Path(path)
        with file_path.open("rb") as handle:
            response = self.session.post(
                f"{self.base_url}/api/convert/file",
                files={"file": (file_path.name, handle)},
                data={"offset": str(offset), "max_chars": str(max_chars)},
                timeout=self.timeout,
            )
        return self._parse(response)
