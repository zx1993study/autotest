"""Classify login inputs and adapt legacy manual steps without rewriting history."""
import re
from copy import deepcopy


def input_type(parameter):
    kind = parameter.get('type') or 'text'
    identity = ' '.join(str(parameter.get(k) or '') for k in ('key', 'label', 'locator'))
    if re.search(r'captcha|verification.?code|\botp\b|验证码|校验码', identity, re.I):
        return 'manual'
    if kind == 'password' or re.search(r'password|passwd|密码', identity, re.I):
        return 'password'
    if kind == 'manual' and re.search(r'username|user.?name|account|账号|帐号|账户|用户名', identity, re.I):
        return 'text'
    return kind


def normalize_parameters(parameters):
    result = deepcopy(parameters or [])
    for p in result:
        p['type'] = input_type(p)
        if p['type'] in {'password', 'manual'}:
            p['default_value'] = None
    return result


def parameter_for_step(step, parameters):
    matches = [p for p in parameters if
               step.get('input_key') == p['key'] or step.get('value') == '{{' + p['key'] + '}}' or
               (p.get('locator') and p['locator'] == step.get('locator') and
                p.get('locator_type', 'label') == step.get('locator_type') and
                (p.get('frame_selector') or '') == (step.get('frame_selector') or ''))]
    return matches[0] if len(matches) == 1 else None


def bind_input_steps(steps, parameters):
    result = deepcopy(steps or [])
    for step in result:
        if step.get('action') not in {'fill', 'manual', 'input', 'type'}:
            continue
        p = parameter_for_step(step, parameters)
        if not p:
            continue
        step.update(input_key=p['key'], frame_selector=p.get('frame_selector') or '')
        if p['type'] == 'manual':
            step.update(action='manual', take_screenshot=False)
            step.pop('value', None)
        else:
            if step.get('action') == 'manual' or p['type'] == 'password':
                step.update(action='fill', value='{{' + p['key'] + '}}')
            if p['type'] == 'password':
                step.update(sensitive=True, take_screenshot=False)
    return result


def public_version(version):
    value = deepcopy(version)
    data = value['data']
    data['parameters'] = normalize_parameters(data.get('parameters'))
    if data.get('candidate'):
        data['candidate']['steps'] = bind_input_steps(data['candidate'].get('steps'), data['parameters'])
    return value
