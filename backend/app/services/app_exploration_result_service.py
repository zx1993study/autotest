from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.app_exploration_service import DISPATCH_LOCK


class AppExplorationResultService:
    """Attach exploration evidence to existing scenario runs, without replay."""

    def __init__(self, repository):
        self.repository = repository

    def finish(self, task):
        data = task['data']
        raw = data['payload']
        with DISPATCH_LOCK:
            saved = data.get('saved_resource')
            if saved:
                self._run(task, saved)
            if task['status'] == 'failed':
                rows, _ = self.repository.list('project_knowledge', page_size=10000,
                    data_filters={'exploration_task_id':task['id']})
                if not rows:
                    self.repository.create('project_knowledge', {
                        'name':'App 设备操作中断', 'project_id':raw['project_id'], 'status':'draft',
                        'data':{'domain':'APP','kind':'app_failure_lesson','verified':False,
                            'feature_id':raw['feature_id'],'device_id':raw['device']['id'],
                            'exploration_task_id':task['id'],'content':'设备操作或通信中断。结果可能未知，不应直接重试提交动作。',
                            'repair_strategy':'人工核实实际结果，重新观察当前界面；确认后才继续。'}})

    def _run(self, task, saved):
        data = task['data']
        raw, live = data['payload'], data['live']
        rows, _ = self.repository.list('app_scenario_runs', page_size=10000,
            data_filters={'agent_task_id':task['id']})
        record = next(iter(data.get('saved_records') or []), {})
        result = (record.get('data') or {})
        run_data = {**result, 'scenario_id':saved['id'], 'feature_id':raw['feature_id'],
            'device_id':raw['device']['id'],'device_name':raw['device']['name'],
            'agent_task_id':task['id'],'execution_record_id':record.get('id'),
            'input_snapshot':live['input_snapshot'], 'step_timeline':live['timeline'],
            'screenshots':live.get('screenshots',[]), 'source_type':'device_exploration',
            'error':data.get('error') or result.get('error') or ''}
        run = rows[0] if rows else self.repository.create('app_scenario_runs', {
            'name':'App 设备实操生成', 'project_id':raw['project_id'],
            'status':task['status'], 'data':run_data})
        scenario = self.repository.get('app_feature_scenarios',saved['id'])
        feature = self.repository.get('app_features',raw['feature_id'])
        service = AppFeatureTestingService(self.repository)
        if scenario:
            service._update_last_run(scenario,run)
        if feature:
            service._update_feature_last_run(feature,run)
