"""Remove secret inputs and authentication state from Web execution evidence."""
from copy import deepcopy


def redact_record(record, case, auth_context=None):
    data = case.get('data') or {}
    keys = set(data.get('secret_inputs') or {})
    if not keys and not auth_context:
        return record
    values = [str(data.get('variables', {}).get(k) or '') for k in keys]
    if auth_context:
        values.extend(str(c.get('value') or '') for c in auth_context.get('cookies') or [])
        for value in (auth_context.get('headers') or {}).values():
            values.extend([str(value), str(value).removeprefix('Bearer ')])

    def redact(value):
        if isinstance(value, dict):
            return {k: '[redacted]' if k in keys else redact(v) for k, v in value.items() if k not in {'secret_inputs', 'runtime_inputs'}}
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, str):
            for secret in values:
                if secret:
                    value = value.replace(secret, '[redacted]')
        return value

    result = redact(deepcopy(record))
    result['data'].update(cookies=[], storage_state={})
    for step in result['data'].get('steps') or []:
        if step.get('sensitive'):
            step['value'] = '[redacted]'
    return result
