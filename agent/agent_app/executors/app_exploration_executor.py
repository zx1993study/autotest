import time
import uuid
from copy import deepcopy

from web_automation.dynamic_values import DynamicValueContext
from agent_app.executors.mobile_observation import capture, ObservationVideo
from agent_app.executors.wda_actions import WdaActions
from agent_app.executors.wda_sessions import WdaSessionPool
from agent_app.runtime.stop_request import requested
from agent_app.executors.app_connection import resolve_device, foreground_identity, AppConnectionError


class AppTaskStopped(Exception):
    def __init__(self, canceled):
        self.canceled = canceled


class LocalAppExplorationExecutor:
    def __init__(self,config,api,pool=None,sleep=time.sleep):
        self.config,self.api = config,api
        self.pool = pool or WdaSessionPool(config.artifacts_dir)
        self.sleep = sleep
        self.dynamic = DynamicValueContext()
        self.inflight = False

    def exchange(self,task_id,lease,operation,payload=None):
        return self.api.app_exchange(task_id,lease,operation,payload or {})

    def execute(self,task_id,lease,payload):
        payload = deepcopy(payload)
        self.dynamic = DynamicValueContext()
        self.inflight = False
        state = {}
        error,canceled = '',False
        recording = ObservationVideo(self.config.artifacts_dir/'videos'/f'{uuid.uuid4().hex}.mp4',payload.get('record_video',True))
        try:
            if payload.get('resolve_connection'):
                self.prepare_connection(task_id,lease,payload)
            current_screen = True if payload.get('resolve_connection') else payload.get('start_from_current_screen',False)
            with self.pool.connect(payload['device'],payload['bundle_id'],current_screen) as (session,reused):
                actions = WdaActions(session)
                start_pending = bool(payload.get('resolve_connection'))
                while True:
                    state = self.exchange(task_id,lease,'state')
                    if requested(self.config) or state['phase'] == 'canceled':
                        canceled = True
                        break
                    if state['phase'] == 'finishing':
                        break
                    if state.get('bundle_id') and payload['bundle_id'] != state['bundle_id']:
                        payload['bundle_id'] = state['bundle_id']
                        self.pool.bind(payload['device'],payload['bundle_id'],session)
                    if state['phase'] == 'connecting' and not payload['bundle_id']:
                        self.discover(task_id,lease,session,reused)
                    elif state['phase'] == 'observing':
                        if start_pending:
                            if not payload.get('start_from_current_screen') and session.app_current().get('bundleId') != payload['bundle_id']:
                                self.inflight = True
                                session.app_launch(payload['bundle_id'])
                                self.inflight = False
                            start_pending = False
                        screen,encoded,frame = capture(session,payload['bundle_id'])
                        recording.append(frame)
                        self.exchange(task_id,lease,'observation',{'observation_id':uuid.uuid4().hex,
                            'screen':screen,'screenshot_base64':encoded,'session_reused':reused})
                    elif state['phase'] == 'ready':
                        self.action(task_id,lease,payload,session,actions,state['command'])
                    self.sleep(1)
        except AppTaskStopped as exc:
            canceled = exc.canceled
        except AppConnectionError as exc:
            error = str(exc)
        except Exception:
            # Network/SDK failures stop the task. No action is reissued after an uncertain acknowledgement.
            error = '设备连接或任务通信中断；不会自动重复已发送的操作，请检查手机当前状态。'
        result = {'case_type':'APP','device_id':payload['device']['id'],'feature_id':payload['feature_id'],
                  'steps':state.get('steps',[]),'input_snapshot':state.get('input_snapshot',{}),
                  'step_timeline':state.get('timeline',[]),'screenshots':state.get('screenshots',[]),
                  'step_count':state.get('cursor',0),'bundle_id':payload['bundle_id'],'error':error,'outcome_unknown':self.inflight or state.get('outcome_unknown',False),
                  **recording.close()}
        has_assertion = any(str(s.get('action','')).startswith('assert') for s in result['steps'])
        result['result_label'] = '任务中断，需检查设备实际结果' if error or result['outcome_unknown'] else '业务验证通过' if has_assertion else '操作完成，业务结果未验证'
        return {'total':1,'failed_count':int(bool(error) or bool(result['outcome_unknown'])),'canceled':canceled,
                'records':[{'name':'App 设备实操生成','project_id':payload['project_id'],
                            'status':'failed' if error or result['outcome_unknown'] else 'success','data':result}]}

    def connection_state(self, task_id, lease):
        while True:
            state = self.exchange(task_id,lease,'state')
            if requested(self.config) or state['phase'] in {'canceled','finishing'}:
                raise AppTaskStopped(state['phase'] != 'finishing')
            if state['phase'] != 'paused':
                return state
            self.sleep(1)

    def prepare_connection(self, task_id, lease, payload):
        self.connection_state(task_id,lease)
        device, connection = resolve_device(payload['device'],self.config.node_key)
        self.connection_state(task_id,lease)
        while not self.exchange(task_id,lease,'connection',{'status':'connected','wda_url':connection['wda_url'],
                'reported_udid':connection.get('reported_udid') or ''}).get('accepted'):
            self.connection_state(task_id,lease)
            self.sleep(1)
        payload['device'] = device

    def discover(self, task_id, lease, session, reused):
        current = foreground_identity(session)
        if current['bundle_id'] != 'com.apple.springboard':
            self.exchange(task_id,lease,'connection',{'status':'identified',**current})
            return
        screen,encoded,_ = capture(session,'com.apple.springboard')
        self.exchange(task_id,lease,'observation',{'observation_id':uuid.uuid4().hex,
            'screen':screen,'screenshot_base64':encoded,'session_reused':reused})

    def action(self,task_id,lease,payload,session,actions,command):
        started = time.monotonic()
        report = {'nonce':command['nonce'],'status':'begin'}
        begin = self.exchange(task_id,lease,'action',report)
        if not begin.get('execute'):
            return
        self.inflight = True
        screen,_,_ = capture(session,command.get('expected_bundle_id') or payload['bundle_id'])
        if screen['hash'] != command['screen_hash']:
            self.exchange(task_id,lease,'action',{**report,'status':'stale'})
            self.inflight = False
            return
        step = deepcopy(command['step'])
        value = None
        if command.get('input_key'):
            key = command['input_key']
            value = str(self.dynamic.resolve(command['input_info'][key],f'$.inputs.{key}'))
            step['value'] = value
        try:
            element = None
            if step.get('locator'):
                elements = actions._selector(step).find_elements()
                if len(elements) != 1:
                    self.exchange(task_id,lease,'action',{**report,'status':'stale'})
                    self.inflight = False
                    return
                element = elements[0]
            actions.run(step,observed_element=element)
        except Exception:
            self.exchange(task_id,lease,'action',{**report,'status':'failed','error':'设备动作失败，需检查实际结果',
                'duration_ms':round((time.monotonic()-started)*1000)})
            self.inflight = False
            return
        self.exchange(task_id,lease,'action',{**report,'status':'success','input_value':value,
            'duration_ms':round((time.monotonic()-started)*1000)})
        self.inflight = False
