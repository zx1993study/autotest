import importlib
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.test_api_flows import MemoryRepository


class MemoryFiles:
    def __init__(self):
        self.values = {}

    def save_json(self, name, payload):
        self.values[name] = deepcopy(payload)
        return name


class ApprovalAccountsTest(unittest.TestCase):
    def setUp(self):
        scripts = str(Path(__file__).resolve().parents[2] / "scripts")
        sys.path.insert(0, scripts)
        self.addCleanup(lambda: sys.path.remove(scripts))
        self.module = importlib.import_module("waiqin_approval_accounts")
        self.spec = self.module.ACCOUNTS[0]
        self.api = Mock(project_id=10)
        self.files = MemoryFiles()
        self.state = {"purpose": self.module.PURPOSE, "project_id": 10, "username": self.spec["username"],
                      "role_id": 2, "marker": "owned-marker", "password": "private-password"}
        self.user = {"user_id": 251, "user_name": self.spec["username"], "dept_id": 229, "user_type": "00",
                     "status": "0", "del_flag": "0", "remark": "owned-marker"}
        self.roles = [{"user_id": 251, "role_id": 2}]

    def test_unowned_existing_username_is_never_modified(self):
        with (patch.object(self.module, "account_rows", return_value=([self.user], self.roles)),
              self.assertRaisesRegex(ValueError, "ownership proof")):
            self.module.ensure_account(self.api, None, self.spec, {}, self.files)
        self.api.send.assert_not_called()
        self.assertFalse(self.files.values)

    def test_owned_account_retry_does_not_create_or_reset_user(self):
        with patch.object(self.module, "account_rows", return_value=([self.user], self.roles)):
            state = self.module.ensure_account(self.api, None, self.spec, self.state, self.files)
        self.assertEqual(state["user_id"], 251)
        self.api.send.assert_not_called()

    def test_role_department_status_or_owner_drift_stops_without_writes(self):
        for key, value in (("dept_id", 1), ("status", "1"), ("del_flag", "2"), ("remark", "different")):
            with self.subTest(key=key):
                changed = {**self.user, key: value}
                with (patch.object(self.module, "account_rows", return_value=([changed], self.roles)),
                      self.assertRaises(ValueError)):
                    self.module.ensure_account(self.api, None, self.spec, self.state, self.files)
        with self.assertRaises(ValueError):
            self.module.check_owned_user(self.spec, self.state, [self.user], self.roles + [{"role_id": 1}])
        self.api.send.assert_not_called()

    def test_creation_checkpoint_precedes_http_and_contains_only_one_role(self):
        def create(api_id, payload):
            self.assertEqual(api_id, 11955)
            self.assertTrue(self.files.values)
            state = next(iter(self.files.values.values()))
            self.assertEqual(payload["roleIds"], [2])
            self.assertEqual(payload["password"], state["password"])
            self.user["remark"] = state["marker"]
        self.api.send.side_effect = create
        with patch.object(self.module, "account_rows", side_effect=lambda *_: ([self.user], self.roles) if self.api.send.called else ([], [])):
            state = self.module.ensure_account(self.api, None, self.spec, {}, self.files)
        self.assertEqual(state["user_id"], 251)
        self.assertEqual(self.api.send.call_count, 1)
        self.assertLessEqual(len(state["password"]), 20)

    def test_wrong_login_identity_or_extra_roles_are_rejected(self):
        profile = {"user": {"userId": 251, "userName": self.spec["username"], "status": "0", "delFlag": "0"}, "roles": ["common"]}
        self.module.verify_profile(profile, 251, self.spec["username"], "common")
        for bad in ({**profile, "roles": ["common", "admin"]}, {**profile, "user": {**profile["user"], "userId": 1}}):
            with self.assertRaises(ValueError):
                self.module.verify_profile(bad, 251, self.spec["username"], "common")

    def test_login_and_auth_are_idempotent_and_summary_contains_no_secrets(self):
        repo = MemoryRepository()
        self.state["user_id"] = 251
        with patch("app.services.project_auth_service.AuthFileService", return_value=self.files):
            first = self.module.save_auth(repo, 10, self.spec, self.state, "private-token")
            second = self.module.save_auth(repo, 10, self.spec, self.state, "private-token")
        self.assertEqual(first["auth_id"], second["auth_id"])
        self.assertEqual(len(repo.tables["project_auth"]), 1)
        self.assertEqual(len(repo.tables["api_test_cases"]), 1)
        self.assertNotIn("private-password", json.dumps(second))
        self.assertNotIn("private-token", json.dumps(repo.tables["project_auth"]))
        auth = repo.get("project_auth", first["auth_id"])
        self.assertEqual(auth["data"]["role_ids"], [2])
        login = repo.get("api_test_cases", first["login_case_id"])
        self.assertTrue(login["data"]["skip_auth"])

    def test_wrong_admin_stops_before_any_provisioning(self):
        args = SimpleNamespace(project_id=10, auth_id=10015)
        with patch.object(self.module, "AccountAPI", return_value=self.api), patch.object(self.module, "ensure_account") as ensure:
            self.api.send.return_value = {"user": {"userId": 2}, "roles": ["common"]}
            with self.assertRaises(ValueError):
                self.module.provision(MemoryRepository(), args)
        ensure.assert_not_called()

    def test_transport_redacts_error_body_and_does_not_retry_post(self):
        api = self.module.AccountAPI.__new__(self.module.AccountAPI)
        api.project_id, api.admin_auth_id, api.executor = 10, 10015, Mock()
        api.executor._send_http_request.return_value = (200, {}, '{"code":500,"msg":"private-password"}')
        with self.assertRaises(ValueError) as error:
            api.send(11955, {"password": "private-password"})
        self.assertNotIn("private-password", str(error.exception))
        self.assertEqual(api.executor._send_http_request.call_count, 1)
        with self.assertRaisesRegex(ValueError, "Only user creation"):
            api.send(12182)


if __name__ == "__main__":
    unittest.main()
