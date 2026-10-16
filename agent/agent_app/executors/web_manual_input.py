import asyncio

from web_automation.engines.playwright import PlaywrightEngine

from agent_app.runtime.task_cancelled import TaskCancelled


async def wait_manual_input(page, step, context, window, index, case_id=None):
    if not context:
        raise RuntimeError('人工输入需要本地有头 Agent')
    _, api, task_id, lease = context
    locator = PlaywrightEngine(page)._strict_locator(step)
    await locator.wait_for(state='visible', timeout=10000)
    if await locator.count() != 1:
        raise ValueError('人工输入定位不唯一')
    await window.set_phase('waiting_input', activate=True)
    await asyncio.to_thread(api.web_state, task_id, lease, {'phase': 'waiting_input', 'step': index, 'case_id': case_id})
    while True:
        if page.is_closed():
            raise TaskCancelled('浏览器已关闭')
        state = await asyncio.to_thread(api.web_state, task_id, lease)
        if state.get('cancel_requested'):
            raise TaskCancelled('用户已中止操作')
        if (state.get('waiting_input') or {}).get('confirmed'):
            # Read locally for presence only. Never transmit or retain the field value.
            if not await locator.input_value():
                raise ValueError('人工输入字段仍为空，请填写后重新执行')
            await window.set_phase('running')
            return
        await asyncio.sleep(1)


def outcome_metadata(steps, completed, status):
    assertions = [i for i, s in enumerate(steps, 1) if s.get('action') == 'assert']
    business = 'not_configured' if not assertions else 'passed' if status == 'success' else 'failed' if completed + 1 in assertions else 'not_run'
    return {'operation_result': 'completed' if status == 'success' else status, 'business_result': business,
            'assertion_count': len(assertions), 'result_label': '操作完成，业务结果未验证' if status == 'success' and not assertions else '操作及业务验证通过' if status == 'success' else '操作未完成'}
