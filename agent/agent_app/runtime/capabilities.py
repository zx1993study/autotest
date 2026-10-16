from __future__ import annotations

import os
from importlib.util import find_spec


def available_capabilities(plugins: tuple[str, ...]) -> tuple[str, ...]:
    capabilities = ["case_execution"]
    if "mobile" in plugins and find_spec("wda") is not None:
        capabilities.extend(["app_execution", "device_discovery", "app_exploration", "app_connection"])
    if "web" in plugins and find_spec("playwright") is not None:
        capabilities.append("web_execution")
        capabilities.append("web_vision_discovery")
        capabilities.append("web_replay")
        capabilities.append("web_recording")
        capabilities.append("web_secret_inputs")
        if os.name == "nt":
            capabilities.append("browser_window_control")
        if "ai_web" in plugins and find_spec("stagehand") is not None:
            capabilities.append("stagehand")
    return tuple(capabilities)
