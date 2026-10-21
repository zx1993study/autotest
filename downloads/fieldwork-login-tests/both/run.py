import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit
from getpass import getpass
from playwright.async_api import async_playwright
from web_automation.dynamic_values import DynamicValueContext
from web_automation.engines.playwright import PlaywrightEngine
from web_automation.manual import manual_input_locator

async def run(args):
    root = Path(__file__).resolve().parent
    candidate = json.loads((root / "steps.json").read_text(encoding="utf-8-sig"))
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
