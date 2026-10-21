"""Compile multiple historical branches onto a shared, ordered API template."""
import re
from copy import deepcopy

UUID = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", re.IGNORECASE)


def signature(step):
    path = UUID.sub("{id}", step["request"]["path"])
    path = re.sub(r"\{[^{}]+\}", "{id}", path)
    return step["request"]["method"].upper(), path


def flatten(flow, scene, cases):
    from app.services.api_flow_values import apply_request_override

    steps = []
    for node in flow["data"]["nodes"]:
        override = scene["data"].get("nodes", {}).get(node["key"], {})
        if override.get("mode") == "skip":
            continue
        assert not node.get("routes") and node.get("next", "auto") in {"auto", "end"}, "Explicit routing needs manual review"
        assert not override.get("condition"), "Conditional source needs manual review"
        case = cases[override.get("case_id") or node["case_id"]]
        data = deepcopy(case["data"])
        legacy = data.pop("request", {})
        data = {**legacy, **data}
        for configured in (node, override):
            apply_request_override(data, configured)
        auth_id = node.get("auth_id") or data.get("auth_id")
        assert auth_id, "Do not infer authentication"
        steps.append({"old_key": node["key"], "api_id": node["api_id"], "case_id": case["id"],
            "auth_id": auth_id, "request": data,
            "assertions": deepcopy(override.get("assertions") if override.get("assertions") is not None else case.get("assertions", [])),
            "bindings": deepcopy(override.get("bindings") if override.get("bindings") is not None else node.get("bindings", [])),
            "extracts": deepcopy(override.get("extracts") if override.get("extracts") is not None else node.get("extracts", []))})
        if node.get("next") == "end":
            break
    return steps


def merge_order(left, right):
    """Shortest common supersequence; repeated calls retain their relative order."""
    n, m = len(left), len(right)
    sizes = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n:
                sizes[i][j] = m - j
            elif j == m:
                sizes[i][j] = n - i
            else:
                sizes[i][j] = 1 + (sizes[i + 1][j + 1] if left[i] == right[j] else min(sizes[i + 1][j], sizes[i][j + 1]))
    result, i, j = [], 0, 0
    while i < n or j < m:
        if i == n:
            result.extend(right[j:])
            break
        if j == m:
            result.extend(left[i:])
            break
        if left[i] == right[j]:
            result.append(left[i]); i += 1; j += 1
        elif sizes[i + 1][j] <= sizes[i][j + 1]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result


def compile_group(branches, canonical):
    order = []
    for branch in branches:
        order = merge_order(order, [signature(s) for s in branch["steps"]])
    assert len(order) <= 100, "Flow exceeds the platform node limit"
    nodes = [{"key": f"node_{i + 1:02}", "name": method + " " + path,
              "api_id": canonical[(method, path)], "next": "auto"} for i, (method, path) in enumerate(order)]
    for branch in branches:
        positions, cursor = {}, 0
        for step in branch["steps"]:
            while order[cursor] != signature(step):
                cursor += 1
            positions[step["old_key"]] = nodes[cursor]["key"]
            cursor += 1
        overrides = {n["key"]: {"mode": "skip"} for n in nodes}
        for step in branch["steps"]:
            key = positions[step["old_key"]]
            bindings = deepcopy(step["bindings"])
            for binding in bindings:
                if binding["source"] != "global":
                    assert binding["source"] in positions, "Binding points outside this branch"
                    binding["source"] = positions[binding["source"]]
            overrides[key] = {"mode": "always", "request": deepcopy(step["request"]),
                              "bindings": bindings, "extracts": deepcopy(step["extracts"]),
                              "assertions": deepcopy(step["assertions"]),
                              "case_key": repr((signature(step), step["auth_id"]))}
        branch["compiled"] = {"inputs": deepcopy(branch["inputs"]), "nodes": overrides,
            "failure_policy": branch["failure_policy"], "expected_end": positions[branch["steps"][-1]["old_key"]]}
    return {"inputs": {}, "nodes": nodes}
