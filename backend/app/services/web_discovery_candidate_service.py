"""Join AI intent to observed controls without inventing selectors or assertions."""

import re
from copy import deepcopy

from web_automation.discovery.dom import safe_dom

from app.services.web_discovery_evidence_service import discovery_parameters
from app.services.web_input_policy_service import normalize_parameters, bind_input_steps


def prepare_discovery(output, capture):
    dom = safe_dom(getattr(capture, 'dom', ()))
    parameters = discovery_parameters(output.get('parameters') or [])
    warnings = list(output.get('warnings') or [])
    for index, control in enumerate(dom):
        if control['tag'] not in {'input', 'textarea', 'select'} or not control['locators']:
            continue
        names = {s for s in (control['name'], control['label'], control['placeholder']) if s}
        matches = [p for p in parameters if p['key'] in names or p['label'] in names or p['locator'] in names]
        if len(matches) > 1:
            warnings.append(f"字段 {control['label'] or control['name']} 对应多个参数，需确认")
            continue
        key = control['name'] if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', control['name']) else f'field_{index + 1}'
        parameter = matches[0] if matches else {'key': key, 'label': control['label'] or control['placeholder'] or key}
        if not matches:
            parameters.append(parameter)
        kind = {'textarea': 'textarea', 'select': 'select'}.get(control['tag'], {'number': 'number', 'date': 'date', 'datetime-local': 'datetime', 'checkbox': 'boolean'}.get(control['type'], 'text'))
        password = control['type'] == 'password' or bool(re.search(r'password|passwd|密码', ' '.join(names), re.I))
        parameter.update(type='password' if password else 'manual' if control['sensitive'] else kind, options=control['options'], **control['locators'][0], frame_selector=control['frame_selector'])
        if control['required_known']:
            parameter.update(required=control['required'], required_known=True)
        if control['sensitive']:
            parameter['default_value'] = None
        parameter['confirmed'] = False
    candidate = deepcopy(output.get('candidate'))
    if candidate and dom:
        for step in candidate.get('steps') or []:
            if step.get('action') == 'wait':
                continue
            matched = [control for control in dom if _matches(step, control)]
            if len(matched) == 1:
                step.update(matched[0]['locators'][0], frame_selector=matched[0]['frame_selector'])
                if matched[0]['sensitive']:
                    step['action'] = 'manual'
                    step.pop('value', None)
            elif step.get('action') != 'assert' and step != (getattr(capture, 'entry_element', None) or {}):
                # An entry can be absent after opening a dialog; only its approved hint is allowed.
                entry = getattr(capture, 'entry_element', None) or {}
                if step.get('action') != 'click' or step.get('locator') != entry.get('locator'):
                    warnings.append(f"步骤 {step.get('name') or step.get('locator')} 定位未获真实 DOM 确认")
                    candidate = None
                    break
    parameters = normalize_parameters(parameters)
    manual_keys = {p['key'] for p in parameters if p['type'] in {'manual', 'password'}}
    if candidate:
        candidate['steps'] = bind_input_steps(candidate.get('steps'), parameters)
        for field in ('input_info', 'variables'):
            candidate[field] = {k: v for k, v in (candidate.get(field) or {}).items() if k not in manual_keys}
    return discovery_parameters(parameters), candidate, warnings


def _matches(step, control):
    if (step.get('frame_selector') or '') != control['frame_selector']:
        return False
    return any(step.get('locator_type') == loc['locator_type'] and step.get('locator') == loc['locator'] and (loc['locator_type'] != 'role' or step.get('role_name', step.get('name')) == loc['role_name']) for loc in control['locators'])
