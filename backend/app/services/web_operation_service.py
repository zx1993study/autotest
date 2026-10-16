from secrets import token_urlsafe

from app.core.exceptions import BusinessRuleError
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.agent_task_service import AgentTaskService


class WebOperationService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _require_web(task):
        data = task.get('data') or {}
        if data.get('task_type') != 'web_replay' and not (data.get('task_type') == 'case_execution' and data.get('payload', {}).get('case_type') == 'WEB'):
            raise BusinessRuleError('任务不是 Web 操作任务')
        return data

    def state(self, task_id, payload):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id, payload.node_key, payload.lease_token)
        data = self._require_web(task)
        if task['status'] != 'running':
            raise BusinessRuleError('任务不在执行中')
        waiting = data.get('waiting_input') or {}
        if payload.phase == 'waiting_input':
            raw = data['payload']
            candidate = raw.get('candidate') if data['task_type'] == 'web_replay' else next((c for c in raw.get('cases', []) if c['id'] == payload.case_id), None)
            steps = (candidate or {}).get('steps') or []
            if not 1 <= payload.step <= len(steps) or steps[payload.step - 1].get('action') != 'manual':
                raise BusinessRuleError('人工输入步骤不属于当前任务')
            waiting = {'nonce': token_urlsafe(18), 'step': payload.step, 'case_id': payload.case_id, 'label': str(steps[payload.step - 1].get('name') or '人工输入')[:160], 'confirmed': False}
            self.repository.patch_running_agent_task(task_id, payload.node_key, {'waiting_input': waiting})
        return {'waiting_input': waiting, 'cancel_requested': bool(data.get('cancel_requested')), 'recording_stop': bool(data.get('recording_stop'))}

    def control(self, task_id, payload):
        task = AgentTaskService(self.repository).get_task(task_id)
        data = self._require_web(task)
        if task['status'] not in {'pending', 'running'}:
            raise BusinessRuleError('任务已结束')
        if payload.action == 'stop':
            if not data.get('payload', {}).get('recording'):
                raise BusinessRuleError('任务不是操作录制')
            patch = {'recording_stop': True}
        elif payload.action == 'cancel':
            if task['status'] == 'pending':
                return self.repository.update_if_status('agent_tasks', task_id, 'pending', {'status': 'canceled'})
            patch = {'cancel_requested': True}
        else:
            waiting = data.get('waiting_input') or {}
            if not waiting or payload.nonce != waiting.get('nonce') or waiting.get('confirmed'):
                raise BusinessRuleError('等待步骤已变化，请刷新后继续')
            patch = {'waiting_input': {**waiting, 'confirmed': True}}
        expected = {'waiting_input': waiting} if payload.action == 'continue' else None
        if not self.repository.patch_running_agent_task(task_id, data.get('claimed_by'), patch, expected):
            raise BusinessRuleError('任务已结束')
        return {'accepted': True}
