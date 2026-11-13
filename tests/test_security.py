import unittest

from convert2md_server.app import _is_public_address, _safe_suffix, _validate_url_shape


class SecurityHelpersTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

