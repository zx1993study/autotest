"""Update installed protocol version while preserving node credentials and settings."""
import argparse
import json
import os
import re
import shutil
from pathlib import Path


def update(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid version')
    root = (Path(os.environ['LOCALAPPDATA']) / 'AutotestAgent').resolve(strict=True)
    path = root / 'config.json'
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not data.get('node_key') or not (data.get('agent_token') or data.get('token')):
        raise ValueError('Existing node identity is missing')
    backup = root / f'config.pre-{version}.json'
    if not backup.exists():
        shutil.copy2(path, backup)
    data.update(version=version, plugins=list(dict.fromkeys([*(data.get('plugins') or []), 'mobile', 'web'])))
    temporary = root / 'config.upgrade.json'
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
    print(f'Agent updated to {version}; node identity and connection settings preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    update(parser.parse_args().version)
