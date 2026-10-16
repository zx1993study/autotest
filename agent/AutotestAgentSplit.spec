import os
import json
from importlib.util import find_spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
profile = os.environ.get("AUTOTEST_AGENT_PROFILE", "mobile")
if profile not in {"core", "mobile", "mobile-web", "web", "ai-web", "full"}:
    raise ValueError("Unsupported Agent profile")
packages = ["pystray", "PIL"]
excluded = ["app", "sqlalchemy", "pymysql", "fastapi", "uvicorn", "tidevice", "tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide6"]
if profile in {"mobile", "mobile-web", "full"}:
    packages.extend(["wda", "imageio", "imageio_ffmpeg"])
else:
    excluded.extend(["wda", "imageio", "imageio_ffmpeg", "numpy", "agent_app.executors.mobile_case_executor"])
if profile in {"web", "mobile-web", "ai-web", "full"}:
    packages.append("playwright")
else:
    excluded.extend(["playwright", "agent_app.executors.web_case_executor"])
if profile in {"ai-web", "full"}:
    packages.extend(["stagehand", "litellm", "tiktoken_ext"])
else:
    excluded.extend(["stagehand", "litellm", "tiktoken"])
data, binaries, imports = [], [], []
for package in packages:
    if find_spec(package) is None:
        raise ModuleNotFoundError(f"Install the {profile} Agent requirements before building: {package}")
    d, b, i = collect_all(package, include_py_files=False)
    data.extend(d)
    binaries.extend(b)
    imports.extend(i)
if "playwright" in packages:
    package_root = Path(find_spec("playwright").origin).parent
    registry = json.loads((package_root / "driver/package/browsers.json").read_text(encoding="utf-8"))
    revision = next(b["revision"] for b in registry["browsers"] if b["name"] == "ffmpeg")
    browser_root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path(os.environ["LOCALAPPDATA"]) / "ms-playwright")
    ffmpeg_dir = browser_root / f"ffmpeg-{revision}"
    if not (ffmpeg_dir / "ffmpeg-win64.exe").is_file():
        raise FileNotFoundError("Install the matching Playwright FFmpeg runtime before building a Web Agent")
    data.append((str(ffmpeg_dir / "ffmpeg-win64.exe"), f"playwright/driver/package/.local-browsers/ffmpeg-{revision}"))
    if (ffmpeg_dir / "COPYING.LGPLv2.1").is_file():
        data.append((str(ffmpeg_dir / "COPYING.LGPLv2.1"), f"playwright/driver/package/.local-browsers/ffmpeg-{revision}"))
a = Analysis([str(root / "agent/agent_app/main.py")], pathex=[str(root / "agent"), str(root / "web_automation/src")], binaries=binaries, datas=data, hiddenimports=imports, excludes=excluded, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AutotestAgent", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="AutotestAgent", upx=False)
