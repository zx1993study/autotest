"""App feature-owned live device tasks; no new physical database tables."""
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.agent import AgentTaskCreateRequest
from app.services.app_agent_execution_service import AppAgentExecutionService
from app.services.ai_model_service import AiModelResourceService
from app.services.agent_task_service import AgentTaskService
from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.generation_candidate_service import candidate_hash, safe_context

DISPATCH_LOCK = RLock()


def now():
    return datetime.now(UTC).isoformat()


def patch_live(repository, task, live):
    previous = deepcopy(task['data']['live'])
    updated = repository.patch_running_agent_task(task['id'], task['data'].get('claimed_by'),
        {'live':live}, {'live':previous})
    if not updated:
        raise BusinessRuleError('任务状态已变化，请刷新后重试')
    return updated


class AppExplorationService:
    def __init__(self, repository):
        self.repository = repository

    def get(self, task_id, feature_id=None):
        task = self.repository.get('agent_tasks', task_id)
        data = (task or {}).get('data') or {}
        if not task or data.get('task_type') != 'app_exploration' or (feature_id and data['payload']['feature_id'] != feature_id):
            raise ResourceNotFoundError('当前功能的设备对话不存在')
        return task

    def public(self, task):
        data = task['data']
        live = deepcopy(data['live'])
        live.pop('screen',None)
        live.pop('observation_id',None)
        live.pop('request_ids',None)
        if task['status'] in {'failed','canceled'} and live.get('phase') == 'executing':
            live['outcome_unknown'] = True
        if live.get('command'):
            live['command'].pop('input_info',None)
        payload = data['payload']
        return {'id':task['id'], 'status':task['status'], 'feature_id':payload['feature_id'],
                'device_id':payload['device']['id'], 'device_name':payload['device']['name'],
                'entry_id':payload['entry_id'], 'bundle_id':payload['bundle_id'], 'live':live,
                'result':data.get('result'), 'error':data.get('error'), 'saved_resource':data.get('saved_resource')}

    def start(self, feature_id, payload):
        if not payload.approve_effects:
            raise BusinessRuleError('请确认允许在所选设备执行本次操作')
        feature = self.repository.get('app_features',feature_id)
        if not feature or not feature.get('project_id'):
            raise BusinessRuleError('功能必须关联项目')
        device = self.repository.get('app_devices',payload.device_id)
        entry = self.repository.get('app_entries',payload.entry_id)
        if not device or device.get('status') != 'active':
            raise BusinessRuleError('请选择设备池中的启用设备')
        if not entry or entry.get('project_id') != feature['project_id'] or entry.get('status') != 'active':
            raise BusinessRuleError('应用入口必须属于当前项目且已启用')
        dd, ed = device.get('data') or {}, entry.get('data') or {}
        if str(dd.get('platform') or 'iOS').lower() not in {'ios','ipados'}:
            raise BusinessRuleError('设备实操生成目前支持 iOS/WDA')
        bundle_id = str(ed.get('bundle_id') or ed.get('bundleId') or '').strip()
        node_key = AppAgentExecutionService(self.repository)._node(dd.get('node_key'))
        nodes,_ = self.repository.list('agent_nodes',page_size=10000)
        node = next(n for n in nodes if n['data']['node_key'] == node_key)
        if 'app_exploration' not in node['data'].get('capabilities',[]):
            raise BusinessRuleError('请更新本地 Agent，以启用设备实操生成')
        if 'app_connection' not in node['data'].get('capabilities',[]):
            raise BusinessRuleError('请更新本地 Agent，以启用设备连接与应用自动识别')
        model = AiModelResourceService(self.repository).active_model(payload.model_id)
        if not model.get('data',{}).get('supports_vision'):
            raise BusinessRuleError('设备实操需要支持视觉的模型')
        with DISPATCH_LOCK:
            rows,_ = self.repository.list('agent_tasks',page_size=10000)
            prior = next((r for r in rows if r.get('data',{}).get('payload',{}).get('request_id') == payload.request_id),None)
            if prior:
                if prior['data']['payload'].get('feature_id') != feature_id or prior['data']['payload'].get('device',{}).get('id') != device['id']:
                    raise BusinessRuleError('请求编号已用于其他设备任务')
                return self.public(prior)
            self.require_available(device['id'],rows)
            prompt = safe_context(payload.prompt)
            live = {'phase':'connecting','revision':0,'steps':[],'input_info':{},'input_snapshot':{},'timeline':[],
                    'conversation':[{'role':'user','content':prompt}],'message':prompt,'events':[],
                    'request_ids':[payload.request_id], 'cursor':0,'model_http_calls':0,'stale_count':0}
            task = AgentTaskService(self.repository).create(AgentTaskCreateRequest(task_type='app_exploration',node_key=node_key,
                payload={'feature_id':feature_id,'project_id':feature['project_id'],'device':device,'entry_id':entry['id'],
                         'bundle_id':bundle_id,'entry_name':entry['name'],'resolve_connection':True,
                         'model_id':model['id'],'request_id':payload.request_id,
                         'start_from_current_screen':payload.start_from_current_screen,'record_video':payload.record_video}),
                initial_data={'live':live})
        return self.public(task)

    @staticmethod
    def require_available(device_id, rows):
        for task in rows:
            if task.get('status') not in {'pending','running'}:
                continue
            raw = task.get('data',{}).get('payload',{})
            bound = raw.get('device') or raw.get('context',{}).get('device') or raw.get('execution',{}).get('config',{}).get('device') or {}
            if bound.get('id') == device_id:
                raise BusinessRuleError('设备已有运行或排队任务，请先停止或完成该任务')

    def active(self, feature_id):
        rows,_ = self.repository.list('agent_tasks',page_size=10000)
        task = next((r for r in rows if r.get('data',{}).get('task_type') == 'app_exploration'
                     and r.get('data',{}).get('payload',{}).get('feature_id') == feature_id
                     and r['status'] in {'pending','running'}),None)
        return self.public(task) if task else None

    def accept(self, task_id, feature_id, payload):
        with DISPATCH_LOCK:
            return self._accept(task_id,feature_id,payload)

    def _accept(self, task_id, feature_id, payload):
        task = self.get(task_id,feature_id)
        if task['data'].get('saved_resource'):
            return task['data']['saved_resource']
        live = deepcopy(task['data']['live'])
        if not payload.name.strip():
            raise BusinessRuleError('场景名称不能为空')
        if task['status'] != 'running' or live['phase'] not in {'waiting_next','saving'} or not live['steps']:
            raise BusinessRuleError('请等待本轮操作完成后保存；失败或结果未知不能保存为已验证场景')
        if live['phase'] != 'saving':
            live['phase'] = 'saving'
            task = patch_live(self.repository,task,live)
        raw = task['data']['payload']
        candidate = {'steps':live['steps'],'input_info':live['input_info']}
        rows,_ = self.repository.list('app_feature_scenarios',page_size=10000,data_filters={'feature_id':feature_id})
        saved = next((row for row in rows if row['data'].get('generation_meta',{}).get('task_id') == task_id),None)
        try:
            saved = saved or AppFeatureTestingService(self.repository).create_scenario(feature_id,{
            'name':payload.name.strip(),'device_id':raw['device']['id'],'entry_id':raw['entry_id'],
            'operation_steps':live['steps'],'input_info':live['input_info'],'assertions':[],
            'source_type':'natural_language','record_video':raw['record_video'],
            'start_from_current_screen':raw['start_from_current_screen'],
            'generation_notes':'包含人工操作前置条件，回放前需在设备上完成相应敏感输入。' if live.get('manual_precondition') else None,
            'generation_meta':{'task_id':task_id,'execution_hash':candidate_hash(candidate),
                               'verification_scope':'executed_steps_and_input_snapshot', 'input_snapshot':live['input_snapshot'],
                               'evidence':live.get('screenshots',[]),'timeline':live['timeline'],
                               'precondition':{'bundle_id':raw['bundle_id'],'start_from_current_screen':raw['start_from_current_screen'],
                                               'manual_input_required':live.get('manual_precondition',False)}}})
        except Exception:
            current = self.get(task_id)
            restored = deepcopy(current['data']['live'])
            restored['phase'] = 'waiting_next'
            patch_live(self.repository,current,restored)
            raise
        task = self.get(task_id)
        live = deepcopy(task['data']['live'])
        live['phase'] = 'finishing'
        resource = {'id':saved['id'],'domain':'APP'}
        updated = self.repository.patch_running_agent_task(task_id,task['data']['claimed_by'],{'live':live,'saved_resource':resource},{'live':task['data']['live']})
        if not updated:
            raise BusinessRuleError('保存状态已变化，请刷新重试；已生成场景不会重复创建')
        return resource
