"""Activate a checksum-verified release behind the existing systemd service."""
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import tarfile
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path("/home/xiaox/apps/autotest")


def command(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def healthy(port):
    for _ in range(25):
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                value = json.load(response)
                if value.get("service") == "Autotest Platform" and value.get("ready") is True:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Platform readiness check failed")


def point_to(release):
    temporary = ROOT / "current.next"
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError("Pending release switch already exists")
    temporary.symlink_to(release)
    os.replace(temporary, ROOT / "current")


def activate(version, checksum):
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", version):
        raise ValueError("Invalid release version")
    archive = ROOT / "releases" / f"AutotestPlatform-server-{version}.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest().lower() != checksum.lower():
        raise ValueError("Release checksum mismatch")
    current = ROOT / "current"
    if not current.is_symlink():
        raise RuntimeError("Current release must be a symlink")
    previous = current.resolve(strict=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8801))
    release = ROOT / "releases" / version
    release.mkdir()
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if not (release / member.name).resolve().is_relative_to(release) or member.issym() or member.islnk():
                raise ValueError("Unsafe release archive")
        bundle.extractall(release, filter="data")
    candidate = f"autotest-candidate-{version}"
    command("systemd-run", "--user", f"--unit={candidate}", "--collect", f"--property=WorkingDirectory={release}", str(ROOT / "shared/venv/bin/python"), str(release / "packaging/server/run.py"), "--shared-dir", str(ROOT / "shared"), "--port", "8801")
    switched = False
    try:
        healthy(8801)
        point_to(release)
        switched = True
        command("systemctl", "--user", "restart", "autotest-platform.service")
        healthy(8800)
        print(json.dumps({"release": version, "ready": True, "rollback": previous.name}))
    except Exception:
        if switched:
            point_to(previous)
            command("systemctl", "--user", "restart", "autotest-platform.service")
            healthy(8800)
        raise
    finally:
        subprocess.run(("systemctl", "--user", "stop", candidate), check=False, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    activate(args.version, args.sha256)
