"""Persist bounded follow-up context and public activity milestones, not reasoning."""
from copy import deepcopy
from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError
from app.services.generation_candidate_service import safe_context, validate_candidate

TABLE = 'ai_generation_tasks'


class GenerationConversationService:
    def __init__(self, repository):
        self.repository = repository

    def prepare(self, domain, source, payload):
        parent_id = payload.get('parent_task_id')
        messages, previous, images = [], None, []
        if parent_id:
            parent = self.repository.get(TABLE, parent_id)
            data = (parent or {}).get('data') or {}
            if not parent or data.get('task_type') != 'business_generation' or data.get('domain') != domain or data.get('source_id') != source['id'] or parent.get('project_id') != source['project_id']:
                raise BusinessRuleError('对话记录不属于当前功能与项目')
            if parent['status'] in {'queued', 'running'}:
                raise BusinessRuleError('请等待当前生成结束，或中止后再继续对话')
            if data.get('agent_task_id'):
                agent = self.repository.get('agent_tasks', data['agent_task_id']) or {}
                if agent.get('status') in {'pending', 'running'}:
                    raise BusinessRuleError('请等待当前执行结束或中止，再继续对话')
            messages = deepcopy(data.get('conversation') or [])
            if not messages and (data.get('payload') or {}).get('prompt'):
                messages = [{'role':'user', 'content':data['payload']['prompt'], 'task_id':parent_id}]
            previous = (data.get('result') or {}).get('candidate')
            images = (data.get('payload') or {}).get('screenshots') or []
        if payload.get('previous_candidate'):
            if not parent_id:
                raise BusinessRuleError('编辑后的候选只能用于继续已有对话')
            previous = validate_candidate(domain, payload['previous_candidate'], source)
        if len(messages) >= 24 or sum(len(str(m.get('content') or '')) for m in messages) + len(payload['prompt']) > 80000:
            raise BusinessRuleError('本次对话已达到长度限制，请开始新对话')
        messages.append({'role':'user', 'content':safe_context(payload['prompt'])})
        images = (images + (payload.get('screenshots') or []))[-6:]
        return safe_context(messages), safe_context(previous), images

    def stage(self, task_id, code, label, status='running'):
        task = self.repository.get(TABLE, task_id)
        if not task or task['status'] != 'running':
            return
        data = deepcopy(task['data'])
        now = datetime.now(UTC).isoformat()
        stages = data.setdefault('stages', [])
        for stage in stages:
            if stage['status'] == 'running':
                stage.update(status='success' if status != 'failed' else 'failed', ended_at=now)
        stages.append({'code':code, 'label':label, 'status':status, 'started_at':now, **({'ended_at':now} if status != 'running' else {})})
        self.repository.update_if_status(TABLE, task_id, 'running', {'data':{**data, 'progress':label}})

    def complete(self, task_id, result):
        task = self.repository.get(TABLE, task_id)
        data = deepcopy((task or {}).get('data') or {})
        messages = data.setdefault('conversation', [])
        candidate = result.get('candidate') or {}
        steps = candidate.get('steps') or []
        parts = [f'已生成 {len(steps)} 条待执行操作步骤。' if steps else '正在确认可执行需求。']
        if result.get('questions'):
            parts.append('需要补充：\n' + '\n'.join(str(q) for q in result['questions']))
        if result.get('warnings'):
            parts.append('待确认事项：\n' + '\n'.join(str(w) for w in result['warnings']))
        if candidate and not steps:
            parts[0] = '已生成候选请求，等待审阅。'
        messages.append({'role':'assistant', 'content':safe_context('\n'.join(parts))[:16000], 'task_id':task_id})
        return data
