from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parents[1]
data, binaries, imports = collect_all("webview", include_py_files=False)
a = Analysis([str(root / "packaging/desktop/launcher.py")], pathex=[str(root / "packaging/desktop"), str(root / "agent")], binaries=binaries, datas=data + [(str(root / "packaging/desktop/connection.html"), ".")], hiddenimports=imports, excludes=["app", "sqlalchemy", "pymysql", "fastapi", "uvicorn", "playwright", "stagehand", "litellm", "wda", "numpy", "imageio", "imageio_ffmpeg", "tidevice", "PIL", "pystray"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AutotestPlatform", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="AutotestPlatform", upx=False)
