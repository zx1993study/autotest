import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="Manually log in and store a private local browser session")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / ".auth" / "h5.json"))
    args = parser.parse_args()
    base = os.environ.get("FW_H5_BASE_URL", "").rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
        raise ValueError("FW_H5_BASE_URL must be an H5 base URL without credentials, query or fragment")
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError("Output exists; choose a different private session filename")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        try:
            page = context.new_page()
            page.goto(base + "/#/pages/login/index", wait_until="domcontentloaded")
            input("Log in manually in the browser, including captcha. Press Enter to store the local session: ")
            if urlsplit(page.url).netloc != parsed.netloc or "/pages/login/" in page.url:
                raise ValueError("Login has not completed on the target site")
            output.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=output)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
