"""Campaign imports and write-through caching for existing domain services."""
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE.parent))

from flow_reorganization.inventory import collect as collect
from flow_reorganization.inventory import fingerprint as fingerprint
from flow_reorganization.inventory import save as save

class CampaignRepository:
    def __init__(self, repository):
        self.repository = repository
        self.cache = {}

    def __getattr__(self, name):
        return getattr(self.repository, name)

    def get(self, table, item_id):
        key = table, item_id
        if key not in self.cache:
            self.cache[key] = self.repository.get(table, item_id)
        return deepcopy(self.cache[key])

    def create(self, table, payload):
        row = self.repository.create(table, payload)
        self.cache[(table, row["id"])] = row
        return row

    def update(self, table, item_id, payload):
        row = self.repository.update(table, item_id, payload)
        self.cache[(table, item_id)] = row
        return row
