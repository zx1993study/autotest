import asyncio

from web_automation.manual import manual_input_locator
from web_automation.outcomes import outcome_metadata  # noqa: F401 - compatibility for existing callers.

from agent_app.runtime.task_cancelled import TaskCancelled


async def wait_manual_input(page, step, context, window, index, case_id=None):
    locator = await manual_input_locator(page, step)
    if locator is None:
        return
    if not context:
        raise RuntimeError('人工输入需要本地有头 Agent')
    _, api, task_id, lease = context
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
