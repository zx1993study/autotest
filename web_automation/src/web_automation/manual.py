"""Resolve conditional manual fields without reading or retaining their input."""

from web_automation.engines.playwright import PlaywrightEngine


async def manual_input_locator(page, step):
    locator = PlaywrightEngine(page)._strict_locator(step)
    if step.get("optional") is True:
        # Conditional login fields settle after the public configuration requests.
        await page.wait_for_load_state("networkidle", timeout=10000)
        if await locator.count() == 0:
            return None
    await locator.wait_for(state="visible", timeout=10000)
    if await locator.count() != 1:
        raise ValueError("人工输入定位不唯一")
    return locator
