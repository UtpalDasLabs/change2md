import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.datastructures import UploadFile

from change2md_server.api import convert_file_api, convert_url_api
from change2md_server.conversion import ConversionChunk
from change2md_server.web import WEB_APP_HTML


class FakeRequest:
    method = "POST"

    def __init__(self, payload=None, form=None):
        self.payload = payload
        self.form_data = form or {}

    async def json(self):
        return self.payload

    async def form(self):
        return self.form_data


def fake_chunk() -> ConversionChunk:
    return ConversionChunk(
        markdown="# Converted",
        total_chars=11,
        offset=0,
        next_offset=None,
        has_more=False,
    )


async def fake_convert(*args, **kwargs) -> ConversionChunk:
    return fake_chunk()


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_url_conversion_returns_chunk_metadata(self) -> None:
        with (
            patch("change2md_server.api.download_to_temp", return_value=Path("unused")),
            patch("change2md_server.api.convert_path", side_effect=fake_convert),
            patch.object(Path, "unlink"),
        ):
            response = await convert_url_api(FakeRequest({"url": "https://example.com"}))
        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["markdown"], "# Converted")
        self.assertFalse(payload["has_more"])
        self.assertEqual(response.headers["access-control-allow-origin"], "*")

    async def test_file_conversion_accepts_multipart_upload(self) -> None:
        upload = UploadFile(io.BytesIO(b"hello"), filename="note.txt")
        with (
            patch("change2md_server.api.convert_path", side_effect=fake_convert),
            patch.object(Path, "unlink"),
        ):
            response = await convert_file_api(FakeRequest(form={"file": upload}))
        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["file_name"], "note.txt")
        self.assertEqual(payload["markdown"], "# Converted")

    async def test_url_conversion_requires_url(self) -> None:
        response = await convert_url_api(FakeRequest({}))
        self.assertEqual(response.status_code, 400)
        self.assertIn("url", json.loads(response.body)["error"])

    def test_web_converter_has_accessible_form_and_output(self) -> None:
        for text in (
            '<label for="file">',
            '<label for="url">',
            'role="status"',
            "Load next chunk",
            "Download Markdown",
        ):
            self.assertIn(text, WEB_APP_HTML)


if __name__ == "__main__":
    unittest.main()
