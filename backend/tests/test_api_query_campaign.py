import importlib
import json
from copy import deepcopy
from threading import Event
from unittest.mock import patch

from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from tests.test_api_crud_campaign import CrudCampaignTest


class QueryCampaignTest(CrudCampaignTest):
    def query_spec(self):
        builder = importlib.import_module("waiqin_query_builder")
        api = self.repo.get("api_interfaces", 12184)
        return builder.build_query_spec({"api": api, "module": "业务管理-测试", "query_fields": ["warehouseName", "warehouseType"],
                                        "fields": [{"name": name} for name in ("warehouseName", "warehouseType", "pageNum", "pageSize")]},
                                       {"params": {"pageNum": 1, "pageSize": 50}, "body": {"code": 200, "rows": [
                                           {"warehouseName": "江城配送仓", "warehouseType": "1"}]}})

    def test_append_is_idempotent_and_existing_mutation_scene_skips_helpers(self):
        self.generate()
        campaign = importlib.import_module("api_query_campaign")
        with patch("app.scheduler.jobs.api_case_executor.ApiCaseExecutor._send_http_request") as send:
            first = campaign.generate_queries(self.repo, self.args, [self.query_spec()])
            counts = {key: len(rows) for key, rows in self.repo.tables.items()}
            second = campaign.generate_queries(self.repo, self.args, [self.query_spec()])
        send.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual(counts, {key: len(rows) for key, rows in self.repo.tables.items()})
        flow = self.repo.get("execution_flows", first["flows"][0]["id"])
        scenes = ApiFlowScenarioService(self.repo).list_for_flow(flow["id"])
        original = next(scene for scene in scenes if scene["name"] == "增查改删闭环")
        self.assertEqual(original["data"]["nodes"]["qs_12184"]["mode"], "skip")
        self.assertEqual(original["data"]["nodes"]["qq_12184"]["mode"], "skip")
        self.assertEqual(original["data"]["template_version"], flow["data"]["version"])

    def test_dynamic_query_uses_latest_seed_and_never_sends_mutations(self):
        self.generate()
        campaign = importlib.import_module("api_query_campaign")
        manifest = campaign.generate_queries(self.repo, self.args, [self.query_spec()])
        flow = self.repo.get("execution_flows", manifest["flows"][0]["id"])
        scene = next(row for row in ApiFlowScenarioService(self.repo).list_for_flow(flow["id"])
                     if row["name"] == "条件查询 12184 - warehouseName")
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers", return_value={"Authorization": "Bearer token"}):
            snapshot = ApiFlowSnapshotService(self.repo).build(flow, scene, {})
        calls = []

        def send(request):
            calls.append(deepcopy(request))
            self.assertEqual(request["method"], "GET")
            if len(calls) == 2:
                self.assertEqual(request["query"]["warehouseName"], "新配送仓")
            return 200, {}, json.dumps({"code": 200, "rows": [{"warehouseName": "新配送仓", "warehouseType": "1"}]})

        with patch("app.scheduler.jobs.api_case_executor.ApiCaseExecutor._send_http_request", side_effect=send):
            result = ApiFlowRunner(snapshot, Event()).run()
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(calls), 2)

    def test_customer_plan_has_no_historical_mutation_ids(self):
        customer = importlib.import_module("waiqin_customer_campaign")
        for aid, kind in ((12086, "create"), (12083, "listing"), (12098, "detail"), (12088, "delete"),
                          (12085, "edit"), (12087, "edit"), (12099, "edit"), (12089, "edit")):
            self.api(aid, kind)
        # The customer adapter uses the actual OpenAPI path names.
        self.repo.tables["api_interfaces"][12098]["data"]["path"] = "/business/customer/{customer_id}"
        self.repo.tables["api_interfaces"][12088]["data"]["path"] = "/business/customer/{customer_ids}"
        plan = customer.customer_plan({"params": {"customerName": "便利店", "customerType": "1", "managerIds": [1], "editCount": 0}},
                                      self.repo.tables["api_interfaces"])
        by_key = {node["key"]: node for node in plan["nodes"]}
        self.assertEqual(by_key["edit"]["params"]["customerId"], "{{owned_id}}")
        self.assertEqual(by_key["batch_edit"]["params"]["customerIds"], "{{owned_ids}}")
        self.assertEqual(by_key["delete"]["params"]["customer_ids"], "{{owned_id}}")
        self.assertEqual(by_key["change_status"]["bindings"][0]["source"], "locate")
        self.assertEqual(by_key["verify_delete"]["api_id"], 12083)
        self.assertEqual(by_key["verify_delete"]["assertions"][-1]["max_items"], 0)

    def test_campaign_cache_tracks_writes_and_does_not_leak_mutable_values(self):
        cache = importlib.import_module("api_campaign_repository").CampaignRepository(self.repo)
        row = cache.create("api_test_cases", {"name": "Cached", "data": {"params": {"status": "1"}}})
        item = cache.get("api_test_cases", row["id"])
        item["data"]["params"]["status"] = "broken"
        self.assertEqual(cache.get("api_test_cases", row["id"])["data"]["params"]["status"], "1")
        cache.update("api_test_cases", row["id"], {"name": "Updated"})
        self.assertEqual(cache.get("api_test_cases", row["id"])["name"], "Updated")

    def test_empty_query_keeps_positive_fixture_disabled(self):
        builder = importlib.import_module("waiqin_query_builder")
        spec = builder.build_query_spec({"api": {"id": 12216}, "module": "业务管理-出库管理",
                                        "fields": [{"name": "outboundNo"}], "query_fields": ["outboundNo"]},
                                       {"params": {}, "body": {"code": 200, "rows": []}})
        positive = next(scene for scene in spec["scenes"] if scene["key"] == "positive_fixture")
        self.assertTrue(positive["blocked"])
        self.assertEqual(positive["assertions"][-1]["min_items"], 1)
        negative = next(scene for scene in spec["scenes"] if scene["key"] == "no_match")
        self.assertEqual(negative["assertions"][-1]["max_items"], 0)

    def test_dates_are_paired_and_sorting_is_not_mistaken_for_equality(self):
        builder = importlib.import_module("waiqin_query_builder")
        fields = [{"name": name} for name in ("beginTime", "endTime", "latitude", "longitude")]
        spec = builder.build_query_spec({"api": {"id": 12083}, "module": "客户管理", "fields": fields,
                                        "query_fields": [field["name"] for field in fields]},
                                       {"params": {}, "body": {"rows": [{"createTime": "2026-10-15 10:00:00", "latitude": 30, "longitude": 114}]}})
        date = next(scene for scene in spec["scenes"] if scene["key"] == "beginTime")
        self.assertEqual(date["params"]["beginTime"], "2026-10-14")
        self.assertEqual(date["params"]["endTime"], "2026-10-16")
        latitude = next(scene for scene in spec["scenes"] if scene["key"] == "latitude")
        self.assertTrue(latitude["blocked"])
        self.assertEqual(latitude["params"], {"latitude": 30, "longitude": 114})

    def test_todo_filter_is_scoped_to_its_own_business_type(self):
        builder = importlib.import_module("waiqin_query_builder")
        spec = builder.build_query_spec({"api": {"id": 12226}, "module": "业务管理-待办", "fields": [{"name": "warehouseName"}],
                                        "query_fields": ["warehouseName"]},
                                       {"params": {}, "body": {"data": {"todoList": [
                                           {"todoType": "stock_in_order", "extraData": {"warehouseName": "配送仓"}}]}}})
        scene = next(scene for scene in spec["scenes"] if scene["key"] == "warehouseName")
        self.assertNotIn("todoType", scene["params"])
        self.assertEqual(scene["rules"][-1]["expected"], "{{bound_q_todoType}}")
        self.assertEqual(scene["extracts"][-1]["path"], "/data/todoList/0/todoType")
        self.assertEqual(scene["bindings"][-1]["source"], scene["bindings"][0]["source"])
        self.assertEqual(scene["bindings"][-1]["name"], "q_todoType")

    def test_customer_multiselect_filters_use_tokens_for_single_and_combined_queries(self):
        builder = importlib.import_module("waiqin_query_builder")
        for name, value, kind in (("cooperationStatus", "正在合作", "1"), ("kolType", "个人用户", "3")):
            with self.subTest(field=name):
                fields = [{"name": field} for field in (name, "customerType")]
                spec = builder.build_query_spec({"api": {"id": 12083}, "module": "客户管理", "fields": fields,
                                                "query_fields": [field["name"] for field in fields]},
                                               {"params": {}, "body": {"rows": [{name: value, "customerType": kind}]}})
                for key in (name, "combined"):
                    scene = next(scene for scene in spec["scenes"] if scene["key"] == key)
                    rule = next(rule for rule in scene["rules"] if rule["paths"] == ["/" + name])
                    self.assertEqual(rule["operator"], "tokens")
                    self.assertEqual(rule["expected"], "{{bound_q_" + name + "}}")
                    self.assertTrue(all(rule["operator"] == "eq" for rule in scene["rules"]
                                        if rule["paths"] == ["/customerType"]))
        fields = [{"name": "warehouseType"}]
        spec = builder.build_query_spec({"api": {"id": 12184}, "module": "仓库管理", "fields": fields,
                                        "query_fields": ["warehouseType"]},
                                       {"params": {}, "body": {"rows": [{"warehouseType": "1"}]}})
        self.assertEqual(spec["scenes"][0]["rules"][0]["operator"], "eq")
