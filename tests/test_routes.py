import unittest

from starlette.testclient import TestClient

from change2md_server.app import app
from vercel import app as vercel_app


class RouteTest(unittest.TestCase):
    def test_health_and_web_converter_routes(self) -> None:
        for application in (app, vercel_app):
            with self.subTest(application=application), TestClient(application) as client:
                health = client.get("/health")
                self.assertEqual(health.status_code, 200)
                self.assertEqual(health.json()["version"], "0.2.0")

                converter = client.get("/convert")
                self.assertEqual(converter.status_code, 200)
                self.assertIn("Turn a file or webpage into Markdown.", converter.text)

                options = client.options("/api/convert")
                self.assertEqual(options.status_code, 200)
                self.assertEqual(options.headers["access-control-allow-origin"], "*")


if __name__ == "__main__":
    unittest.main()
