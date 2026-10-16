import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
config = json.loads(Path('D:/AutotestPlatform/config.json').read_text(encoding='utf-8-sig'))
os.environ['DATABASE_URL'] = config['database_url']
os.environ['AUTO_CREATE_SCHEMA'] = 'false'
sys.path.insert(0, str(ROOT / 'backend'))
from app.db import init_db

timings = {}


def measure(name, function):
    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            timings[name] = round((time.perf_counter() - start) * 1000)
    return wrapped


for name in ('ensure_database_exists', 'ensure_test_case_strategy_columns',
             'ensure_execution_plan_requirement_columns', 'ensure_resource_record_indexes',
             'ensure_schema_compatibility', 'seed_default_data'):
    setattr(init_db, name, measure(name, getattr(init_db, name)))
init_db.Base.metadata.create_all = measure('create_all', init_db.Base.metadata.create_all)
for cls, name in ((init_db.AuthService, 'ensure_default_admin'),
                  (init_db.DictionarySeedService, 'seed_playwright_defaults'),
                  (init_db.AiPromptSeedService, 'seed_defaults'),
                  (init_db.TestCaseMigrationService, 'migrate_legacy_test_cases'),
                  (init_db.KnowledgeSeedService, 'seed_defaults')):
    setattr(cls, name, measure(cls.__name__, getattr(cls, name)))
start = time.perf_counter()
ready = init_db.try_init_db()
print(json.dumps({'ready': ready, 'total_ms': round((time.perf_counter() - start) * 1000), 'phases_ms': timings}))
