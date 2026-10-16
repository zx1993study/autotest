"""Executable scenario templates grouped by test principle code."""

from app.core.types import JsonObject
from app.enums.business import KnowledgePrincipleEnum


def _scenario(
    title: str,
    objective: str,
    steps: list[str],
    expected: str,
) -> JsonObject:
    """Build one normalized scenario consumed by plan generation."""

    return {
        "title": title,
        "objective": objective,
        "steps": steps,
        "expected": expected,
    }


PRINCIPLE_SCENARIOS: dict[str, list[JsonObject]] = {
    KnowledgePrincipleEnum.CONDITION_COVERAGE.code: [
        _scenario(
            "单条件成立",
            "验证每个独立条件成立时进入目标分支。",
            ["准备满足条件的数据", "执行页面操作"],
            "页面进入需求约定的目标状态。",
        ),
        _scenario(
            "单条件不成立",
            "验证每个独立条件不成立时不会误入目标分支。",
            ["准备不满足条件的数据", "执行相同页面操作"],
            "页面保持在非目标状态并给出正确反馈。",
        ),
        _scenario(
            "关键条件组合",
            "验证多个条件同时成立、部分成立时的组合行为。",
            ["构造关键条件组合", "逐组执行页面操作"],
            "每组结果与需求中的组合规则一致。",
        ),
    ],
    KnowledgePrincipleEnum.BOUNDARY_TESTING.code: [
        _scenario("最小边界", "验证最小允许值及其相邻值。", ["输入最小值", "输入小于最小值的数据"], "最小值可接受，越界值被阻止。"),
        _scenario("最大边界", "验证最大允许值及其相邻值。", ["输入最大值", "输入大于最大值的数据"], "最大值可接受，越界值被阻止。"),
        _scenario("空值与零值边界", "验证空值、零值及默认值行为。", ["分别输入空值、零值和默认值", "提交表单"], "结果符合字段必填和取值规则。"),
    ],
    KnowledgePrincipleEnum.EXCEPTION_TESTING.code: [
        _scenario("非法输入", "验证非法格式和特殊字符不会产生脏数据。", ["输入非法格式或特殊字符", "提交表单"], "页面明确提示错误且数据未写入。"),
        _scenario("重复提交", "验证连续点击或重复请求不会重复写入。", ["连续触发提交操作", "检查列表和后台结果"], "只产生一份有效数据或明确拒绝重复操作。"),
        _scenario("请求失败恢复", "验证超时或服务失败后的页面反馈与重试。", ["模拟请求失败", "恢复服务后重试"], "失败有明确提示，重试后可正常完成。"),
    ],
    KnowledgePrincipleEnum.SMOKE_TESTING.code: [
        _scenario("页面可访问", "确认页面可正常打开且关键区域完成加载。", ["进入目标页面", "等待关键内容加载"], "页面无阻断错误，关键控件可见可用。"),
        _scenario("核心查询", "确认默认查询或主要检索功能可用。", ["输入典型条件", "执行查询"], "列表或详情返回符合条件的数据。"),
        _scenario("核心提交", "确认主要新增、保存或提交链路可完成。", ["填写最小有效数据", "提交并检查结果"], "操作成功且页面数据及时刷新。"),
    ],
    KnowledgePrincipleEnum.BULK_INSERT.code: [
        _scenario("正常批量新增", "验证多条合法数据可一次性新增。", ["准备多条合法数据", "执行批量新增"], "新增数量、内容和提示均正确。"),
        _scenario("批量上限", "验证最大批量数量及超限处理。", ["按上限提交", "按上限加一提交"], "上限内成功，超限请求被明确拒绝。"),
        _scenario("部分数据异常", "验证批量数据中存在非法或重复记录时的一致性。", ["混入非法或重复数据", "执行批量新增"], "按需求执行全部回滚或明确返回逐条结果。"),
    ],
    KnowledgePrincipleEnum.INPUT_OVERWRITE.code: [
        _scenario("异步回填不覆盖", "验证用户先输入后加载的数据不会覆盖输入内容。", ["页面加载后立即输入", "等待异步数据返回"], "用户输入保持不变。"),
        _scenario("切换关联项不误覆盖", "验证切换下拉或关联项后的字段联动符合需求。", ["输入自定义内容", "切换关联选项"], "仅需求指定字段被重置或回填。"),
        _scenario("失败重试保留输入", "验证提交失败后输入内容可继续修改和重试。", ["填写表单并模拟提交失败", "检查并修改原输入"], "原内容仍保留且可再次提交。"),
    ],
    KnowledgePrincipleEnum.TEXT_LENGTH_LIMIT.code: [
        _scenario("文本最大长度", "验证最大长度文本可以保存。", ["输入恰好达到最大长度的文本", "提交保存"], "保存成功且内容完整。"),
        _scenario("文本长度超限", "验证键入和粘贴超限文本的处理一致。", ["键入超限文本", "粘贴超限文本并提交"], "输入被限制或提交被明确阻止。"),
        _scenario("多字节字符长度", "验证中文、符号等字符的长度计算符合需求。", ["输入中英文和符号组合", "达到并超过长度限制"], "字符计数和服务端校验一致。"),
    ],
    KnowledgePrincipleEnum.NUMBER_RANGE_LIMIT.code: [
        _scenario("数字范围边界", "验证最小值、最大值及相邻越界值。", ["依次输入最小值、最大值和越界值", "提交表单"], "范围内可保存，越界值被拒绝。"),
        _scenario("数字精度与步长", "验证小数位数和步长限制。", ["输入允许精度", "输入超精度和非步长值"], "数值按需求校验或规范化。"),
        _scenario("非数字与科学计数", "验证非法字符和特殊数字格式。", ["输入字母、符号、科学计数法", "提交表单"], "仅需求允许的数字格式可以提交。"),
    ],
}
