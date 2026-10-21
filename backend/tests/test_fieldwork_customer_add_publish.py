import copy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

from app.services.web_feature_testing_service import WebFeatureTestingService
from fieldwork_customer_add_definition import (
    DIALOG,
    ERRORS,
    FEATURES,
    OUTCOMES,
    inputs,
    parameters,
)
from fieldwork_customer_add_publish import publish, validate_retry
from test_web_page_management_service import FakeResourceRepository
from web_automation.compiler import ExecutionPlanCompiler

EVIDENCE = {'commit': 'a' * 40, 'sha256': {'source': 'b' * 64}}
FACTS = {'manager_id': 1, 'manager_name': 'Test Manager', 'cooperation_options': ['正在合作', '终止合作']}


@pytest.fixture
def repo():
    result = FakeResourceRepository()
    result.rows = {}
    for fid, route in FEATURES.items():
        result.create('web_pages', {'id': fid, 'name': '新增终端客户', 'project_id': 10,
            'data': {'route': route, 'url': 'https://example.test' + route,
                     'auth_id': 10084, 'feature_type': 'add', 'page_group_id': 15190}})
    result.create('web_test_cases', {'id': 42, 'source_id': 200, 'project_id': 10, 'steps': [{'action': 'click'}]})
    return result


def test_dry_run_does_not_write(repo):
    before = copy.deepcopy(repo.rows)
    assert publish(repo, EVIDENCE, FACTS)['cases_per_feature'] == 5
    assert repo.rows == before


def test_publishes_both_routes_and_binds_each_outcome_without_touching_other_cases(repo):
    unrelated = copy.deepcopy(repo.get('web_test_cases', 42))
    result = publish(repo, EVIDENCE, FACTS, True)
    assert len(result['features']) == 2
    assert len(repo.rows['web_function_versions']) == 10
    assert repo.get('web_test_cases', 42) == unrelated
    for feature in result['features']:
        assert [c['outcome'] for c in feature['cases']] == list(OUTCOMES)
        assert repo.get('web_pages', feature['feature_id'])['data']['script_version'] == feature['cases'][0]['version_id']
        for item in feature['cases']:
            row = repo.get('web_test_cases', item['case_id'])
            assert row['data']['allow_invalid_inputs'] == (item['outcome'] != 'success')
            assert row['data']['script_version'] == item['version_id']
            assert len([s for s in row['steps'] if s['name'] == '点击新增']) == 1
            assert len([s for s in row['steps'] if s['name'] == '提交新增客户']) == 1
            assert all(s['require_unique'] for s in row['steps'])


def test_success_reuses_the_same_unique_name_in_fill_query_and_assertions(repo):
    result = publish(repo, EVIDENCE, FACTS, True)
    row = repo.get('web_test_cases', result['features'][0]['cases'][0]['case_id'])
    compiled = ExecutionPlanCompiler().compile_case(row, {})
    name = compiled.raw['data']['variables']['customer_name']
    assert name.startswith('青禾便利店_回归_') and '{{' not in name
    assert compiled.steps[3]['value'] == name
    assert sum(s.get('expected') == name for s in compiled.steps) == 2
    assert any(s['name'] == '打开本轮新增客户详情' and name in s['locator'] for s in compiled.steps)
    assert all('编辑' not in s['name'] and '删除' not in s['name'] for s in compiled.steps)
    assert compiled.raw['data']['variables']['manager_names'] == ['Test Manager']


def test_missing_inputs_assert_specific_errors_without_selecting_empty_options(repo):
    result = publish(repo, EVIDENCE, FACTS, True)
    for item in result['features'][0]['cases'][1:]:
        row = repo.get('web_test_cases', item['case_id'])
        key, message = ERRORS[item['outcome']]
        assert any(s.get('expected') == message for s in row['steps'])
        assert not any(s['action'] == 'multi_select' and s.get('value') == '{{' + key + '}}' for s in row['steps'])
        assert not any(s.get('expected') == '新增成功，等待审批' for s in row['steps'])
        assert row['steps'][-1]['name'] == '取消异常输入'


