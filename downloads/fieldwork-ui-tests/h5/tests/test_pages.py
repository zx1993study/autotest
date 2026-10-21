import os

import pytest
from conftest import load_catalog
from pages.source_page import SourcePage


@pytest.mark.parametrize("case", load_catalog(), ids=lambda case: case["id"])
def test_source_case(case, guarded_page):
    page, params, guard = guarded_page
    source = SourcePage(page, os.environ["FW_H5_BASE_URL"])
    source.open(case["route"], params)
    for operation in case["operations"]:
        source.execute(operation)
    guard.settle(page)
    source.assert_route(case["route"])
