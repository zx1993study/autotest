"""Save a manually completed browser login. Never solve or bypass captcha."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def capture(args):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, executable_path=args.browser_executable)
        context = browser.new_context()
        try:
            page = context.new_page()
            page.goto(args.base_url.rstrip("/") + "/login")
            input("Complete login and captcha in the browser, then press Enter: ")
            if urlsplit(page.url).path.rstrip("/") in {"/login", "/401", "/404"}:
                raise ValueError("Login was not completed")
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(target))
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://test.waiqin.yios.cn")
    parser.add_argument("--output", default=".auth/state.json")
    parser.add_argument("--browser-executable")
    capture(parser.parse_args())
