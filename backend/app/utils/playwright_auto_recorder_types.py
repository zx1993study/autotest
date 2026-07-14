from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from app.utils.select_control_resolver import SelectControlResolver


SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "storage" / "screenshots"
CONTROL_SELECTOR = (
    "input:not([type='hidden']), textarea, select, button, a, "
    "[role='button'], [role='link'], [role='textbox'], [role='radio'], [role='checkbox'], [contenteditable='true'], "
    f"{SelectControlResolver.control_selector()}"
)
DIALOG_SELECTOR = "[role='dialog'], .el-dialog, .el-drawer, .ant-modal, .ant-drawer, .modal, .drawer"


def ensure_windows_playwright_event_loop_policy() -> None:
    """Ensure Playwright can spawn its driver process on Windows worker threads."""

    if not sys.platform.startswith("win"):
        return

    proactor_policy = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    if proactor_policy is None:
        return

    if not isinstance(asyncio.get_event_loop_policy(), proactor_policy):
        asyncio.set_event_loop_policy(proactor_policy())


@dataclass
class ControlInfo:
    css: str
    tag: str
    role: str
    name: str
    input_type: str
    placeholder: str
    value: str
    disabled: bool
    visible: bool
    in_dialog: bool
    readonly: bool = False
    class_name: str = ""
    opener_css: str = ""

    @property
    def lower_name(self) -> str:
        return self.name.lower()
