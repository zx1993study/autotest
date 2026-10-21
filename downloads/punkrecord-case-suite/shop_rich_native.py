"""Additional real native purchase flows: contract boundaries and state invariants."""
from datetime import datetime
from decimal import Decimal
import json
import os
import re
import time
from uuid import uuid4

from account_pool import load_pool, read_password, use_existing_accounts
import case_suite_runner as core
from case_suite_runner import BASE, CN, HERE, PROJECT_ID, Platform, write_json
from native_replay_82 import Replay, UUID

OUTPUT = HERE / "shop-rich-native-results.json"
OMIT = object()


class Shop(Replay):
    def __init__(self, output=OUTPUT):
        assert not output.exists(), "Do not duplicate a completed purchase suite"
        core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
        self.platform, self.output = Platform(), output
        self.case_label = "SHOPPLUS"
        self.reuse_read_cases = True
        self.prefix = "CASE_" + datetime.now(CN).strftime("%Y%m%d_%H%M%S")
        self.state = {"target": BASE, "project_id": PROJECT_ID, "run_prefix": self.prefix,
            "started_at": datetime.now(CN).isoformat(), "scenarios": [], "fixtures": [], "cleanup": [], "path_fields": {}}
        previous = HERE / "native-82-results.json"
        if previous.exists():
            self.state["path_fields"] = json.loads(previous.read_text(encoding="utf-8")).get("path_fields", {})
        self.sessions, self.auth, self.user_ids, self.interfaces = {}, {}, {}, {}
        self.translations = {}
        self.pid = "00000000-0000-0000-0000-000000000000"
        self.current = None
        self.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        pool = load_pool()
        use_existing_accounts(self, pool, read_password(pool))
        self.source_interfaces = []
        for page in range(1, 30):
            batch = self.platform.call("GET", f"/api-testing/interfaces?project_id={PROJECT_ID}&page={page}&pageSize=200")
            self.source_interfaces.extend(batch["items"])
            if len(self.source_interfaces) >= batch["total"]:
                break
        self.skus = {}
        self.state["baseline_account"] = self.balance()
        self.save()

    def interface(self, method, path):
        def normalize(value):
            return re.sub(r"\{[^{}]+\}", "{id}", UUID.sub("{id}", value))
        canonical = normalize(path)
        key = method + " " + canonical
        if key in self.interfaces:
            return self.interfaces[key]
        matches = [row for row in self.source_interfaces if row.get("data", {}).get("method", "").upper() == method
                   and normalize(row.get("data", {}).get("path", "")) == canonical]
        if matches:
            item = min(matches, key=lambda row: row["id"])
        else:
            item = self.platform.call("POST", "/api-testing/interfaces", {"project_id": PROJECT_ID,
                "name": "商城 " + key, "status": "active", "data": {"method": method, "path": path,
                    "module": "贝利商城", "api_base_path": "/api/v1"}})
            self.source_interfaces.append(item)
        self.interfaces[key] = item["id"]
        return item["id"]

    def product(self, key, *, price="3.33", stock=10, active=True, kind="physical"):
        body = {"name": self.prefix + " SHOPPLUS " + key, "kind": kind, "price": price, "stock": stock, "active": active}
        if kind == "leave":
            body.update(leave_type="annual", leave_days=.5)
        row = self.direct("manager", "POST", "/beli/products", body)
        self.skus[key] = row
        self.state["fixtures"].append({"type": "product", "id": row["id"], "name": row["name"], "body": body})
        self.save()
        return row

    def balance(self, actor="employee"):
        return self.direct(actor, "GET", "/beli/accounts")["items"][0]

    def sku_now(self, sku_id):
        return next(row for row in self.direct("manager", "GET", "/beli/products") if row["id"] == sku_id)

    def ledger(self, actor="employee"):
        result = []
        for page in range(1, 100):
            batch = self.direct(actor, "GET", f"/beli/ledger?user_id={self.user_ids[actor]}&page={page}")
            result.extend(batch)
            if len(batch) < 30:
                return result
        raise AssertionError("Ledger pagination exceeded safety limit")

    def step(self, key, actor, method, path, body=None, *, expected=200, equals=None, response=None):
        self.plan.append({"key": key, "actor": actor, "method": method, "path": path, "body": body or {},
            "expected": expected, "equals": equals or {}, "contains": None, "missing": [], "content_type": "application/json",
            "source_id": self.interface(method, path), "response": response or {"code": 0, "data": {}}})

    def account_step(self, key, before, *, frozen_delta=0, balance_delta=0, leave_delta=0, actor="employee"):
        balance = Decimal(str(before["balance"])) + Decimal(str(balance_delta))
        frozen = Decimal(str(before["frozen"])) + Decimal(str(frozen_delta))
        self.step(key, actor, "GET", "/beli/accounts", equals={"data.items.0.user_id": self.user_ids[actor],
            "data.items.0.balance": float(balance), "data.items.0.frozen": float(frozen),
            "data.items.0.available": float(balance - frozen),
            "data.items.0.leave.annual": float(Decimal(str(before["leave"]["annual"])) + Decimal(str(leave_delta)))})

    def execute(self, code, title, build, verify):
        self.current = {"code": code, "title": title, "status": "running", "case_ids": [], "started_at": datetime.now(CN).isoformat()}
        self.state["scenarios"].append(self.current)
        self.plan = []
        flow = None
        try:
            build()
            nodes = self.compile()
            flow = self.platform.call("POST", "/execution/flows", {"project_id": PROJECT_ID, "name": "商城补充 " + code,
                "description": title + "；远程15173；核对订单/库存/冻结/余额，结果见商城补充报告；复跑需准备新夹具。", "status": "active",
                "data": {"version": 1, "inputs": {}, "nodes": nodes}})
            scene = self.platform.call("POST", f"/execution/flows/{flow['id']}/scenarios", {"name": title, "status": "active",
                "data": {"flow_id": flow["id"], "template_version": flow["data"]["version"], "nodes": {}, "failure_policy": "continue", "expected_end": "auto"}})
            batch = self.platform.call("POST", f"/execution/flows/{flow['id']}/runs", {"scenario_ids": [scene["id"]], "mode": "serial", "concurrency": 1, "inputs": {}})
            self.current.update(flow_id=flow["id"], scenario_id=scene["id"], run_id=batch["id"])
            self.save()
            while batch["status"] in {"queued", "running"}:
                time.sleep(1)
                batch = self.platform.call("GET", f"/execution/flows/{flow['id']}/runs/{batch['id']}")
            self.current["native_result"] = batch
            rows = batch["data"]["results"][0]["nodes"]
            values = {}
            for item, row in zip(self.plan, rows):
                response = row.get("outputs", {}).get("response")
                if response is None:
                    try:
                        response = json.loads(row.get("response_body", "{}"))
                    except ValueError:
                        response = {}
                values[item["key"]] = response.get("data")
            self.current["semantic_checks"] = verify(values)
            failed = [{"step": self.plan[index]["key"], "status": row["status"], "http": row.get("response_status"),
                "error": row.get("error"), "assertions": [entry for entry in row.get("assertions", []) if not entry.get("passed")]} for index, row in enumerate(rows) if row["status"] != "success"]
            assert not failed, json.dumps(failed, ensure_ascii=False)
            self.current.update(status="success", semantic_assertions_passed=True)
        except Exception as error:
            self.current.update(status="failed", error=str(error)[:2500])
        finally:
            if flow:
                self.platform.call("PUT", f"/execution/flows/{flow['id']}", {"status": "disabled"})
            self.current["finished_at"] = datetime.now(CN).isoformat()
            self.save()
            print(self.current["status"].upper(), code, "run=" + str(self.current.get("run_id")), self.current.get("error", ""), flush=True)

    def cancel_step(self, key, order_id, *, actor="employee", expected=200, action="cancel"):
        self.step(key, actor, "POST", f"/beli/orders/{order_id}/action", {"action": action}, expected=expected,
            equals={"data.status": "cancelled"} if expected == 200 and action == "cancel" else {})

    def purchase(self, code, title, *, quantity=1, expected=422, sku="standard", changes=None, remove=(), actor="employee"):
        product = self.skus[sku]
        watched = actor if actor != "manager" else "employee"
        before, stock = self.balance(watched), self.sku_now(product["id"])["stock"]
        orders_before = {row["id"] for row in self.direct(watched, "GET", "/beli/orders")}
        ledger_before = {row["id"] for row in self.ledger(watched)}
        order_id = str(uuid4())
        body = {"product_id": product["id"], "request_key": str(uuid4()), "delivery": self.prefix + " test collection"}
        if quantity is not OMIT:
            body["quantity"] = quantity
        body.update(changes or {})
        for key in remove:
            body.pop(key, None)
        actual_quantity = 1 if quantity is OMIT else quantity
        amount = Decimal(str(product["price"])) * Decimal(str(actual_quantity)) if expected == 200 else Decimal(0)
        def build():
            self.step("purchase", actor, "POST", "/beli/orders", body, expected=expected,
                equals={"data.quantity": actual_quantity, "data.amount": f"{amount:.2f}", "data.status": "pending"} if expected == 200 else {},
                response={"code": 0, "data": {"id": order_id}} if expected == 200 else None)
            self.account_step("after_account", before, frozen_delta=amount, actor=watched)
            self.step("after_products", "manager", "GET", "/beli/products")
            self.step("after_orders", watched, "GET", "/beli/orders")
            if expected == 200:
                self.cancel_step("cancel", order_id, actor=actor)
                self.account_step("restored_account", before, actor=watched)
                self.step("restored_products", "manager", "GET", "/beli/products")
        def verify(values):
            after = next(row for row in values["after_products"] if row["id"] == product["id"])
            new_orders = {row["id"] for row in values["after_orders"]} - orders_before
            if expected == 200:
                assert after["stock"] == stock - actual_quantity, "Stock not reduced by quantity"
                assert new_orders == {values["purchase"]["id"]}, "Purchase did not create exactly one order"
                restored = next(row for row in values["restored_products"] if row["id"] == product["id"])
                assert restored["stock"] == stock, "Cancellation did not restore stock"
            else:
                assert after["stock"] == stock and not new_orders, "Rejected purchase changed stock/orders"
            assert {row["id"] for row in self.ledger(watched)} == ledger_before, "Purchase/cancel unexpectedly wrote balance ledger"
            return {"stock_before": stock, "stock_after_purchase": after["stock"], "new_order_count": len(new_orders), "ledger_unchanged": True}
        try:
            self.execute(code, title, build, verify)
        finally:
            for order in self.direct(watched, "GET", "/beli/orders"):
                if order["id"] not in orders_before and order["product_id"] == product["id"] and order["status"] == "pending":
                    self.direct(watched, "POST", f"/beli/orders/{order['id']}/action", {"action": "cancel"})

    def richer_flows(self):
        product = self.skus["standard"]
        before = self.balance()
        symbolic = str(uuid4())
        body = {"product_id": product["id"], "quantity": 2, "request_key": str(uuid4()), "delivery": "test"}
        amount = Decimal(str(product["price"])) * 2
        stock = self.sku_now(product["id"])["stock"]
        def idempotency():
            self.step("first", "employee", "POST", "/beli/orders", body, response={"code": 0, "data": {"id": symbolic}})
            self.step("same", "employee", "POST", "/beli/orders", body)
            self.step("different_quantity", "employee", "POST", "/beli/orders", {**body, "quantity": 3}, expected=400)
            self.step("different_delivery", "employee", "POST", "/beli/orders", {**body, "delivery": "different"}, expected=400)
            self.step("different_product", "employee", "POST", "/beli/orders", {**body, "product_id": self.skus["limited"]["id"]}, expected=400)
            self.account_step("frozen_once", before, frozen_delta=amount)
            self.step("products", "manager", "GET", "/beli/products")
            self.cancel_step("cancel", symbolic)
            self.account_step("restored", before)
        def check_idempotency(values):
            assert values["first"]["id"] == values["same"]["id"], "Same request key created different orders"
            assert next(row for row in values["products"] if row["id"] == product["id"])["stock"] == stock - 2
            return {"single_order_id": values["first"]["id"], "freeze_once": float(amount), "changed_payload_rejected": 3}
        self.execute("SHOPPLUS-IDEMPOTENCY", "同键重放只建一单；变更数量、配送、商品均拒绝", idempotency, check_idempotency)

        before = self.balance()
        symbolic = str(uuid4())
        def permissions():
            self.step("create", "employee", "POST", "/beli/orders", {**body, "quantity": 1, "request_key": str(uuid4())}, response={"code": 0, "data": {"id": symbolic}})
            self.cancel_step("other_cancel", symbolic, actor="other", expected=403)
            self.cancel_step("employee_approve", symbolic, action="approve", expected=403)
            self.cancel_step("ship_pending", symbolic, actor="manager", action="ship", expected=400)
            self.step("invalid_action", "manager", "POST", f"/beli/orders/{symbolic}/action", {"action": "unknown"}, expected=422)
            self.cancel_step("missing_order", str(uuid4()), actor="manager", expected=404)
            self.cancel_step("owner_cancel", symbolic)
            self.account_step("restored", before)
        self.execute("SHOPPLUS-ACTION-GUARDS", "他人取消、员工审批、未批准发货、无效操作及不存在订单", permissions,
                     lambda values: {"cancelled_order": values["owner_cancel"]["id"], "guard_branches": 5})

        before = self.balance()
        exact = self.product("exact_available", price=str(before["available"]), stock=1)
        symbolic = str(uuid4())
        def exact_balance():
            self.step("exact", "employee", "POST", "/beli/orders", {"product_id": exact["id"], "request_key": str(uuid4()), "delivery": "test"}, response={"code": 0, "data": {"id": symbolic}})
            self.account_step("all_frozen", before, frozen_delta=before["available"])
            self.step("cannot_overspend", "employee", "POST", "/beli/orders", {"product_id": self.skus["penny"]["id"], "request_key": str(uuid4()), "delivery": "test"}, expected=400)
            self.cancel_step("cancel", symbolic)
            self.account_step("restored", before)
        self.execute("SHOPPLUS-EXACT-BALANCE", "可用余额恰好等于总价可兑换，冻结后不能再透支", exact_balance,
                     lambda values: {"frozen_exactly": before["available"], "extra_purchase_rejected": True})

        before = self.balance()
        product = self.skus["leave"]
        symbolic = str(uuid4())
        amount = Decimal(str(product["price"])) * 2
        def leave_quantity():
            self.step("create", "employee", "POST", "/beli/orders", {"product_id": product["id"], "quantity": 2, "request_key": str(uuid4())},
                equals={"data.amount": f"{amount:.2f}", "data.quantity": 2}, response={"code": 0, "data": {"id": symbolic}})
            self.account_step("frozen", before, frozen_delta=amount)
            for key in ("approve", "repeat_approve"):
                self.step(key, "manager", "POST", f"/beli/orders/{symbolic}/action", {"action": "approve"}, equals={"data.status": "fulfilled"})
            self.account_step("paid_once", before, balance_delta=-amount, leave_delta=1)
            self.cancel_step("cannot_refund_fulfilled", symbolic, actor="manager", expected=400)
            self.cancel_step("cannot_ship_leave", symbolic, actor="manager", action="ship", expected=400)
        self.execute("SHOPPLUS-LEAVE-MULTIPLE", "兑换2份半天假期：只扣款一次、增加1天，履约后不可取消发货", leave_quantity,
                     lambda values: {"paid": float(amount), "annual_days_added": 1, "repeat_approval_idempotent": values["approve"]["id"] == values["repeat_approve"]["id"]})

    def run_all(self):
        self.product("standard")
        self.product("penny", price="0.01", stock=100)
        self.product("limited", price="1.23", stock=3)
        self.product("zero_stock", stock=0)
        self.product("inactive", active=False)
        self.product("expensive", price="9999999999.99", stock=100)
        self.product("leave", kind="leave", price="1.23", stock=5)
        invalid = [("ZERO", 0), ("NEGATIVE", -1), ("HUGE-NEGATIVE", -9999999999999999999999),
            ("FRACTION", 1.5), ("SMALL-FRACTION", .0005), ("NULL", None), ("EMPTY", ""),
            ("TEXT", "abc"), ("NAN", "NaN"), ("INFINITY", "Infinity"), ("OBJECT", {}), ("ARRAY", []),
            ("MAX-PLUS-ONE", 101), ("HUGE", 99999999999999999999999999)]
        for name, quantity in invalid:
            self.purchase("SHOPPLUS-QTY-" + name, f"购买数量={quantity!r} 拒绝且无副作用", quantity=quantity)
        for name, quantity, sku in (("DEFAULT", OMIT, "standard"), ("MIN", 1, "standard"), ("MULTIPLE", 2, "standard"),
                                     ("MAX", 100, "penny"), ("EXACT-STOCK", 3, "limited")):
            self.purchase("SHOPPLUS-NORMAL-" + name, "正常兑换数量" + ("默认1" if quantity is OMIT else str(quantity)) + "，取消后恢复", quantity=quantity, sku=sku, expected=200)
        variants = [
            ("MISSING-PRODUCT", 422, {}, ("product_id",)), ("NULL-PRODUCT", 422, {"product_id": None}, ()),
            ("BAD-PRODUCT", 422, {"product_id": "bad-uuid"}, ()), ("MISSING-KEY", 422, {}, ("request_key",)),
            ("NULL-KEY", 422, {"request_key": None}, ()), ("BAD-KEY", 422, {"request_key": "invalid"}, ()),
            ("NO-PRODUCT", 400, {"product_id": str(uuid4())}, ()),
            ("EMPTY-DELIVERY", 400, {"delivery": ""}, ()), ("BLANK-DELIVERY", 400, {"delivery": "   "}, ()),
            ("LONG-DELIVERY", 422, {"delivery": "x" * 1001}, ())]
        for name, expected, changes, remove in variants:
            self.purchase("SHOPPLUS-INPUT-" + name, "兑换参数异常 " + name, changes=changes, remove=remove, expected=expected)
        self.purchase("SHOPPLUS-DELIVERY-MAX", "配送信息1000字符边界可兑换", changes={"delivery": "x" * 1000}, expected=200)
        self.purchase("SHOPPLUS-STOCK-ZERO", "库存为0拒绝兑换", sku="zero_stock", expected=400)
        self.purchase("SHOPPLUS-STOCK-OVER", "库存3件购买4件拒绝", sku="limited", quantity=4, expected=400)
        self.purchase("SHOPPLUS-INACTIVE", "已下架商品拒绝兑换", sku="inactive", expected=400)
        self.purchase("SHOPPLUS-AMOUNT-LARGE", "超出可用余额的大额总价拒绝", sku="expensive", quantity=100, expected=400)
        self.purchase("SHOPPLUS-L0-FORBIDDEN", "L0不属于商城兑换员工范围", actor="manager", expected=403)
        self.purchase("SHOPPLUS-OTHER-INSUFFICIENT", "固定另一员工余额不足拒绝兑换", actor="other", sku="expensive", expected=400)
        self.richer_flows()


def main():
    suite = Shop()
    try:
        suite.run_all()
    finally:
        suite.state["final_account"] = suite.balance()
        suite.cleanup()
        suite.state["finished_at"] = datetime.now(CN).isoformat()
        suite.save()
        print("SUMMARY", json.dumps({"total": len(suite.state["scenarios"]), "success": sum(row["status"] == "success" for row in suite.state["scenarios"]),
            "failed": [row["code"] for row in suite.state["scenarios"] if row["status"] != "success"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
