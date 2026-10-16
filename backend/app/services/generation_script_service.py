from app.core.exceptions import BusinessRuleError
from app.services.business_generation_service import BusinessGenerationService
from app.services.web_script_export_service import WebScriptExportService


class GenerationScriptService:
    def __init__(self, repository):
        self.repository = repository

    def export(self, task_id):
        generation = BusinessGenerationService(self.repository)
        task = generation.get(task_id)
        data = task['data']
        candidate = data.get('accepted_candidate') or (data.get('result') or {}).get('candidate')
        if data.get('domain') != 'WEB' or task['status'] != 'success' or not candidate:
            raise BusinessRuleError('没有可导出的 Web 操作脚本')
        source = generation.source('WEB', data['source_id'])
        verification = (candidate.get('generation_meta') or {}).get('verification') or {}
        return WebScriptExportService(self.repository).bundle(source, candidate, task_id, verification.get('status') or 'draft')
