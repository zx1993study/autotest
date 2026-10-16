"""Business enums shared by validation, persistence, and API output."""

from app.enums.base import DescribedStrEnum


class ResourceStatusEnum(DescribedStrEnum):
    """Lifecycle status for generic resources."""

    ACTIVE = ("active", "启用")
    DRAFT = ("draft", "草稿")
    DISABLED = ("disabled", "停用")
    ARCHIVED = ("archived", "归档")


class CaseDraftStatusEnum(DescribedStrEnum):
    """Review status for generated test case drafts."""

    DRAFT = ("draft", "待审核")
    ACCEPTED = ("accepted", "已采纳")
    REJECTED = ("rejected", "已驳回")


class CaseTypeEnum(DescribedStrEnum):
    """Supported automation test domains."""

    API = ("API", "API")
    WEB = ("WEB", "Web")
    APP = ("APP", "App")
    MINIAPP = ("MINIAPP", "小程序")


class ExecutionModeEnum(DescribedStrEnum):
    """Supported local and remote execution modes."""

    SERVER_HEADLESS = ("server_headless", "服务器无头浏览器")
    LOCAL_HEADLESS = ("local_headless", "本地无头浏览器")
    LOCAL_HEADED = ("local_headed", "本地有头浏览器")
    LOCAL_APPIUM = ("local_appium", "本地 Appium")
    REMOTE_NODE = ("remote_node", "远程执行节点")


class WebEngineEnum(DescribedStrEnum):
    """Execution engines for Web test cases."""

    PLAYWRIGHT = ("playwright", "静态定位")
    STAGEHAND = ("stagehand", "AI 执行")
    HYBRID = ("hybrid", "智能混合")


class ExecutionPlanStatusEnum(DescribedStrEnum):
    """Lifecycle status for execution plans."""

    ACTIVE = ("active", "进行中")
    DONE = ("done", "已完成")


class ExecutionPlanTestTypeEnum(DescribedStrEnum):
    """Case domains that can be included in an execution plan."""

    WEB = ("WEB", "Web")
    API = ("API", "API")
    APP = ("APP", "App")
    ALL = ("ALL", "全部")


class KnowledgePrincipleEnum(DescribedStrEnum):
    """System-managed principles used to design requirement-based tests."""

    CONDITION_COVERAGE = ("condition_coverage", "条件覆盖原则")
    BOUNDARY_TESTING = ("boundary_testing", "边界测试")
    EXCEPTION_TESTING = ("exception_testing", "异常测试")
    SMOKE_TESTING = ("smoke_testing", "冒烟测试")
    BULK_INSERT = ("bulk_insert", "批量插入数据")
    INPUT_OVERWRITE = ("input_overwrite", "输入框内容是否被覆盖")
    TEXT_LENGTH_LIMIT = ("text_length_limit", "文本框输入超限")
    NUMBER_RANGE_LIMIT = ("number_range_limit", "数字输入框超限")


class ExecutionRunStatusEnum(DescribedStrEnum):
    """Aggregate status for one execution plan run."""

    QUEUED = ("queued", "排队中")
    RUNNING = ("running", "执行中")
    SUCCESS = ("success", "成功")
    FAILED = ("failed", "失败")
    PARTIAL = ("partial", "部分通过")


class ExecutionRunItemStatusEnum(DescribedStrEnum):
    """Status for a single case within an execution plan run."""

    QUEUED = ("queued", "排队中")
    RUNNING = ("running", "执行中")
    SUCCESS = ("success", "成功")
    FAILED = ("failed", "失败")
    SKIPPED = ("skipped", "已跳过")


class AgentNodeStatusEnum(DescribedStrEnum):
    """Lifecycle status for installed local execution agents."""

    ONLINE = ("online", "在线")
    OFFLINE = ("offline", "离线")
    BUSY = ("busy", "忙碌")
    DISABLED = ("disabled", "停用")


class AgentTaskStatusEnum(DescribedStrEnum):
    """Dispatch status for tasks claimed by installed local agents."""

    PENDING = ("pending", "待领取")
    RUNNING = ("running", "执行中")
    SUCCESS = ("success", "成功")
    FAILED = ("failed", "失败")
    CANCELED = ("canceled", "已取消")


class AgentTaskTypeEnum(DescribedStrEnum):
    """Task types that can run inside the local agent package."""

    CASE_EXECUTION = ("case_execution", "用例执行")
    DEVICE_DISCOVERY = ("device_discovery", "设备扫描")
    WEB_VISION_DISCOVERY = ("web_vision_discovery", "Web AI 发现")
    WEB_REPLAY = ("web_replay", "Web 截图复现")
    APP_EXPLORATION = ("app_exploration", "App 设备实操生成")
