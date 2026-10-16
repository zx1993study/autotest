from copy import deepcopy
from secrets import token_urlsafe

from app.core.exceptions import BusinessRuleError
from app.services.app_exploration_service import AppExplorationService, patch_live
from app.services.generation_candidate_service import safe_context


class AppExplorationControlService:
    def __init__(self,repository):
        self.repository = repository

    def control(self,task_id,feature_id,payload):
        task = AppExplorationService(self.repository).get(task_id,feature_id)
        live = deepcopy(task['data']['live'])
        if payload.request_id in live['request_ids']:
            return AppExplorationService(self.repository).public(task)
        if task['status'] not in {'pending','running'}:
            raise BusinessRuleError('设备任务已结束')
        if task['status'] == 'pending':
            if payload.action != 'cancel':
                raise BusinessRuleError('请等待 Agent 领取任务')
            task = self.repository.update_if_status('agent_tasks',task_id,'pending',{'status':'canceled'})
            if not task:
                return self.control(task_id,feature_id,payload)
            return AppExplorationService(self.repository).public(task)
        if live['phase'] in {'saving','finishing','canceled'}:
            raise BusinessRuleError('当前任务正在结束')
        action = payload.action
        next_phase = 'observing' if task['data']['payload']['bundle_id'] else 'connecting'
        if action == 'cancel':
            live.update(phase='canceled',revision=live['revision']+1)
        elif action == 'pause':
            if live['phase'] == 'executing':
                live['pause_requested'] = True
            else:
                live.update(phase='paused',revision=live['revision']+1,command=None)
        elif action in {'check_app','confirm_app'}:
            required = {'waiting_app','waiting_app_confirmation'} if action == 'check_app' else {'waiting_app_confirmation'}
            if live['phase'] not in required or payload.nonce != live.get('nonce'):
                raise BusinessRuleError('应用识别状态已变化，请刷新后再确认')
            if action == 'confirm_app':
                live['confirmed_app'] = deepcopy(live.get('app_candidate'))
            else:
                live.pop('confirmed_app', None)
            live.update(phase='connecting',revision=live['revision']+1,command=None,nonce=None)
        elif action == 'confirm_not_executed':
            if not live.get('outcome_unknown') or payload.nonce != live.get('nonce'):
                raise BusinessRuleError('当前没有可确认的结果未知步骤')
            live['conversation'].append({'role':'user','content':'人工确认上一动作没有生效，请重新观察再判断，不重放整段脚本。'})
            live.update(outcome_unknown=False,phase=next_phase,revision=live['revision']+1,command=None)
        elif action in {'approve','manual_done'}:
            required = 'waiting_approval' if action == 'approve' else 'waiting_manual'
            if live['phase'] != required or payload.nonce != live.get('nonce'):
                raise BusinessRuleError('等待步骤已变化，请刷新后确认')
            live.update(phase='ready' if action == 'approve' else next_phase,nonce=None)
            if action == 'manual_done':
                live['manual_precondition'] = True
        elif action in {'resume','message'}:
            if live['phase'] not in {'paused','waiting_next','waiting_user','waiting_manual'}:
                raise BusinessRuleError('请等待当前操作结束或暂停后补充')
            if live.get('outcome_unknown'):
                raise BusinessRuleError('上一操作结果未知，请先在手机确认；不能自动重放')
            if action == 'message':
                if not payload.message.strip():
                    raise BusinessRuleError('请输入补充内容')
                if len(live['conversation']) >= 24:
                    raise BusinessRuleError('对话长度已达上限，请完成并保存后开始新任务')
                message = safe_context(payload.message)
                live['conversation'].append({'role':'user','content':message})
                live['message'] = message
            live.update(phase=next_phase,revision=live['revision']+1,command=None,pause_requested=False)
        elif action == 'finish':
            if live['phase'] == 'executing':
                raise BusinessRuleError('请等待当前动作返回后结束')
            live.update(phase='finishing',revision=live['revision']+1)
        live['request_ids'] = (live['request_ids']+[payload.request_id])[-100:]
        return AppExplorationService(self.repository).public(patch_live(self.repository,task,live))


def ask(live, message, phase='waiting_user'):
    live.update(phase=phase,nonce=token_urlsafe(18))
    live['conversation'].append({'role':'assistant','content':str(message)[:2000]})
