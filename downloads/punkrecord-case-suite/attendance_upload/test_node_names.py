import pytest
from node_names import node_name, unchanged_steps


@pytest.mark.parametrize(("path", "body", "actor", "inputs", "expected"), [
    ("/meeting/records", {"meeting_type": "morning"}, None, {}, "创建早会-类型：早会"),
    ("/meeting/records", {"meeting_type": "{{meeting_type}}"}, None, {"meeting_type": "weekly"}, "创建会议-类型：周会"),
    ("/meeting/records", {"meeting_type": "other"}, "L0管理员", {}, "创建会议-类型：其他"),
    ("/beli/orders/{{bound_order_id}}/action", {"action": "approve"}, "直属主管", {}, "审核订单：直属主管同意通过"),
    ("/beli/orders/{id}/action", {"action": "reject"}, "L0管理员", {}, "审核订单：L0管理员拒绝"),
    ("/todo/leaves/{id}/approve", {}, "直属主管", {}, "审核请假：直属主管同意通过"),
])
def test_business_labels_include_meeting_type_or_review_actor(path, body, actor, inputs, expected):
    assert node_name({"method": "POST", "path": path, "body": body}, actor, inputs) == expected


def test_names_do_not_modify_step_configuration():
    before = {"version": 1, "inputs": {}, "nodes": [{"key": "create", "name": "POST /meeting/records"}]}
    after = {"version": 2, "inputs": {}, "nodes": [{"key": "create", "name": "创建早会-类型：早会"}]}
    assert unchanged_steps(before) == unchanged_steps(after)
    assert before["nodes"][0]["name"] == "POST /meeting/records"


def test_unknown_business_route_requires_an_explicit_label():
    with pytest.raises(KeyError):
        node_name({"method": "POST", "path": "/new-business"})
