"""Shared, deterministic mobile observation and action contracts."""
import hashlib
import json
import re
from xml.etree import ElementTree


ACTIONS = {'tap', 'input', 'swipe', 'wait', 'assert_text', 'assert_screen_contains', 'hide_keyboard'}
DANGEROUS = re.compile(r'删除|支付|付款|转账|注销|购买|清空|delete|pay|purchase|transfer', re.I)
SENSITIVE = re.compile(r'密码|验证码|口令|password|captcha|verification.code|\botp\b|api.?key|\btoken\b', re.I)


def screen_from_xml(xml, bundle_id, size):
    if len(xml) > 2_000_000 or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise ValueError('Device element tree exceeds safe limits')
    root = ElementTree.fromstring(xml)
    elements, sensitive = [], False
    for node in root.iter():
        attrs = node.attrib
        kind = attrs.get('type') or node.tag
        if attrs.get('visible', 'true') != 'true':
            continue
        editable = any(k in kind for k in ('TextField', 'TextView', 'SearchField'))
        secret = 'SecureTextField' in kind or bool(SENSITIVE.search(attrs.get('label', '') + attrs.get('name', '')))
        sensitive = sensitive or secret
        if len(elements) >= 200:
            continue
        name, label = attrs.get('name', '')[:240], attrs.get('label', '')[:240]
        if editable:
            name = '' if attrs.get('value') and name == attrs['value'] else name
            label = '' if attrs.get('value') and label == attrs['value'] else label
        if not name and not label and not editable:
            continue
        elements.append({'id':len(elements)+1, 'type':kind[:100], 'name':name, 'label':label,
                         'enabled':attrs.get('enabled', 'true') == 'true', 'editable':editable,
                         'sensitive':secret, 'rect':{k:float(attrs.get(k) or 0) for k in ('x','y','width','height')}})
    screen = {'bundle_id':bundle_id, 'width':float(size.width), 'height':float(size.height),
              'elements':elements, 'sensitive':sensitive}
    screen['hash'] = screen_hash(screen)
    return screen


def screen_hash(screen):
    clean = {k:screen[k] for k in ('bundle_id','width','height','elements','sensitive')}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_screen(screen, bundle_id):
    if screen.get('bundle_id') != bundle_id:
        raise ValueError('前台应用不是当前任务的目标应用')
    elements = screen.get('elements')
    if not isinstance(elements, list) or len(elements) > 200:
        raise ValueError('Invalid device observation')
    if any(not isinstance(e, dict) or not isinstance(e.get('id'), int) or len(str(e)) > 4000 for e in elements):
        raise ValueError('Invalid observed element')
    if screen_hash(screen) != screen.get('hash'):
        raise ValueError('Device observation hash mismatch')
    return screen


def element_locator(element, elements):
    name, label = element.get('name'), element.get('label')
    if name and sum(e.get('name') == name for e in elements) == 1:
        return {'locator_type':'accessibility_id', 'locator':name}
    pairs = [('type',element['type'])]
    if label:
        pairs.append(('label',label))
    elif name:
        pairs.append(('name',name))
    else:
        raise ValueError('元素没有可复用的定位标识，请人工补充')
    if sum(all(e.get(k) == v for k,v in pairs) for e in elements) != 1:
        raise ValueError('定位不唯一，不能自动操作')
    def quote(value):
        return str(value).replace('\\','\\\\').replace("'", "\\'")
    return {'locator_type':'ios_predicate', 'locator':' AND '.join(f"{k} == '{quote(v)}'" for k,v in pairs)}


def decision_command(decision, screen):
    raw = decision.get('step') or {}
    action = raw.get('action')
    if action not in ACTIONS:
        raise ValueError('模型提出了当前设备不支持的动作')
    step = {'name':str(raw.get('name') or action)[:160], 'action':action}
    command = {'step':step, 'screen_hash':screen['hash'], 'input_info':{}, 'manual':False}
    if action in {'tap','input','assert_text'}:
        element = next((e for e in screen['elements'] if e['id'] == raw.get('target_id')), None)
        if not element or not element.get('enabled'):
            raise ValueError('目标元素不存在或不可操作')
        step.update(element_locator(element, screen['elements']))
        command['target_id'] = element['id']
        command['manual'] = bool(element.get('sensitive'))
        if action == 'input':
            if not element.get('editable'):
                raise ValueError('目标元素不是输入框')
            key = str(raw.get('input_key') or '')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', key):
                raise ValueError('输入操作需要有效参数名')
            if command['manual'] or SENSITIVE.search(key):
                raise ValueError('敏感输入请在手机上人工填写后继续')
            value = raw.get('value')
            if not isinstance(value, str) or len(value) > 2000:
                raise ValueError('输入内容无效')
            step['value'] = '{{' + key + '}}'
            step['input_key'] = key
            command['input_info'][key] = value
            command['input_key'] = key
        if action == 'assert_text':
            step['expected'] = str(raw.get('expected') or '')[:500]
            if not step['expected']:
                raise ValueError('文本断言缺少预期内容')
    elif action == 'swipe':
        direction = raw.get('direction')
        if direction not in {'up','down','left','right'}:
            raise ValueError('滑动方向无效')
        step.update(direction=direction, duration_ms=500)
    elif action == 'wait':
        step['duration_ms'] = min(5000,max(100,int(raw.get('duration_ms') or 1000)))
    elif action == 'assert_screen_contains':
        step['expected'] = str(raw.get('expected') or '')[:500]
        if not step['expected']:
            raise ValueError('屏幕断言缺少预期内容')
    command['requires_confirmation'] = bool(decision.get('requires_confirmation')) or bool(DANGEROUS.search(json.dumps(step,ensure_ascii=False)))
    return command
