import base64
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from web_automation.engines import playwright

from app.core.exceptions import BusinessRuleError
from app.services.generation_candidate_service import validate_candidate
from app.services.web_feature_testing_service import VERSIONS, WebFeatureTestingService
from app.services.web_target_url_service import resolve_web_target_url
from web_automation import dynamic_values, manual, outcomes

RUNNER = r'''import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit
from getpass import getpass
from playwright.async_api import async_playwright
from web_automation.dynamic_values import DynamicValueContext
from web_automation.engines.playwright import PlaywrightEngine
from web_automation.manual import manual_input_locator
from web_automation.outcomes import verification_error

async def run(args):
    root = Path(__file__).resolve().parent
    candidate = json.loads((root / "steps.json").read_text(encoding="utf-8-sig"))
    if error := verification_error(candidate["steps"]):
        raise ValueError(error)
    inputs = json.loads(Path(args.inputs or root / "inputs.json").read_text(encoding="utf-8-sig"))
    manual = any(s["action"] == "manual" for s in candidate["steps"]) or args.login
    private = manual or any(s.get("sensitive") for s in candidate["steps"])
    if manual and args.headless:
        raise ValueError("Manual input requires a headed browser")
    for step in candidate["steps"]:
        if step.get("sensitive"):
            key = step["input_key"]
            value = inputs.get(key) if key in inputs else getpass(f"Password for {key}: ")
            inputs[key] = value.replace("{{", r"\{{")
    dynamic = DynamicValueContext({**candidate.get("variables", {}), **inputs})
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless, executable_path=args.browser_executable)
        context = await browser.new_context(**({"record_video_dir": str(root / "evidence")} if not private else {}))
        page = await context.new_page()
        try:
            await page.goto(candidate["url"], wait_until="domcontentloaded")
            if args.login:
                await asyncio.to_thread(input, "Complete login, then press Enter: ")
                await page.goto(candidate["url"], wait_until="domcontentloaded")
            engine = PlaywrightEngine(page, default_timeout=10000)
            for index, original in enumerate(candidate["steps"], 1):
                if urlsplit(page.url).netloc != urlsplit(candidate["url"]).netloc:
                    raise RuntimeError("Browser left the target site")
                step = dynamic.resolve(original)
                if step["action"] == "manual":
                    locator = await manual_input_locator(page, step)
                    if locator is None:
                        continue
                    await asyncio.to_thread(input, f"Fill {step.get('name', 'field')} in browser, then press Enter: ")
                    if not await locator.input_value():
                        raise ValueError("Manual field is empty")
                else:
                    await engine.execute(step)
                if not private:
                    (root / "evidence").mkdir(exist_ok=True)
                    await page.screenshot(path=str(root / "evidence" / f"step-{index}.png"), full_page=True)
            if urlsplit(page.url).netloc != urlsplit(candidate["url"]).netloc:
                raise RuntimeError("Browser left the target site")
            print("Operations completed; " + ("business assertions passed" if any(s["action"] == "assert" for s in candidate["steps"]) else "business result not verified"))
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--browser-executable")
    asyncio.run(run(parser.parse_args()))
'''


class WebScriptExportService:
    def __init__(self, repository):
        self.repository = repository

    def feature(self, feature_id, version_id=None):
        source = WebFeatureTestingService(self.repository).feature(feature_id)
        version_id = version_id or (source.get('data') or {}).get('script_version')
        version = self.repository.get(VERSIONS, version_id) if version_id else None
        if not version or version['data'].get('feature_id') != feature_id or version.get('project_id') != source['project_id']:
            raise BusinessRuleError('请先保存当前功能的脚本版本')
        return self.bundle(source, version['data']['candidate'], version_id, version['status'])

    def bundle(self, source, candidate, identifier, status='draft'):
        original_url = candidate.get('url')
        candidate = validate_candidate('WEB', candidate, source)
        candidate['url'] = original_url or resolve_web_target_url(self.repository, source)
        inputs = candidate.pop('input_info', {})
        candidate['variables'] = {k: v for k, v in candidate.get('variables', {}).items() if k not in inputs}
        files = {'run.py': RUNNER, 'steps.json': json.dumps(candidate, ensure_ascii=False, indent=2), 'inputs.json': json.dumps(inputs, ensure_ascii=False, indent=2),
                 'requirements.txt': 'playwright>=1.48,<2\n', 'web_automation/__init__.py': '', 'web_automation/engines/__init__.py': '',
                 'web_automation/dynamic_values.py': Path(dynamic_values.__file__).read_text(encoding='utf-8'),
                 'web_automation/manual.py': Path(manual.__file__).read_text(encoding='utf-8'),
                 'web_automation/outcomes.py': Path(outcomes.__file__).read_text(encoding='utf-8'),
                 'web_automation/engines/playwright.py': Path(playwright.__file__).read_text(encoding='utf-8'),
                 'README.txt': f'Script status: {status}. Export does not verify execution.\nInstall: python -m pip install -r requirements.txt\nBrowser: python -m playwright install chromium\nRun: python run.py [--headless] [--login] [--inputs inputs.json]\nInputs and steps are separate. Manual secrets must be entered only in the headed browser.\n'}
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
            for filename, content in files.items():
                archive.writestr(filename, content)
        return {'filename': f'web_case_{identifier}.py', 'script': RUNNER, 'bundle_filename': f'web_case_{identifier}.zip', 'bundle_base64': base64.b64encode(buffer.getvalue()).decode('ascii'), 'status': status}
