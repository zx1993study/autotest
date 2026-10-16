"""Bounded, value-free browser metadata used by discovery and recording."""

import logging
import re

from web_automation.engines.playwright import PlaywrightEngine

DOM_SCRIPT = r"""() => Array.from(document.querySelectorAll(
  'input:not([type=hidden]),textarea,select,button,a[href],[role=button],[role=combobox],[contenteditable=true]'
)).filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden').slice(0,200).map(el => {
  const clean = s => String(s || '').replace(/\s+/g,' ').trim().slice(0,160);
  const label = clean(el.getAttribute('aria-label') || Array.from(el.labels || []).map(l => l.textContent).join(' ') ||
    (el.getAttribute('aria-labelledby') || '').split(' ').map(id => document.getElementById(id)?.textContent || '').join(' '));
  const tag = el.tagName.toLowerCase(), type = el.getAttribute('type') || '';
  const text = ['button','a'].includes(tag) || el.getAttribute('role') === 'button' ? clean(el.textContent) : '';
  const role = el.getAttribute('role') || ({button:'button',a:'link',textarea:'textbox',select:'combobox'}[tag]) ||
    (tag === 'input' ? ({checkbox:'checkbox',radio:'radio',number:'spinbutton'}[type] || 'textbox') : '');
  const testid = el.getAttribute('data-testid') || '';
  const name = el.getAttribute('name') || '', placeholder = clean(el.getAttribute('placeholder'));
  let selector = el.id ? '#' + CSS.escape(el.id) : name ? tag + '[name=' + JSON.stringify(name) + ']' : '';
  if (selector && document.querySelectorAll(selector).length !== 1) selector = '';
  const sensitive = type === 'password' || /password|passwd|captcha|verification.?code|验证码|密码/i.test([name,label,placeholder,el.id].join(' '));
  const locators = [];
  if (testid) locators.push({locator_type:'testid',locator:testid});
  if (label) locators.push({locator_type:'label',locator:label});
  if (role && (text || label)) locators.push({locator_type:'role',locator:text || label,role,role_name:text || label});
  if (placeholder) locators.push({locator_type:'placeholder',locator:placeholder});
  if (selector) locators.push({locator_type:'css',locator:selector});
  return {tag,type,name,label,text,role,placeholder,sensitive,required:el.required || el.getAttribute('aria-required') === 'true',
    required_known:el.hasAttribute('required') || el.hasAttribute('aria-required'), locators,
    options:tag === 'select' ? Array.from(el.options).slice(0,60).map(o => ({label:clean(o.textContent),value:o.value})) : []};
})"""


def safe_dom(items):
    result = []
    for item in (items or [])[:200]:
        if not isinstance(item, dict):
            continue
        row = {key: str(item.get(key) or '')[:512] for key in ('tag', 'type', 'name', 'label', 'text', 'role', 'placeholder', 'frame_selector')}
        row.update({key: bool(item.get(key)) for key in ('sensitive', 'required', 'required_known')})
        row['sensitive'] = row['sensitive'] or row['type'] == 'password' or bool(re.search(r'password|passwd|captcha|验证码|密码', ' '.join(row[k] for k in ('name', 'label', 'placeholder')), re.IGNORECASE))
        row['options'] = [{'label': str(o.get('label') or '')[:160], 'value': str(o.get('value') or '')[:160]} for o in (item.get('options') or [])[:60] if isinstance(o, dict)]
        row['locators'] = [{k: str(loc.get(k) or '')[:512] for k in ('locator_type', 'locator', 'role', 'role_name')} for loc in (item.get('locators') or [])[:5] if isinstance(loc, dict) and loc.get('locator_type') in {'role', 'label', 'testid', 'placeholder', 'css'} and loc.get('locator')]
        result.append(row)
    return result


async def collect_dom(page):
    if not hasattr(page, 'evaluate'):
        return []
    rows = []
    frames = getattr(page, 'frames', [page])
    for frame in frames:
        scope = ''
        try:
            if frame != getattr(page, 'main_frame', page):
                owner = await frame.frame_element()
                scope = await owner.evaluate("el => el.id ? '#' + CSS.escape(el.id) : el.name ? 'iframe[name=' + JSON.stringify(el.name) + ']' : ''")
                if not scope or await page.locator(scope).count() != 1:
                    continue
            raw = await frame.evaluate(DOM_SCRIPT)
            for row in safe_dom(raw):
                row['frame_selector'] = scope
                valid = []
                for loc in row['locators']:
                    target = PlaywrightEngine(page)._strict_locator({**loc, 'frame_selector': scope})
                    if await target.count() == 1:
                        valid.append(loc)
                row['locators'] = valid
                rows.append(row)
                if len(rows) >= 200:
                    return rows
        except Exception as exc:  # noqa: BLE001 - inaccessible frames must not expose field values.
            logging.getLogger(__name__).debug('DOM collection unavailable: %s', type(exc).__name__)
            continue
    return rows
