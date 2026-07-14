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

    LOCAL_HEADLESS = ("local_headless", "本地无头浏览器")
    LOCAL_HEADED = ("local_headed", "本地有头浏览器")
    LOCAL_APPIUM = ("local_appium", "本地 Appium")
    REMOTE_NODE = ("remote_node", "远程执行节点")
