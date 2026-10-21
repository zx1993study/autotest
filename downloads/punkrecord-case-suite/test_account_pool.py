import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from account_pool import load_pool, use_existing_accounts, read_password, save_password


class FakeSuite:
    def __init__(self, pool, status="inactive"):
        self.users = {a["id"]: {**a, "status": status, "profile_completed": True, "must_change_password": False}
                      for a in pool["accounts"].values()}
        self.state = {"fixtures": []}
        self.calls = []
        self.logins = []

    def direct(self, actor, method, path, body=None):
        self.calls.append((actor, method, path, body))
        if method == "GET":
            return copy.deepcopy(self.users[path.rsplit("/", 1)[-1]])
        if method == "PATCH":
            self.users[path.rsplit("/", 1)[-1]].update(body)
            return
        raise AssertionError("User creation and password reset are forbidden")

    def login(self, actor, username, password):
        self.logins.append((actor, username))

    def save(self):
        pass


class AccountPoolTests(unittest.TestCase):
    def setUp(self):
        self.pool = load_pool()

    def test_inactive_accounts_are_reused_not_created(self):
        suite = FakeSuite(self.pool)
        use_existing_accounts(suite, self.pool, "test-secret")
        self.assertEqual(len(suite.logins), 4)
        self.assertEqual([c[1] for c in suite.calls], ["GET"] * 4 + ["PATCH"] * 4)
        self.assertTrue(all(u["reused"] and u["original_status"] == "inactive" for u in suite.state["fixtures"]))

    def test_active_accounts_are_not_reactivated(self):
        suite = FakeSuite(self.pool, "active")
        use_existing_accounts(suite, self.pool, "test-secret")
        self.assertEqual([c[1] for c in suite.calls], ["GET"] * 4)

    def test_repeated_reuse_never_creates(self):
        for _ in range(2):
            suite = FakeSuite(self.pool)
            use_existing_accounts(suite, self.pool, "test-secret")
            self.assertFalse(any(c[1] == "POST" for c in suite.calls))

    def test_wrong_username_fails_before_mutation(self):
        suite = FakeSuite(self.pool)
        suite.users[self.pool["accounts"]["employee"]["id"]]["username"] = "real_employee"
        with self.assertRaises(AssertionError):
            use_existing_accounts(suite, self.pool, "test-secret")
        self.assertTrue(all(c[1] == "GET" for c in suite.calls))
        self.assertFalse(suite.state["fixtures"])

    def test_missing_account_does_not_create_replacement(self):
        suite = FakeSuite(self.pool)
        del suite.users[self.pool["accounts"]["other"]["id"]]
        with self.assertRaises(KeyError):
            use_existing_accounts(suite, self.pool, "test-secret")
        self.assertTrue(all(c[1] == "GET" for c in suite.calls))

    def test_wrong_reporting_line_is_rejected(self):
        suite = FakeSuite(self.pool)
        suite.users[self.pool["accounts"]["employee"]["id"]]["manager_user_id"] = None
        with self.assertRaises(AssertionError):
            use_existing_accounts(suite, self.pool, "test-secret")
        self.assertTrue(all(c[1] == "GET" for c in suite.calls))

    def test_missing_secret_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "creation is disabled"):
                read_password(self.pool, Path(directory) / "missing.json")

    def test_cleanup_restores_fixed_account_without_deleting(self):
        from case_suite_runner import Suite
        suite = Suite.__new__(Suite)
        suite.prefix = "CASE_NEW_RUN"
        suite.account_pool = self.pool
        suite.sessions = {}
        suite.state = {"fixtures": [{"type": "user", "id": a["id"], "name": a["display_name"],
                        "username": a["username"], "reused": True, "original_status": "inactive"}
                       for a in self.pool["accounts"].values()], "cleanup": []}
        calls = []
        suite.direct = lambda actor, method, path, body: calls.append((method, path, body))
        suite.save = lambda: None
        suite.cleanup()
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(method == "PATCH" and body == {"status": "inactive"} for method, _, body in calls))
        self.assertTrue(all(item["status"] == "success" for item in suite.state["cleanup"]))

    @unittest.skipUnless(os.name == "nt", "DPAPI requires Windows")
    def test_secret_round_trip_is_not_plaintext(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / "vault.json"
            save_password(self.pool, "unit-test-secret", path)
            self.assertNotIn("unit-test-secret", path.read_text())
            self.assertEqual(read_password(self.pool, path), "unit-test-secret")


if __name__ == "__main__":
    unittest.main()
