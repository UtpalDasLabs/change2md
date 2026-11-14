import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from change2md_server.cli import main
from change2md_server.client import Change2MD, Change2MDError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.ok = status_code < 400

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.closed = False

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response

    def close(self):
        self.closed = True


class CliAndSdkTest(unittest.TestCase):
    def test_cli_converts_local_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "note.txt"
            source.write_text("Hello from the CLI", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main([str(source)])
        self.assertEqual(exit_code, 0)
        self.assertIn("Hello from the CLI", stdout.getvalue())

    def test_cli_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "note.txt"
            output = Path(directory) / "note.md"
            source.write_text("Saved Markdown", encoding="utf-8")
            self.assertEqual(main([str(source), "-o", str(output)]), 0)
            self.assertIn("Saved Markdown", output.read_text(encoding="utf-8"))

    def test_python_sdk_returns_chunk_metadata(self) -> None:
        payload = {
            "markdown": "hello",
            "total_chars": 10,
            "offset": 0,
            "next_offset": 5,
            "has_more": True,
            "source_url": "https://example.com",
        }
        session = FakeSession(FakeResponse(payload))
        client = Change2MD("https://converter.example/")
        client.session = session
        result = client.convert_url("https://example.com", max_chars=5)
        self.assertEqual(result.next_offset, 5)
        self.assertTrue(result.has_more)
        self.assertEqual(session.calls[0][1]["json"]["max_chars"], 5)

    def test_python_sdk_surfaces_api_errors(self) -> None:
        client = Change2MD()
        client.session = FakeSession(FakeResponse({"error": "Invalid URL"}, 400))
        with self.assertRaisesRegex(Change2MDError, "Invalid URL"):
            client.convert_url("https://invalid.example")

    def test_cloud_cli_uses_sdk(self) -> None:
        payload = {
            "markdown": "cloud",
            "total_chars": 5,
            "offset": 0,
            "next_offset": None,
            "has_more": False,
        }
        session = FakeSession(FakeResponse(payload))
        with patch("change2md_server.client.requests.Session", return_value=session):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["https://example.com", "--cloud"]), 0)
        self.assertEqual(stdout.getvalue(), "cloud\n")
        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
