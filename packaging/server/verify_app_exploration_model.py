"""Model planning check with synthetic observations, no real device or DB writes."""
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from verify_generation_model import MemoryRepository
from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.ai_model_service import AiModelResourceService
from app.services.app_exploration_planner_service import AppExplorationPlannerService
from app.utils.vision_images import red_test_image
from web_automation.mobile import screen_from_xml


class DeviceMemoryRepository(MemoryRepository):
    def patch_running_agent_task(self, task_id, node_key, patch_data, expected=None):
        row = self.get('agent_tasks',task_id)
        if row['status'] != 'running' or any(row['data'].get(k) != v for k,v in (expected or {}).items()):
            return None
        return self.update('agent_tasks',task_id,{'data':{**row['data'],**deepcopy(patch_data)}})


def main():
    with SessionLocal() as db:
        model = AiModelResourceService(SqlAlchemyResourceRepository(db)).active_model()
    repository = DeviceMemoryRepository(model)
    repository.create('app_features',{'id':700003,'name':'Synthetic message','project_id':700001,'data':{}})
    screen = screen_from_xml('<App><Field type="XCUIElementTypeTextField" name="消息输入框"/>'
        '<Button type="XCUIElementTypeButton" name="发送"/></App>',
        'test.synthetic',SimpleNamespace(width=390,height=844))
    results = []
    with TemporaryDirectory() as temp:
        image = Path(temp)/'synthetic.png'
        image.write_bytes(red_test_image())
        for prompt, expected in (
            ('本次只在消息输入框输入你好，不发送。红色方块是合成图片，不要从图片猜测元素；依据真实观察元素列表。','ready'),
            ('目标控件不在当前界面，请先询问我缺失的入口，不进行点击或滑动。','waiting_user'),
        ):
            task = repository.create('agent_tasks',{'status':'running','data':{'task_type':'app_exploration',
                'claimed_by':'synthetic','payload':{'feature_id':700003,'project_id':700001,'model_id':model['id']},
                'live':{'phase':'planning','revision':1,'cursor':0,'steps':[],'input_info':{},'input_snapshot':{},
                    'timeline':[],'events':[],'conversation':[{'role':'user','content':prompt}],
                    'message':prompt,'screen':screen,'preview':{'screenshot_file':'synthetic.png'},
                    'model_http_calls':0,'observed_at':datetime.now(UTC).isoformat()}}})
            with patch('app.services.app_exploration_planner_service.storage_path',return_value=image):
                AppExplorationPlannerService(repository).plan(task['id'],1)
            live = task['data']['live']
            command = live.get('command') or {}
            ok = live['phase']==expected and (expected!='ready' or command['step']['action']=='input'
                and command['target_id']==1 and '你好' in command['input_info'].values())
            results.append({'phase':live['phase'],'expected':expected,'http_calls':live['model_http_calls'],'contract_ok':ok})
    print(json.dumps({'model_id':model['id'],'results':results,'database_writes':0,'device_actions':0}))
    if not all(r['contract_ok'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
