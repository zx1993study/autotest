"""In-memory stock API with independently enforced inventory/ownership rules."""

import json
from copy import deepcopy

from tests.api_approval_fixtures import PATHS as APPROVAL_PATHS
from tests.api_stock_orders import OrderBook

PATHS = {**APPROVAL_PATHS, 12100: ("GET", ""), 12102: ("POST", ""), 12107: ("GET", "product_id"),
         12191: ("GET", "warehouse_id"), 12192: ("GET", "warehouse_id"), 12193: ("PUT", "warehouse_id"),
         12195: ("POST", "warehouse_id"), 12207: ("GET", "warehouse_id"), 12211: ("GET", ""),
         12213: ("GET", "inbound_id"), 12214: ("POST", ""), 12220: ("PUT", ""), 12222: ("DELETE", "return_ids"),
         12224: ("POST", "")}


def inventory_fixture(apis):
    return {"project_id": 10, "snapshot_id": 11942, "interfaces": [{"api": row} for row in apis],
        "fixtures": {"warehouse": {"warehouse_id": 230, "warehouse_name": "fixture-warehouse", "admin_user_id": 1, "warehouse_type": "1"},
            "customer": {"customer_id": 1083, "customer_name": "fixture-customer"},
            "products": [{"product_type": "water", "product_brand": "water", "unit": "瓶"}],
            "dicts": [{"dict_type": kind, "dict_value": value} for kind, value in (
                ("product_type", "water"), ("product_brand", "water"), ("product_unit", "瓶"), ("product_unit", "件"))]},
        "business": {"test_users": [{"user_id": user_id, "user_name": username, "status": "0", "del_flag": "0"}
            for user_id, username in ((1, "admin"), (251, "qa_approval_manager"), (252, "qa_approval_direct"))],
            "test_user_roles": [{"user_id": user_id, "role_id": role} for user_id, role in ((1, 1), (251, 2), (252, 112))],
            "approval_flow_definition": {"configuration": [{"flow_id": flow, "business_type": business,
                "creator_role_id": role, "status": "0", "activity_type": None, "is_default": "0" if role else "1"}
                for flow, business, role in ((11, "purchase_in_order", 2), (12, "sales_order", None), (13, "return_order", None))]},
            "approval_flow_node": {"configuration": [{"flow_id": flow, "approver_type": "1", "approver_ids": "1"} for flow in (11, 12, 13)]}}}


