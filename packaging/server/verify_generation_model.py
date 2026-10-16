"""Read current model configuration and call it using isolated in-memory sources."""
import base64
import json
from copy import deepcopy
from pathlib import Path

from run import configure

ROOT = Path(__file__).resolve().parents[2]
configure(Path('/home/xiaox/apps/autotest/shared'), ROOT)

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.business_generation import GenerationRequest, ReferenceScreenshot
from app.services.ai_model_service import AiModelResourceService
from app.services.business_generation_service import BusinessGenerationService
from app.utils.vision_images import red_test_image


class MemoryRepository:
    def __init__(self, model):
        self.rows = {
            'ai_models': [model],
            'projects': [{'id': 700001, 'name': 'Synthetic verification'}],
            'web_pages': [{'id': 700002, 'name': 'Synthetic page', 'project_id': 700001, 'data': {'url': 'http://127.0.0.1/fixture', 'known_elements': [{'locator_type': 'text', 'locator': 'Ready'}, {'locator_type': 'label', 'locator': 'Name'}]}}],
        }

    def list(self, table, *args, **kwargs):
        return self.rows.get(table, []), len(self.rows.get(table, []))

    def get(self, table, item_id):
        return next((r for r in self.rows.get(table, []) if r['id'] == item_id), None)

    def create(self, table, data):
        row = {'id': 700010 + len(self.rows.get(table, [])), **deepcopy(data)}
        self.rows.setdefault(table, []).append(row)
        return row

    def update(self, table, item_id, data):
        row = self.get(table, item_id)
        row.update(data)
        return row

    def update_if_status(self, table, item_id, expected, data):
        row = self.get(table, item_id)
        return self.update(table, item_id, data) if row['status'] == expected else None


def main():
    with SessionLocal() as db:
        model = AiModelResourceService(SqlAlchemyResourceRepository(db)).active_model()
    repository = MemoryRepository(model)
    service = BusinessGenerationService(repository)
    results = []
    conversation_parent = None
    for mode, screenshot, prompt in (
        ('text', False, 'Generate only one fill step for the known label locator Name using {{customerName}}, input_info customerName Synthetic. No assertions. Do not add clicks, waits or extra steps.'),
        ('screenshot', True, 'Generate only one fill step for the known label locator Name using {{customerName}}, input_info customerName Synthetic. No assertions. Do not infer DOM from the synthetic image.'),
        ('explicit_assertion', False, 'Generate only one assert step: locator_type text, locator Ready, expected Ready. No clicks or inputs. This is a synthetic model transport check, not execution.'),
    ):
        images = [ReferenceScreenshot(description='Synthetic red pixel probe; follow the provided Ready locator, do not infer the red pixel as an element.', image_base64=base64.b64encode(red_test_image()).decode())] if screenshot else []
        task = service.submit('WEB', GenerationRequest(source_id=700002, model_id=model['id'], prompt=prompt, screenshots=images))
        service.run(task['id'])
        result = service.get(task['id'])
        data = result['data']
        steps = ((data.get('result') or {}).get('candidate') or {}).get('steps') or []
        contract_ok = len(steps) == 1 and (steps[0].get('action') == 'assert' and steps[0].get('expected') == 'Ready' if mode == 'explicit_assertion' else steps[0].get('action') == 'fill')
        results.append({'mode': mode, 'status': result['status'], 'http_calls': data.get('model_http_calls'), 'steps': len(steps), 'contract_ok': contract_ok, 'questions': len((data.get('result') or {}).get('questions') or []), 'error': data.get('error')})
        if mode == 'text':
            conversation_parent = result
    followup = service.submit('WEB', GenerationRequest(
        source_id=700002, model_id=model['id'], parent_task_id=conversation_parent['id'],
        previous_candidate=conversation_parent['data']['result']['candidate'],
        prompt='Keep the existing fill step unchanged. Append only one assert step: locator_type text, locator Ready, expected Ready. Return the two-step complete candidate, no other actions.',
    ))
    service.run(followup['id'])
    result = service.get(followup['id'])
    data = result['data']
    steps = ((data.get('result') or {}).get('candidate') or {}).get('steps') or []
    results.append({'mode':'conversation','status':result['status'],'http_calls':data.get('model_http_calls'),'steps':len(steps),'messages':len(data.get('conversation') or []),'contract_ok':len(steps)==2 and steps[0].get('action')=='fill' and steps[1].get('expected')=='Ready' and len(data.get('conversation') or [])==4,'error':data.get('error')})
    print(json.dumps({'model_id': model['id'], 'results': results, 'database_writes': 0, 'browser_actions': 0}))
    if any(r['status'] != 'success' or not r['contract_ok'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
