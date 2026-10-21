import asyncio
import json
from pathlib import Path

import pytest
from conftest import load_catalog
from pages.list_page import execute

CATALOG = load_catalog()
FEATURES = {feature["feature_id"]: feature for feature in CATALOG["features"]}


@pytest.mark.parametrize("case", CATALOG["cases"], ids=lambda case: f"existing-{case['case_id']}")
def test_existing_web_case(case, request):
    if case["status"] != "source_ready":
        pytest.skip(case["reason"])
    inputs = json.loads(Path(request.config.getoption("--inputs-file")).read_text(encoding="utf-8-sig"))
    config = request.getfixturevalue("web_config")
    asyncio.run(execute(config, FEATURES[case["feature_id"]], case, inputs.get(str(case["case_id"]), {})))
