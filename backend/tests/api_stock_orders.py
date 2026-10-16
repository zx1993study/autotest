"""Independent in-memory order/approval rules for stock campaign tests."""

from copy import deepcopy
from typing import ClassVar


class OrderBook:
    SPECS: ClassVar[dict[str, tuple[str, str, int, str]]] = {"purchase": ("orderId", "orderStatus", 11, "purchase_in_order"),
             "sales": ("orderId", "orderStatus", 12, "sales_order"), "return": ("returnId", "returnStatus", 13, "return_order")}

    def __init__(self, server):
        self.server = server
        self.orders, self.instances = {}, {}

    def validate(self, kind, body):
        order, items = body.get("order", body), body.get("items", [])
        if not items or not order.get("warehouseId") or (kind != "purchase" and not order.get("customerId")):
            return False
        item = items[0]
        quantity = item.get("returnQuantity" if kind == "return" else "quantity", 0)
        if quantity <= 0:
            return False
        if kind == "sales":
            stock = self.server.stock.get(item["productId"], {"quantity": 0, "lockedQuantity": 0})
            return quantity <= stock["quantity"] - stock["lockedQuantity"]
        if kind == "return" and order.get("returnOrderType") == "1":
            original = self.orders.get(order.get("salesOrderId"))
            if not original or original["kind"] != "sales" or original["order"]["orderStatus"] != "5":
                return False
            source = original["items"][0]
            returned = sum(row["items"][0]["returnQuantity"] for row in self.orders.values()
                           if row["kind"] == "return" and row["order"].get("salesOrderId") == order["salesOrderId"]
                           and row["order"]["returnStatus"] != "4")
            return (item.get("salesItemId") == source["itemId"] and item["productId"] == source["productId"]
                    and quantity <= source["quantity"] - returned)
        return True

    def create(self, kind, body):
        if not self.validate(kind, body):
            return self.server.reject()
        owned_id = self.server.allocate()
        field, status, _, _ = self.SPECS[kind]
        order = {**deepcopy(body.get("order", body)), field: owned_id, status: "1" if kind == "purchase" else "2",
                 "orderNo" if kind != "return" else "returnNo": f"OWN-{owned_id}"}
        order.pop("items", None)
        items = deepcopy(body["items"])
        items[0]["itemId"] = self.server.allocate()
        entry = {"kind": kind, "order": order, "items": items}
        self.orders[owned_id] = entry
        self.begin(owned_id)
        return {"code": 200, "data": {field: owned_id}}

    def begin(self, owned_id):
        entry = self.orders[owned_id]
        instance_id = self.server.allocate()
        _, _, flow_id, business_type = self.SPECS[entry["kind"]]
        entry["order"]["approvalInstanceId"] = instance_id
        self.instances[instance_id] = {"owned_id": owned_id, "instance": {"instanceId": instance_id,
            "businessId": owned_id, "flowId": flow_id, "businessType": business_type, "processStatus": "0"},
            "nodeInstances": [{"instanceId": instance_id, "nodeInstanceId": self.server.allocate(),
                               "approverId": 1, "isCurrent": "1", "nodeStatus": "0", "approveResult": None}]}

    def detail(self, owned_id):
        entry = deepcopy(self.orders[owned_id])
        for item in entry["items"]:
            key = "returnQuantity" if entry["kind"] == "return" else "quantity"
            item[key] = str(item[key])
        if entry["kind"] == "purchase":
            return {"code": 200, "data": {**entry["order"], "items": entry["items"]}}
        return {"code": 200, "data": {"order": entry["order"], "items": entry["items"]}}

    def process(self, instance_id):
        entry = self.instances[instance_id]
        return {"code": 200, "data": {"instance": deepcopy(entry["instance"]), "nodeInstances": deepcopy(entry["nodeInstances"])}}

    def approve(self, body, headers):
        server = self.server
        if headers.get("Authorization") != "Bearer private-reviewer":
            return server.reject(403)
        instance = next(row for row in self.instances.values() if row["nodeInstances"][0]["nodeInstanceId"] == body["nodeInstanceId"])
        if instance["instance"]["processStatus"] != "0":
            return server.reject()
        entry = self.orders[instance["owned_id"]]
        kind, item, result = entry["kind"], entry["items"][0], body["approveResult"]
        stock = server.stock.setdefault(item["productId"], {"quantity": 0, "lockedQuantity": 0})
        quantity = item.get("quantity", item.get("returnQuantity"))
        if kind == "sales" and result == "1" and quantity > stock["quantity"] - stock["lockedQuantity"]:
            return server.reject()
        status = self.SPECS[kind][1]
        if result == "2":
            entry["order"][status] = "3" if kind == "purchase" else "4"
        elif kind == "purchase":
            stock["quantity"] += quantity
            entry["order"][status] = "4"
        else:
            entry["order"][status] = "3"
            if kind == "sales" and server.fault != "wrong_lock":
                stock["lockedQuantity"] += quantity
            server.add_receipt(instance["owned_id"], entry)
        instance["instance"]["processStatus"] = result
        instance["nodeInstances"][0].update(nodeStatus=result, approveResult=result)
        return {"code": 200}
