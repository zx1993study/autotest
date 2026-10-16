"""Record user actions through public browser bindings, never private codegen APIs."""

RECORDING_SCRIPT = r"""(() => {
  let sequence = 0;
  const clean = s => String(s || '').replace(/\s+/g,' ').trim().slice(0,160);
  function capture(event) {
    const el = event.type === 'click' ? event.target.closest('button,a,[role=button]') : event.target;
    if (!el || !el.tagName || (event.type === 'change' && !el.matches('input,textarea,select'))) return;
    const tag = el.tagName.toLowerCase(), type = el.type || '';
    const label = clean(el.getAttribute('aria-label') || Array.from(el.labels || []).map(l => l.textContent).join(' '));
    const text = clean(el.textContent), name = el.getAttribute('name') || '';
    const sensitive = type === 'password' || /password|passwd|captcha|验证码|密码/i.test([name,label,el.placeholder].join(' '));
    let locator;
    const testid = el.getAttribute('data-testid');
    if (testid && document.querySelectorAll('[data-testid=' + JSON.stringify(testid) + ']').length === 1)
      locator = {locator_type:'testid',locator:testid};
    const css = el.id ? '#' + CSS.escape(el.id) : name ? tag + '[name=' + JSON.stringify(name) + ']' : '';
    if (!locator && css && document.querySelectorAll(css).length === 1) locator = {locator_type:'css',locator:css};
    if (!locator && label && Array.from(document.querySelectorAll('input,textarea,select')).filter(x =>
      clean(x.getAttribute('aria-label') || Array.from(x.labels || []).map(l => l.textContent).join(' ')) === label).length === 1)
      locator = {locator_type:'label',locator:label};
    const role = el.getAttribute('role') || (tag === 'a' ? 'link' : 'button');
    if (!locator && event.type === 'click' && text && Array.from(document.querySelectorAll('button,a,[role=button]')).filter(x =>
      clean(x.textContent) === text && (x.getAttribute('role') || (x.tagName === 'A' ? 'link' : 'button')) === role).length === 1)
      locator = {locator_type:'role',locator:text,role,role_name:text};
    if (!locator) { void window.autotestRecord({sequence:++sequence,error:'操作目标没有唯一定位'}); return; }
    const action = event.type === 'click' ? 'click' : sensitive ? 'manual' : tag === 'select' ? (el.multiple ? 'multi_select' : 'select') : type === 'checkbox' ? (el.checked ? 'check' : 'uncheck') : 'fill';
    const value = sensitive ? undefined : tag === 'select' ? (el.multiple ? Array.from(el.selectedOptions).map(o => o.value) : el.value) : type === 'checkbox' ? el.checked : el.value;
    void window.autotestRecord({sequence:++sequence,step:{name:label || text || name || action,action,...locator},key:name,value,sensitive});
  }
  document.addEventListener('click',capture,true);
  document.addEventListener('change',capture,true);
})()"""


def recording_candidate(events, name):
    import re

    steps, inputs, errors = [], {}, []
    if len(events) > 60:
        errors.append('录制超过 60 步')
    for event in sorted(events, key=lambda e: e.get('sequence', 0))[:60]:
        if event.get('error'):
            errors.append(event['error'])
            continue
        step = dict(event['step'])
        step.update(require_unique=True, take_screenshot=not event.get('sensitive'))
        if step['action'] in {'fill', 'select', 'multi_select', 'check', 'uncheck'}:
            key = event.get('key') or ''
            key = key if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) else f'field_{len(inputs) + 1}'
            if key in inputs and inputs[key] != event.get('value'):
                key += f'_{len(steps) + 1}'
            inputs[key] = event.get('value')
            step['value'] = '{{' + key + '}}'
        steps.append(step)
    return {'name': name, 'steps': steps, 'input_info': inputs}, errors
