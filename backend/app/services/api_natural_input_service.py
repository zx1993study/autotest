"""Natural free-text examples, with bounded timestamp names for created records."""

import hashlib
from typing import Any


def natural_text_example(field: dict[str, Any], fallback: str) -> str:
    name = str(field.get("name") or "").lower()
    description = str(field.get("description") or "")
    examples = [("商品名称", "晨露矿泉水"), ("仓库名称", "洪山配送仓"),
                ("活动名称", "秋季门店陈列活动"), ("模板名称", "城区门店周拜访计划"),
                ("任务内容", "核对门店陈列并记录补货需求"), ("拜访内容", "了解门店销售情况并确认补货安排"),
                ("备注", "按门店日常补货安排办理"), ("地址", "武汉市洪山区珞喻路配送中心")]
    value = next((value for label, value in examples if label in description), None)
    if value is None and name.endswith("name"):
        value = "晨星门店" if "customer" in name else "日常业务记录"
    if value is None:
        value = "日常业务说明" if name in {"remark", "description", "content"} else fallback
    return value


def timestamp_text(value: str, maximum: int | None, scenario_key: str) -> str:
    if "{{timestamp_ms}}" in value:
        return value
    discriminator = hashlib.sha256(scenario_key.encode("utf-8")).hexdigest()[:6]
    suffix = f"_{{{{timestamp_ms}}}}_{discriminator}"
    # A resolved millisecond timestamp occupies 13 characters, not the token's length.
    reserved = 21
    if maximum is not None:
        if maximum <= reserved:
            raise ValueError("字符串长度上限不足以容纳自然名称、毫秒时间戳和场景标识")
        value = value[:maximum - reserved]
    return value + suffix
