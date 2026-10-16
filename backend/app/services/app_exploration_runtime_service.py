from copy import deepcopy
from datetime import UTC, datetime

from web_automation.mobile import validate_screen

from app.core.exceptions import BusinessRuleError
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.agent_task_service import AgentTaskService
from app.services.app_exploration_service import AppExplorationService, patch_live, now
from app.services.app_exploration_control_service import ask
from app.services.generation_candidate_service import safe_context


class AppExplorationRuntimeService:
    def __init__(self,repository):
        self.repository = repository

    def owned(self,task_id,payload):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id,payload.node_key,payload.lease_token)
        AppExplorationService(self.repository).get(task_id)
        try:
            expiry = datetime.fromisoformat(task['data'].get('lease_expires_at') or '')
        except ValueError:
            raise BusinessRuleError('任务租约无效，禁止继续设备操作') from None
        if task['status'] != 'running' or expiry.replace(tzinfo=expiry.tzinfo or UTC) <= datetime.now(UTC):
            raise BusinessRuleError('任务租约已过期，禁止继续设备操作')
        return task

    def state(self,task_id,payload):
        task = self.owned(task_id,payload)
        live = task['data']['live']
        return {'phase':live['phase'],'revision':live['revision'],'cursor':live['cursor'],
                'bundle_id':task['data']['payload']['bundle_id'],
                'command':live.get('command') if live['phase'] == 'ready' else None,
                'steps':live['steps'],'input_info':live['input_info'],'input_snapshot':live['input_snapshot'],'timeline':live['timeline'],
                'screenshots':live.get('screenshots',[]),'outcome_unknown':live.get('outcome_unknown',False)}

    def connection(self, task_id, payload):
        from app.services.app_exploration_connection_service import AppExplorationConnectionService

        return AppExplorationConnectionService(self.repository).report(self.owned(task_id,payload),payload)

    def observe(self,task_id,payload):
        task = self.owned(task_id,payload)
        live = deepcopy(task['data']['live'])
        if payload.observation_id == live.get('observation_id'):
            return {'revision':live['revision'],'planning':False}
        bundle_id = task['data']['payload']['bundle_id']
        discovering = not bundle_id and live['phase'] == 'connecting'
        if live['phase'] != 'observing' and not discovering:
            return {'revision':live['revision'],'planning':False}
        screen = validate_screen(payload.screen,'com.apple.springboard' if discovering else bundle_id)
        if screen.get('sensitive'):
            live['manual_precondition'] = True
        # Sensitive screen images are never persisted or sent to the model.
        if payload.screenshot_base64 and not screen.get('sensitive'):
            shot = {'screenshot_base64':payload.screenshot_base64}
            AgentTaskService(self.repository)._store_agent_screenshot(shot)
            if shot.get('screenshot_error'):
                raise BusinessRuleError('设备截图保存失败')
            live['preview'] = shot
            live['screenshots'] = (live.get('screenshots',[]) + [{**shot,'step_order':live['cursor']}])[-61:]
        else:
            live['preview'] = None
        live.update(screen=screen,observation_id=payload.observation_id,session_reused=payload.session_reused,
                    revision=live['revision']+1,phase='planning',observed_at=now(),discovering_app=discovering)
        live['events'] = (live['events']+[{'label':'查找目标应用图标' if discovering else '采集目标应用界面','status':'success','time':now()}])[-100:]
        patch_live(self.repository,task,live)
        return {'revision':live['revision'],'planning':True}

    def action(self,task_id,payload):
        task = self.owned(task_id,payload)
        live = deepcopy(task['data']['live'])
        command = live.get('command') or {}
        if payload.nonce in {item.get('nonce') for item in live['timeline'] + live.get('bootstrap_timeline',[])}:
            return {'accepted':True,'execute':False}
        if command.get('nonce') != payload.nonce:
            raise BusinessRuleError('设备动作编号已变化')
        if payload.status == 'begin':
            if live['phase'] != 'ready':
                return {'accepted':False,'execute':False}
            live.update(phase='executing',action_started_at=now())
            patch_live(self.repository,task,live)
            return {'accepted':True,'execute':True}
        if live['phase'] not in {'executing','canceled'}:
            raise BusinessRuleError('动作没有获得执行授权')
        step = deepcopy(command['step'])
        item = {'index':live['cursor']+1,'name':step['name'],'action':step['action'],'status':payload.status,
                'nonce':payload.nonce,'duration_ms':payload.duration_ms,'error':safe_context(payload.error)}
        history = live.setdefault('bootstrap_timeline',[]) if command.get('app_bootstrap') else live['timeline']
        history.append(item)
        canceled = live['phase'] == 'canceled'
        if payload.status == 'success':
            for key,value in command['input_info'].items():
                # A parameter reused with a different value gets its own stable key.
                live['input_info'][key] = {'label':key,'type':'text','value':value,'required':True}
                live['input_snapshot'][key] = payload.input_value if payload.input_value is not None else value
            if not command.get('app_bootstrap'):
                live['steps'].append(step)
                live['cursor'] += 1
            else:
                live['bootstrap_opened'] = True
                live['events'] = (live['events']+[{'label':'已打开目标图标，读取真实应用标识','status':'success','time':now()}])[-100:]
            next_phase = 'connecting' if command.get('app_bootstrap') else 'observing'
            live['phase'] = 'paused' if live.get('pause_requested') else next_phase
        elif payload.status == 'stale':
            live['stale_count'] += 1
            if live['stale_count'] >= 3:
                ask(live,'界面连续变化，请确认手机当前界面后继续。')
            else:
                live['phase'] = 'connecting' if command.get('app_bootstrap') else 'observing'
        else:
            live['outcome_unknown'] = step['action'] in {'tap','input','swipe'}
            ask(live,'操作中断。请在手机检查是否已完成；不会自动重复本次操作。','paused')
            item['outcome_unknown'] = live['outcome_unknown']
        if canceled:
            live['phase'] = 'canceled'
        live['command'] = None
        patch_live(self.repository,task,live)
        return {'accepted':True,'execute':False}