def test_repeat_publish_keeps_user_inputs_and_case_ids(repo):
    first = publish(repo, EVIDENCE, FACTS, True)
    row = repo.get('web_test_cases', first['features'][0]['cases'][0]['case_id'])
    row['data']['input_info']['remark'] = 'user edited'
    before = copy.deepcopy(repo.rows['web_test_cases'])
    second = publish(repo, EVIDENCE, FACTS, True)
    assert second['features'] == first['features']
    assert len(repo.rows['web_function_versions']) == 10
    assert repo.rows['web_test_cases'] == before


def test_foreign_route_or_existing_script_refused_before_any_write(repo):
    repo.get('web_pages', 11363)['data']['route'] = '/customer/direct'
    before = copy.deepcopy(repo.rows)
    with pytest.raises(ValueError, match='ownership'):
        publish(repo, EVIDENCE, FACTS, True)
    assert repo.rows == before
    repo.get('web_pages', 11363)['data']['route'] = FEATURES[11363]
    WebFeatureTestingService(repo).save_version(11355, {'name': 'User custom script', 'steps': [
        {'action': 'assert', 'locator_type': 'css', 'locator': 'body', 'expected': 'User text'}]})
    before = copy.deepcopy(repo.rows)
    with pytest.raises(ValueError, match='user script'):
        publish(repo, EVIDENCE, FACTS, True)
    assert repo.rows == before


def test_export_defaults_are_templates_and_required_fields_match_source(repo):
    assert {p['key'] for p in parameters(FACTS) if p['required']} == {
        'customer_name', 'cooperation_status', 'manager_names'}
    result = publish(repo, EVIDENCE, FACTS, True)
    for item in result['features'][0]['cases']:
        version = repo.get('web_function_versions', item['version_id'])
        assert version['data']['candidate']['input_info'] == inputs(item['outcome'], FACTS)


def test_nested_dialogs_and_filterable_manager_use_precise_interactive_locators(repo):
    result = publish(repo, EVIDENCE, FACTS, True)
    row = repo.get('web_test_cases', result['features'][0]['cases'][0]['case_id'])
    title = next(s for s in row['steps'] if s['name'] == '验证新增弹窗')
    submit = next(s for s in row['steps'] if s['name'] == '提交新增客户')
    manager = next(s for s in row['steps'] if s.get('value') == '{{manager_names}}')
    assert title['locator'] == DIALOG + ' > .el-dialog__header > .el-dialog__title'
    assert ' > .el-dialog__footer > .dialog-footer > ' in submit['locator']
    assert manager['locator'].endswith('input.el-select__input')
    assert manager['action'] == 'multi_select' and manager['require_unique'] is True


@pytest.mark.parametrize('completed,negative,allow_fresh,name,allowed', [
    (0, False, False, 'fixed-name', True),
    (1, False, False, 'fixed-name', True),
    (2, False, False, 'fixed-name', False),
    (3, False, False, 'fixed-name', False),
    (4, True, False, 'fixed-name', True),
    (2, False, True, 'fixed-name', False),
    (4, False, True, 'test_{{timestamp_ms}}_{{random_digits:6}}', True),
])
def test_write_retry_requires_pre_submit_failure_or_explicit_fresh_record(
        completed, negative, allow_fresh, name, allowed):
    platform = Mock()
    platform.get.return_value = {'data': {'payload': {'cases': [{'id': 74,
        'steps': [{'name': '点击新增'}, {'name': '填写参数'}, {'name': '提交新增客户'}],
        'data': {'input_info': {'customer_name': name}, 'allow_invalid_inputs': negative}}]}}}
    old = {'agent_task_id': 1, 'records': [{'case_id': 74, 'step_count': completed,
                                         'status': 'success' if negative else 'failed'}]}
    if allowed:
        validate_retry(platform, old, allow_fresh)
    else:
        with pytest.raises(ValueError, match='may have submitted'):
            validate_retry(platform, old, allow_fresh)
