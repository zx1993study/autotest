import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.agent_task_service import AgentTaskService
from web_automation.engines.pipeline import ActionStrategyPipeline, AiBudget
from web_automation.engines.playwright import PlaywrightEngine
from web_automation.outcomes import outcome_metadata, verification_error


def test_skipped_assertion_and_precondition_cannot_prove_completion():
    assert verification_error([{'action': 'assert', 'expected': 'Saved', 'skip': True}])
    assert verification_error([{'action': 'assert', 'expected': 'Ready'}, {'action': 'click'}])
    assert verification_error([{'action': 'assert', 'expected': '  '}])
    steps = [{'action': 'click'}, {'action': 'assert', 'expected': 'Saved'}]
    assert outcome_metadata(steps, 1, 'success')['business_result'] != 'passed'
    assert outcome_metadata(steps, 2, 'success')['business_result'] == 'passed'


def test_explicit_cleanup_does_not_replace_business_assertion():
    assert verification_error([{'action': 'click'}, {'action': 'assert', 'expected': 'Rejected'},
                               {'action': 'click', 'cleanup': True}]) is None
    assert verification_error([{'action': 'assert', 'expected': 0}]) is None


def test_native_select_rejects_duplicate_labels_and_accepts_unique_id():
    locator = Mock(wait_for=AsyncMock(), select_option=AsyncMock(), click=AsyncMock(),
                   evaluate=AsyncMock(return_value=[{'label': 'Same name', 'value': 'user-1'},
                                                    {'label': 'Same name', 'value': 'user-2'}]))
    engine = PlaywrightEngine(Mock())
    with pytest.raises(ValueError, match='ambiguous'):
        asyncio.run(engine._select(locator, 'Same name', multi=False))
    locator.select_option.assert_not_called()
    asyncio.run(engine._select(locator, 'user-2', multi=False))
    locator.select_option.assert_awaited_once_with(value='user-2')
    with pytest.raises(ValueError, match='Unsupported'):
        asyncio.run(engine.execute_selector({'action': 'execute_python'}, '#cached'))
    locator.click.assert_not_called()


def test_hybrid_assertion_cannot_be_healed_or_satisfied_by_cached_locator():
    pipeline = ActionStrategyPipeline(engine='hybrid', budget=AiBudget(3), target_url='https://example.test',
                                      max_healing_time_ms=100, disable_ai_after_429=True)
    static = AsyncMock(side_effect=AssertionError('Not saved'))
    cache, ai = AsyncMock(), AsyncMock()
    with pytest.raises(AssertionError, match='Not saved'):
        asyncio.run(pipeline.execute({'action': 'assert', 'ai_cache': {'selector': '#other'}},
                                    static_action=static, cached_action=cache, ai_action=ai))
    cache.assert_not_called()
    ai.assert_not_called()


def test_text_assertion_waits_for_async_result_and_preserves_actual_value():
    locator = Mock(wait_for=AsyncMock(), inner_text=AsyncMock(side_effect=['Saving', 'Saved']))
    engine = PlaywrightEngine(Mock(), default_timeout=500)
    engine.locator = Mock(return_value=locator)
    asyncio.run(engine.execute({'action': 'assert', 'locator': '#result', 'expected': 'Saved'}))
    assert engine.last_assertion == {'locator': '#result', 'expected': 'Saved', 'actual': 'Saved', 'passed': True}


def test_empty_select_and_unknown_action_never_click():
    locator = Mock(wait_for=AsyncMock(), click=AsyncMock())
    engine = PlaywrightEngine(Mock())
    engine.locator = Mock(return_value=locator)
    for step in ({'action': 'select', 'value': ''}, {'action': 'execute_python'}):
        with pytest.raises(ValueError):
            asyncio.run(engine.execute(step))
    locator.click.assert_not_called()


def test_input_limit_assertion_measures_actual_value_not_label():
    locator = Mock(wait_for=AsyncMock(), scroll_into_view_if_needed=AsyncMock(),
                   input_value=AsyncMock(return_value='A' * 2000))
    engine = PlaywrightEngine(Mock(), default_timeout=0)
    engine.locator = Mock(return_value=locator)
    asyncio.run(engine.execute({'action': 'assert', 'locator': '#notes',
                                'assertion_type': 'input_length', 'expected': 2000}))
    assert engine.last_assertion['actual'] == 2000
    locator.input_value.return_value += 'X'
    with pytest.raises(AssertionError, match='actual: 2001'):
        asyncio.run(engine.execute({'action': 'assert', 'locator': '#notes',
                                    'assertion_type': 'input_length', 'expected': 2000}))


def test_layout_assertion_preserves_overflow_measurements_and_fails():
    measurements = {'clientWidth': 600, 'scrollWidth': 60000, 'contained': False}
    locator = Mock(wait_for=AsyncMock(), scroll_into_view_if_needed=AsyncMock(),
                   evaluate=AsyncMock(return_value=measurements))
    engine = PlaywrightEngine(Mock(), default_timeout=0)
    engine.locator = Mock(return_value=locator)
    with pytest.raises(AssertionError, match='within_container'):
        asyncio.run(engine.execute({'action': 'assert', 'locator': '.description',
                                    'assertion_type': 'within_container', 'expected': 'contained'}))
    assert engine.last_assertion['actual'] == measurements
    assert engine.last_assertion['passed'] is False
    measurements.update(scrollWidth=600, contained=True)
    asyncio.run(engine.execute({'action': 'assert', 'locator': '.description',
                                'assertion_type': 'within_container', 'expected': 'contained'}))
    assert engine.last_assertion['passed'] is True


def test_screenshot_masks_include_passwords_manual_inputs_and_secret_output():
    page = Mock()
    engine = PlaywrightEngine(page)
    engine.locator = Mock(side_effect=lambda step: step['locator'])
    masks = engine.screenshot_masks([
        {'locator': '#password', 'sensitive': True},
        {'locator': '#captcha', 'action': 'manual'},
        {'locator': '.mcp-token', 'mask_in_screenshots': True},
        {'locator': '#public'}])
    assert len(masks) == 4
    assert masks[1:] == ['#password', '#captcha', '.mcp-token']
    assert 'input[type="password"]' in page.locator.call_args.args[0]


def test_old_agent_operation_success_is_rejected_and_counts_are_recalculated():
    task = {'data': {'task_type': 'case_execution', 'payload': {'case_type': 'WEB', 'cases': [{'id': 1}]}}}
    result = {'success_count': 1, 'records': [{'status': 'success', 'data': {'case_id': 1}}]}
    assert AgentTaskService(Mock())._validate_web_completion(task, result)
    assert result['success_count'] == 0
    assert result['failed_count'] == 1
    assert result['records'][0]['status'] == 'failed'


def test_missing_agent_record_cannot_report_whole_task_success():
    task = {'data': {'task_type': 'case_execution', 'payload': {'case_type': 'WEB', 'cases': [{'id': 1}]}}}
    assert AgentTaskService(Mock())._validate_web_completion(task, {'records': []})
