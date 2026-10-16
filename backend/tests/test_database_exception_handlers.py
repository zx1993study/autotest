import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import (
    DisconnectionError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from app.api.exception_handlers import register_exception_handlers


class DatabaseExceptionHandlersTest(unittest.TestCase):
    def response_for(self, error):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/database-test")
        def fail():
            raise error

        with patch("app.api.exception_handlers.logger.exception"), TestClient(app) as client:
            return client.get("/database-test")

    def test_sort_memory_error_is_not_reported_as_connection_failure(self):
        error = OperationalError("sensitive SQL", {"password": "secret"}, Exception(1038, "Out of sort memory"))
        response = self.response_for(error)
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["code"], 50301)
        self.assertIn("排序内存不足", payload["message"])
        self.assertNotIn("连接失败", payload["message"])
        self.assertEqual(payload["data"], {"path": "/database-test"})
        self.assertNotIn("secret", response.text)
        self.assertNotIn("sensitive SQL", response.text)

    def test_connection_failures_keep_connection_guidance(self):
        errors = [
            OperationalError("connect", {}, Exception(number, "Connection error"))
            for number in (1045, 1049, 2002, 2003, 2005, 2006, 2013, 2055)
        ]
        errors.extend([
            DisconnectionError("Connection lost"),
            OperationalError("query", {}, Exception("Disconnected"), connection_invalidated=True),
        ])
        for error in errors:
            with self.subTest(error=type(error).__name__):
                response = self.response_for(error)
                self.assertIn("数据库连接失败", response.json()["message"])

    def test_other_database_errors_have_safe_general_message(self):
        for error in (SQLAlchemyError("details"), IntegrityError("SQL", {}, Exception(1062, "Duplicate"))):
            with self.subTest(error=type(error).__name__):
                response = self.response_for(error)
                self.assertEqual(response.json()["message"], "数据库操作失败，请查看服务端日志。")
                self.assertNotIn("details", response.text)


if __name__ == "__main__":
    unittest.main()