class StockHTTP:
    def __init__(self, fault=""):
        self.fault, self.calls, self.products, self.receipts = fault, [], {}, {}
        self.stock = {5: {"quantity": 200, "lockedQuantity": 20}}
        self.counter = 2000
        self.book = OrderBook(self)

    def allocate(self):
        self.counter += 1
        return self.counter

    @staticmethod
    def reject(code=400):
        return {"code": code, "msg": "Business validation rejected", "success": False}

    def add_receipt(self, owned_id, entry):
        inbound_id, kind = self.allocate(), entry["kind"]
        quantity = entry["items"][0].get("quantity", entry["items"][0].get("returnQuantity"))
        self.receipts[inbound_id] = {"order": {"inboundId": inbound_id, "sourceType": "2" if kind == "return" else "1",
            "sourceId": owned_id, "warehouseId": 0 if kind == "return" else 230, "targetWarehouseId": 230 if kind == "return" else None,
            "inboundStatus": "2" if kind == "return" else "0"},
            "items": [{"productId": entry["items"][0]["productId"], "quantity": quantity}]}

    def receipt(self, api, body, query, tail, headers):
        if api == 12211:
            rows = [deepcopy(entry["order"]) for entry in self.receipts.values()
                    if entry["order"]["sourceType"] == query["sourceType"] and entry["order"]["sourceId"] == query["sourceId"]]
            if rows and self.fault == "wrong_receipt_owner":
                rows[0]["sourceId"] += 1
            return {"code": 200, "rows": rows}
        if api == 12213:
            entry = deepcopy(self.receipts[int(tail)])
            if self.fault == "wrong_receipt_product":
                entry["items"][0]["productId"] = 5
            if self.fault == "wrong_receipt_quantity":
                entry["items"][0]["quantity"] += 1
            return {"code": 200, "data": entry}
        if headers.get("Authorization") != "Bearer private-reviewer":
            return self.reject(403)
        entry = self.receipts[body["inboundId"]]
        order = entry["order"]
        is_return = order["sourceType"] == "2"
        if order["inboundStatus"] != ("2" if is_return else "0"):
            return self.reject()
        item = entry["items"][0]
        stock = self.stock[item["productId"]]
        stock["quantity"] += item["quantity"] if is_return else -item["quantity"]
        if not is_return:
            stock["lockedQuantity"] -= item["quantity"]
        order["inboundStatus"] = "1" if is_return else "2"
        self.book.orders[order["sourceId"]]["order"]["returnStatus" if is_return else "orderStatus"] = "5"
        return {"code": 200}

    def convert(self, body, headers):
        if headers.get("Authorization") != "Bearer private-reviewer":
            return self.reject(403)
        required = ("sourceProductId", "targetProductId", "sourceQuantity", "targetQuantity")
        if any(key not in body for key in required):
            return self.reject(422)
        source_id, target_id, quantity, target_quantity = (body[key] for key in required)
        stock = self.stock.get(source_id)
        if (not stock or source_id == target_id or quantity <= 0 or target_quantity <= 0
                or quantity > stock["quantity"] - stock["lockedQuantity"]):
            return self.reject()
        stock["quantity"] -= quantity
        self.stock.setdefault(target_id, {"quantity": 0, "lockedQuantity": 0})["quantity"] += target_quantity
        return {"code": 200}

    def product(self, api, body, query, tail):
        if api == 12102:
            product_id = self.allocate()
            self.products[product_id] = {**body, "productId": product_id, "delFlag": "0"}
            return {"code": 200}
        if api == 12100:
            return {"code": 200, "rows": [row for row in self.products.values() if row["productName"] == query["productName"]]}
        return {"code": 200, "data": self.products[int(tail)]}

    def dispatch(self, api, request, tail):
        body, query, headers = request["body"], request["query"], request["headers"]
        if api in {12100, 12102, 12107}:
            return self.product(api, body, query, tail)
        if api == 12191:
            return {"code": 200, "data": {"warehouseId": 230, "warehouseName": "fixture-warehouse", "adminUserId": 1, "status": "0", "delFlag": "0"}}
        if api == 12192:
            product_id = query["productId"]
            stock = self.stock.get(product_id)
            return {"code": 200, "rows": [] if stock is None else [{"productId": product_id, "warehouseId": 230,
                **stock, "availableQuantity": stock["quantity"] - stock["lockedQuantity"]}]}
        if api == 12193:
            assert body["productId"] in self.products, "Never initialize an existing business SKU"
            if body["productId"] not in self.stock:
                return {"code": 500, "msg": "库存记录不存在", "success": False}
            self.stock[body["productId"]] = {"quantity": body["quantity"], "lockedQuantity": 0}
            return {"code": 200}
        if api == 12195:
            return self.convert(body, headers)
        if api in {12211, 12213, 12214}:
            return self.receipt(api, body, query, tail, headers)
        if api in {12199, 12205, 12221}:
            return self.book.create({12199: "purchase", 12205: "sales", 12221: "return"}[api], body)
        if api == 12203:
            return self.reject()
        if api in {12202, 12208, 12223}:
            return self.book.detail(int(tail))
        if api in {12204, 12219}:
            return {"code": 200, "rows": [entry["order"] for entry in self.book.orders.values()
                if entry["kind"] == ("sales" if api == 12204 else "return") and entry["order"].get("remark") == query["remark"]]}
        if api == 12181:
            return self.book.process(int(tail))
        if api == 12182:
            return self.book.approve(body, headers)
        if api in {12220, 12222, 12224}:
            return self.reject()
        raise AssertionError(f"Unexpected API {api}")

    def send(self, request):
        self.calls.append(deepcopy(request))
        parts = request["path"].split("/")
        response = self.dispatch(int(parts[2]), request, parts[-1])
        return 200, {"Content-Type": "application/json"}, json.dumps(response, ensure_ascii=False)
