from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from .client import Change2MD, DEFAULT_BASE_URL
from .conversion import (
    MAX_MARKDOWN_CHARS,
    _safe_suffix,
    convert_path,
    download_to_temp,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="change2md",
        description="Convert a local file or public HTTPS URL to Markdown.",
    )
    parser.add_argument("input", help="Local file path or public HTTPS URL")
    parser.add_argument("-o", "--output", help="Write Markdown to this file instead of stdout")
    parser.add_argument("--offset", type=int, default=0, help="Character offset to resume from")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=MAX_MARKDOWN_CHARS,
        help=f"Maximum characters to return (1–{MAX_MARKDOWN_CHARS})",
    )
    parser.add_argument("--cloud", action="store_true", help="Use the hosted API instead of local conversion")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS)
    return parser


async def _convert_locally(args: argparse.Namespace) -> str:
    parsed = urlparse(args.input)
    path: Path
    downloaded = False
    if parsed.scheme:
        path = await asyncio.to_thread(
            download_to_temp,
            args.input,
            _safe_suffix(parsed.path, "text/html"),
        )
        downloaded = True
    else:
        path = Path(args.input).expanduser()
        if not path.is_file():
            raise ValueError(f"File not found: {path}")
    try:
        result = await convert_path(path, offset=args.offset, max_chars=args.max_chars)
        return result.markdown
    finally:
        if downloaded:
            path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cloud:
            with Change2MD(args.base_url) as client:
                if Path(args.input).expanduser().is_file():
                    result = client.convert_file(args.input, args.offset, args.max_chars)
                else:
                    result = client.convert_url(args.input, args.offset, args.max_chars)
                markdown = result.markdown
        else:
            markdown = asyncio.run(_convert_locally(args))
        if args.output:
            Path(args.output).expanduser().write_text(markdown, encoding="utf-8")
        else:
            sys.stdout.write(markdown)
            if markdown and not markdown.endswith("\n"):
                sys.stdout.write("\n")
        return 0
    except Exception as exc:
        parser.exit(1, f"change2md: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
