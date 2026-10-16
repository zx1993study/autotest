"""Install only the Autotest location into the existing HTTPS virtual host."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import shutil
import subprocess
from pathlib import Path


def configure(backup):
    configuration = Path("/usr/local/nginx/nginx.conf")
    template = Path(__file__).with_name("nginx-location.conf").read_text(encoding="utf-8")
    subprocess.run(["sudo", "-n", "/usr/bin/nginx", "-t"], check=True)
    with configuration.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        old = handle.read()
        if "location ^~ /autotest/" in old:
            if template.strip() not in old:
                raise ValueError("An existing Autotest location needs manual review")
            return
        marker = "        location = /realreview {"
        if old.count(marker) != 1 or "server_name  dev-cn-01.yios.cn;" not in old:
            raise ValueError("Expected HTTPS insertion point not found")
        updated = old.replace(marker, template + "\n" + marker, 1)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(configuration, backup)
        handle.seek(0)
        handle.write(updated)
        handle.truncate()
        handle.flush()
        try:
            subprocess.run(["sudo", "-n", "/usr/bin/nginx", "-t"], check=True)
            subprocess.run(["sudo", "-n", "/usr/bin/systemctl", "reload", "nginx"], check=True)
        except subprocess.CalledProcessError:
            if hashlib.sha256(configuration.read_bytes()).hexdigest() == hashlib.sha256(updated.encode()).hexdigest():
                handle.seek(0)
                handle.write(old)
                handle.truncate()
                handle.flush()
            raise
    print("Autotest HTTPS location installed; other virtual hosts unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    configure(parser.parse_args().backup)
