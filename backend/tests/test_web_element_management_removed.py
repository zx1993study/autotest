"""Retired Web element management must not leave public endpoints behind."""

import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router


class WebElementManagementRemovedTest(unittest.TestCase):
    def test_public_crud_is_not_registered(self):
        app = FastAPI()
        app.include_router(api_router, prefix="/api/v1")
        paths = app.openapi()["paths"]
        self.assertFalse(any(path.startswith("/api/v1/web-testing/elements") for path in paths))
        self.assertIn("/api/v1/web-testing/pages", paths)
        self.assertIn("/api/v1/web-testing/case-drafts/generate", paths)
        self.assertIn("/api/v1/web-testing/cases/run", paths)
        self.assertIn("/api/v1/web-testing/vision-discovery", paths)
        with TestClient(app) as client:
            for method, path in (
                ("GET", ""), ("POST", ""), ("POST", "/batch-delete"),
                ("GET", "/42"), ("PUT", "/42"), ("DELETE", "/42"),
            ):
                with self.subTest(method=method, path=path):
                    response = client.request(method, f"/api/v1/web-testing/elements{path}")
                    self.assertEqual(404, response.status_code)

    def test_exclusive_management_files_are_physically_removed(self):
        root = Path(__file__).resolve().parents[2]
        for name in (
            "frontend/src/views/web-testing/WebElementsPage.vue",
            "backend/app/api/v1/web_elements.py",
            "backend/app/services/web_element_service.py",
        ):
            with self.subTest(path=name):
                self.assertFalse((root / name).exists())


if __name__ == "__main__":
    unittest.main()
