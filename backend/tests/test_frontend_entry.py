from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import _mount_frontend


class FrontendEntryTest(unittest.TestCase):
    def test_html_is_not_cached_but_hashed_assets_keep_their_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
            (root / "assets").mkdir()
            (root / "assets" / "index-newhash.js").write_text('console.log("current")', encoding="utf-8")
            app = FastAPI()
            with patch("app.main._frontend_dist_candidates", return_value=[root]):
                _mount_frontend(app)
            with TestClient(app) as client:
                for path in ("/", "/login", "/reports/statistics", "/api/interfaces", "/api/interfaces/42",
                             "/api/interfaces/42/", "/api/flows", "/api/flows/42", "/api/flows/42/"):
                    response = client.get(path)
                    self.assertEqual(200, response.status_code)
                    self.assertEqual("no-store, max-age=0", response.headers["cache-control"])
                    self.assertEqual("no-cache", response.headers["pragma"])
                self.assertEqual('console.log("current")', client.get('/assets/index-newhash.js').text)
                self.assertEqual(404, client.get('/assets/index-oldhash.js').status_code)
                self.assertEqual(404, client.get('/api/v1/unknown').status_code)
                self.assertEqual(404, client.get('/api/unknown').status_code)
                self.assertEqual(404, client.get('/api/interfaces/42/missing').status_code)
                self.assertEqual(404, client.get('/api/flows/42/missing').status_code)
                for path in ('/api/fields?interface_id=42', '/api/case-drafts', '/api/cases'):
                    self.assertEqual(404, client.get(path).status_code)


if __name__ == "__main__":
    unittest.main()
