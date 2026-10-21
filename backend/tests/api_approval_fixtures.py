"""In-memory business server for approval campaign contract/safety tests."""

from copy import deepcopy

PATHS = {12083: ("GET", ""), 12086: ("POST", ""), 12098: ("GET", "customer_id"),
         12108: ("GET", ""), 12110: ("POST", ""), 12113: ("GET", "activity_id"),
         12116: ("GET", ""), 12117: ("GET", "activity_type"), 12119: ("POST", ""),
         12121: ("GET", ""), 12126: ("POST", ""), 12129: ("GET", "apply_id"),
         12169: ("GET", ""), 12170: ("GET", "flow_id"), 12173: ("POST", ""), 12175: ("POST", ""),
         12179: ("GET", ""), 12181: ("GET", "instance_id"), 12182: ("PUT", ""), 12198: ("GET", ""), 12199: ("POST", ""),
         12202: ("GET", "order_id"), 12203: ("POST", "order_id"), 12204: ("GET", ""),
         12205: ("POST", ""), 12208: ("GET", "order_id"), 12219: ("GET", ""),
         12221: ("POST", ""), 12223: ("GET", "return_id")}


class ApprovalHTTP:
    def __init__(self, specs, fault=""):
        self.specs = specs
        self.fault = fault
        self.calls, self.records, self.instances, self.flows = [], {}, {}, {}
        self.type = {}
        self.counter = 500
        self.flow_ids = {"terminal": 1, "direct": 5, "kol": 6, "sales": 12, "sales_direct": 24, "return": 13, "purchase": 11}

    def allocate(self):
        self.counter += 1
        return self.counter

    def spec_for_create(self, api, body):
        candidates = [row for row in self.specs if row.create == api]
        if api == 12086:
            return next(row for row in candidates if row.customer_type == body["customerType"])
        if api == 12205:
            return next(row for row in candidates if row.key == ("sales_direct" if body["order"]["salesType"] == "1" else "sales"))
        return candidates[0]

    def begin_approval(self, spec, record):
        instance_id = record[spec.id_field] + 1000
        if spec.key in {"activity", "apply"}:
            flow_id = next(flow["flowId"] for flow in self.flows.values() if flow["businessType"] == spec.business_type)
        else:
            flow_id = self.flow_ids[spec.key]
        record["approvalInstanceId"] = instance_id
        self.instances[instance_id] = {"spec": spec, "record": record, "instance": {
            "instanceId": instance_id, "businessId": record[spec.id_field], "flowId": flow_id,
            "businessType": spec.business_type, "processStatus": "0", "currentNodeId": 71, "currentNodeOrder": 3},
            "nodeInstances": [{"nodeInstanceId": instance_id + 1000, "nodeId": 71, "nodeOrder": 3,
                               "instanceId": instance_id, "approverId": 1, "nodeStatus": "0", "isCurrent": "1", "approveResult": None}]}

    def create_record(self, spec, body):
        record = deepcopy(body.get("order", body))
        record[spec.id_field] = self.allocate()
        record[spec.status] = "0" if spec.key == "purchase" else spec.pending
        if spec.key == "apply":
            assert record["activityId"] == self.records["activity"]["activityId"]
            assert self.records["activity"]["approvalStatus"] == "1"
        if spec.key == "activity":
            assert record["activityType"] == self.type["activityType"]
        self.records[spec.key] = record
        if spec.key != "purchase":
            self.begin_approval(spec, record)
        return {"code": 200, "data": {spec.id_field: record[spec.id_field]}}

    def read_process(self, instance_id):
        entry = self.instances[instance_id]
        result = {"instance": deepcopy(entry["instance"]), "nodeInstances": deepcopy(entry["nodeInstances"])}
        if result["instance"]["processStatus"] == "0":
            if self.fault == "wrong_business":
                result["instance"]["businessId"] += 1
            if self.fault == "wrong_approver":
                result["nodeInstances"][0]["approverId"] = 2
            if self.fault == "not_current":
                result["nodeInstances"][0]["isCurrent"] = "0"
            if self.fault == "auto_skipped":
                result["instance"]["processStatus"] = "1"
            if self.fault == "multiple_nodes":
                result["nodeInstances"].append(deepcopy(result["nodeInstances"][0]))
        return {"code": 200, "data": result}

    def approve(self, body, headers):
        assert headers["Authorization"] == "Bearer private-reviewer"
        entry = next(row for row in self.instances.values() if row["nodeInstances"][0]["nodeInstanceId"] == body["nodeInstanceId"])
        assert entry["instance"]["processStatus"] == "0"
        assert body["approveResult"] in {"1", "2"}
        result, spec = body["approveResult"], entry["spec"]
        entry["instance"]["processStatus"] = result
        entry["nodeInstances"][0].update(nodeStatus=result, approveResult=result)
        rejected = "2" if spec.key in {"terminal", "direct", "kol"} else spec.rejected
        entry["record"][spec.status] = spec.passed if result == "1" else rejected
        if self.fault == "wrong_final_status":
            entry["record"][spec.status] = "3"
        return {"code": 200}

    def workflow(self, api, body, query, tail):
        if api == 12173:
            flow = {**deepcopy(body), "flowId": self.allocate(), "nodes": []}
            assert flow["isDefault"] == "0" and flow["activityType"] == self.type["activityType"]
            self.flows[flow["flowId"]] = flow
            return {"code": 200}
        if api == 12169:
            return {"code": 200, "rows": [flow for flow in self.flows.values() if flow["flowName"] == query["flowName"]]}
        if api == 12175:
            assert body["approverType"] == "1" and body["approverIds"] == "1"
            self.flows[body["flowId"]]["nodes"].append(body)
            return {"code": 200}
        flow = self.flows[int(tail)]
        return {"code": 200, "data": {"flow": flow, "nodes": flow["nodes"]}}

    def send(self, request):
        import json

        self.calls.append(deepcopy(request))
        parts = request["path"].split("/")
        api, tail = int(parts[2]), parts[-1]
        body, query = request["body"], request["query"]
        if api == 12119:
            self.type = {**deepcopy(body), "configId": self.allocate(), "activityType": f"isolated_{self.counter}"}
            response = {"code": 200}
        elif api == 12116:
            response = {"code": 200, "rows": [self.type]}
        elif api == 12117:
            response = {"code": 200, "data": self.type}
        elif api in {12169, 12170, 12173, 12175}:
            response = self.workflow(api, body, query, tail)
        elif api == 12181:
            response = self.read_process(int(tail))
        elif api == 12182:
            response = self.approve(body, request["headers"])
        elif api == 12203:
            spec = next(row for row in self.specs if row.key == "purchase")
            record = self.records[spec.key]
            assert record["orderId"] == int(tail)
            record[spec.status] = spec.pending
            self.begin_approval(spec, record)
            response = {"code": 200}
        elif request["method"] == "POST":
            response = self.create_record(self.spec_for_create(api, body), body)
        else:
            response = self.read_record(api, tail)
        return 200, {"Content-Type": "application/json"}, json.dumps(response)

    def read_record(self, api, tail):
        spec = next(row for row in self.specs if row.key in self.records and api in {row.listing, row.detail})
        record = deepcopy(self.records[spec.key])
        if api == spec.listing:
            if self.fault == "wrong_owner":
                record[spec.marker] = "historical-record"
            return {"code": 200, "rows": [record]}
        assert record[spec.id_field] == int(tail)
        data = {"order": record} if spec.root == "/data/order" else {"apply": record} if spec.key == "apply" else record
        result = {"code": 200, "data": data}
        if spec.customer_type:
            result["approvalProcess"] = {"instanceId": record["approvalInstanceId"]}
        return result
