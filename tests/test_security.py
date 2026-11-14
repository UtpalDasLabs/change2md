import unittest

from change2md_server.app import (
    _allowed_hosts,
    _allowed_origins,
    _is_public_address,
    _safe_suffix,
    _validate_url_shape,
)
from change2md_server.conversion import chunk_markdown


class SecurityHelpersTest(unittest.TestCase):
    def test_vercel_hosts_are_allowed(self) -> None:
        hosts = _allowed_hosts(
            {
                "VERCEL_URL": "change2md-preview.vercel.app",
                "VERCEL_PROJECT_PRODUCTION_URL": "change2md.vercel.app",
            }
        )
        self.assertIn("change2md-preview.vercel.app", hosts)
        self.assertIn("change2md.vercel.app", hosts)

    def test_private_addresses_are_blocked(self) -> None:
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"):
            self.assertFalse(_is_public_address(address))

    def test_public_address_is_allowed(self) -> None:
        self.assertTrue(_is_public_address("93.184.216.34"))

    def test_only_plain_https_urls_are_accepted(self) -> None:
        self.assertEqual(_validate_url_shape("https://example.com/file.pdf"), ("example.com", 443))
        for url in ("http://example.com", "file:///etc/passwd", "https://user:pass@example.com"):
            with self.assertRaises(ValueError):
                _validate_url_shape(url)

    def test_suffix_is_sanitized(self) -> None:
        self.assertEqual(_safe_suffix("report.DOCX"), ".docx")
        self.assertEqual(_safe_suffix("report", "application/pdf"), ".pdf")
        self.assertEqual(_safe_suffix("report.bad-suffix"), "")

    def test_additional_mcp_origins_are_configurable(self) -> None:
        origins = _allowed_origins(
            {"ALLOWED_ORIGINS": "https://client.example, https://client.example/"}
        )
        self.assertIn("https://chatgpt.com", origins)
        self.assertEqual(origins.count("https://client.example"), 1)

    def test_markdown_can_be_chunked_and_resumed(self) -> None:
        first = chunk_markdown("first line\nsecond line\nthird line", max_chars=23)
        self.assertEqual(first.markdown, "first line\nsecond line\n")
        self.assertEqual(first.next_offset, 23)
        self.assertTrue(first.has_more)
        second = chunk_markdown(
            "first line\nsecond line\nthird line",
            offset=first.next_offset or 0,
            max_chars=23,
        )
        self.assertEqual(second.markdown, "third line")
        self.assertFalse(second.has_more)
        self.assertIsNone(second.next_offset)

    def test_chunk_bounds_are_validated(self) -> None:
        for offset, max_chars in ((-1, 20), (0, 0), (4, 20)):
            with self.assertRaises(ValueError):
                chunk_markdown("abc", offset=offset, max_chars=max_chars)


if __name__ == "__main__":
    unittest.main()

