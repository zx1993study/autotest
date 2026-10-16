from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import AgentTaskCreateRequest
from app.services.agent_task_service import AgentTaskService
from app.services.generation_candidate_service import validate_candidate
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_target_url_service import resolve_web_target_url


class WebRecordingService:
    def __init__(self, repository):
        self.repository = repository
        self.workspace = WebFeatureTestingService(repository)

    def start(self, feature_id, payload):
        feature = self.workspace.feature(feature_id)
        self.workspace._not_running(feature)
        if not payload.approve_side_effects:
            raise BusinessRuleError('请确认录制时由你实际操作业务页面')
        nodes, _ = self.repository.list('agent_nodes', page_size=1000)
        node = next((n for n in nodes if (n.get('data') or {}).get('node_key') == payload.node_key), {})
        data = node.get('data') or {}
        try:
            fresh = (datetime.now(UTC) - datetime.fromisoformat(data.get('last_seen_at') or '')).total_seconds() < 90
        except (ValueError, TypeError):
            fresh = False
        if not fresh or node.get('status') != 'active' or data.get('agent_status') not in {'online', 'busy'} or 'web_recording' not in data.get('capabilities', []):
            raise BusinessRuleError('请选择已升级支持操作录制的在线 Agent')
        task = AgentTaskService(self.repository).create(AgentTaskCreateRequest(task_type='web_replay', node_key=payload.node_key, payload={
            'recording': True, 'source_id': feature_id, 'project_id': feature['project_id'], 'target_url': resolve_web_target_url(self.repository, feature), 'name': feature['name'],
        }))
        return {'agent_task_id': task['id']}

    def accept(self, feature_id, payload):
        feature = self.workspace.feature(feature_id)
        task = AgentTaskService(self.repository).get_task(payload.task_id)
        data = task.get('data') or {}
        raw = data.get('payload') or {}
        if not raw.get('recording') or raw.get('source_id') != feature_id or raw.get('project_id') != feature['project_id'] or task['status'] != 'success':
            raise BusinessRuleError('录制结果不属于当前功能或尚未完成')
        if data.get('saved_version'):
            return {'id': data['saved_version']}
        records = (data.get('result') or {}).get('records') or []
        result = (records[0].get('data') or {}) if records else {}
        candidate = validate_candidate('WEB', payload.candidate, feature)
        screenshots = [s['screenshot_file'] for s in result.get('screenshots', []) if s.get('screenshot_file')]
        version = self.workspace.save_version(feature_id, candidate, parameters=self.workspace.parameters_from_candidate(candidate), screenshots=screenshots)
        self.workspace.save_case(feature_id, {'name': candidate['name'], 'input_info': candidate.get('input_info') or {}, 'script_version': version['id']})
        self.repository.update('agent_tasks', task['id'], {'data': {**data, 'saved_version': version['id']}})
        return version
