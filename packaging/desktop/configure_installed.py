"""Migrate local connection settings without changing node credentials or data."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from client_config import data_root, platform_url, read_config, save_config


def configure(address):
    platform_url({"server_url": address})
    agent_root = Path(os.environ["LOCALAPPDATA"]) / "AutotestAgent"
    agent_file = agent_root / "config.json"
    backup = agent_root / "config.pre-remote-v1.json"
    shutil.copy2(agent_file, backup)
    agent = json.loads(agent_file.read_text(encoding="utf-8-sig"))
    agent.update(server_url=address.rstrip("/"), plugins=["mobile"], version="0.3.0")
    temp = agent_file.with_suffix(".new")
    temp.write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(agent_file)
    client_file = data_root() / "client.json"
    if client_file.exists():
        shutil.copy2(client_file, client_file.with_suffix(".pre-remote-v1.json"))
    client = read_config(client_file)
    client.update(server_url=address.rstrip("/"), agent_config=str(agent_file), auto_start_agent=True)
    save_config(client_file, client)
    print("Client and Agent URLs updated; node token and artifacts directory preserved")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    configure(parser.parse_args().url)
