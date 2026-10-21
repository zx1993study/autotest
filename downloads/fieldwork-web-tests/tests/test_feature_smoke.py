import asyncio

import pytest
from conftest import load_catalog
from pages.list_page import execute

FEATURES = [feature for feature in load_catalog()["features"] if feature["status"] == "source_ready"]


@pytest.mark.parametrize("feature", FEATURES, ids=lambda feature: f"feature-{feature['feature_id']}")
def test_source_page_list(feature, request):
    if not request.config.getoption("--feature-smoke"):
        pytest.skip("Enable --feature-smoke to run page/list checks, not CRUD business verification")
    config = request.getfixturevalue("web_config")
    asyncio.run(execute(config, feature))
