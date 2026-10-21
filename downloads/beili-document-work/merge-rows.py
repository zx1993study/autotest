from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import base64
import json
import re
from lxml import etree

work = Path(__file__).parent
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PKG = 'http://schemas.microsoft.com/office/2006/xmlPackage'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
ns = {'w': W, 'pkg': PKG}
q = lambda n: '{' + W + '}' + n
root = etree.parse(str(work / 'merge-input-flat.xml'))
tables = root.findall('.//w:tbl', ns)
main_tables = [t for t in tables if len(t.findall('w:tr', ns)) == 28]
assert len(main_tables) == 1
table = main_tables[0]
rows = table.findall('w:tr', ns)
assert len(rows) == 28


def text(element):
    pieces = []
    for node in element.iter():
        if node.tag == q('p') and pieces:
            pieces.append('\n')
        elif node.tag == q('br'):
            pieces.append('\n')
        elif node.tag == q('t'):
            pieces.append(node.text or '')
    return ''.join(pieces)


def set_text(element, value):
    p = element if element.tag == q('p') else element.find('w:p', ns)
    pp = deepcopy(p.find('w:pPr', ns)) if p is not None and p.find('w:pPr', ns) is not None else None
    rp_node = p.find('w:r/w:rPr', ns) if p is not None else None
    rp = deepcopy(rp_node) if rp_node is not None else None
    if element.tag == q('p'):
        for child in list(element):
            element.remove(child)
        target = element
    else:
        for child in list(element):
            if child.tag != q('tcPr'):
                element.remove(child)
        target = etree.SubElement(element, q('p'))
    if pp is not None:
        target.append(pp)
    run = etree.SubElement(target, q('r'))
    if rp is not None:
        run.append(rp)
    for i, line in enumerate(value.split('\n')):
        if i:
            etree.SubElement(run, q('br'))
        node = etree.SubElement(run, q('t'))
        node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        node.text = line


def result(cell):
    value = text(cell)
    record_id = int(re.search(r'#(\d+)', value).group(1))
    payload = value[value.index('['):]
    return record_id, payload


def normalize(value):
    return re.sub(r'STR3_\d+_\d+', 'STR3_SAMPLE', value)


groups = OrderedDict()
for row in rows[2:]:
    cells = row.findall('w:tc', ns)
    feature, op = text(cells[0]).strip().rsplit(' ', 1)
    groups.setdefault(feature, {})[op] = row

merged = []
mapping = []
for feature, operations in groups.items():
    if set(operations) != {'新增', '编辑'}:
        continue
    create, edit = operations['新增'], operations['编辑']
    a, b = create.findall('w:tc', ns), edit.findall('w:tc', ns)
    equal = text(a[1]) == text(b[1])
    for col in [2, 4]:
        equal = equal and normalize(result(a[col])[1]) == normalize(result(b[col])[1])
        equal = equal and text(a[col + 1]) == text(b[col + 1])
    if not equal:
        continue
    set_text(a[0], feature + '\n新增/编辑')
    records = []
    for col in [2, 4]:
        create_id, payload = result(a[col])
        edit_id, _ = result(b[col])
        heading = f'新增 #{create_id}（以下JSON）\n编辑 #{edit_id}（结论一致）\n'
        set_text(a[col], heading + payload)
        records.extend([create_id, edit_id])
    table.remove(edit)
    merged.append(feature)
    mapping.append({'feature': feature, 'record_ids': records})

assert len(merged) == 11
assert len(table.findall('w:tr', ns)) == 17

# Keep a readable fixed grid within the portrait A4 text area.
widths = [1140, 1400, 3040, 920, 3040, 926]
pr = table.find('w:tblPr', ns)
for name in ['tblpPr', 'tblOverlap']:
    for el in pr.findall('w:' + name, ns):
        pr.remove(el)
tw = pr.find('w:tblW', ns)
tw.set(q('w'), str(sum(widths)))
tw.set(q('type'), 'dxa')
grid = table.find('w:tblGrid', ns)
grid.clear()
for width in widths:
    etree.SubElement(grid, q('gridCol')).set(q('w'), str(width))
mar = pr.find('w:tblCellMar', ns)
if mar is None:
    mar = etree.SubElement(pr, q('tblCellMar'))
for side, width in [('left', 80), ('right', 80), ('top', 100), ('bottom', 100)]:
    el = mar.find('w:' + side, ns)
    if el is None:
        el = etree.SubElement(mar, q(side))
    el.set(q('w'), str(width))
    el.set(q('type'), 'dxa')
for i, row in enumerate(table.findall('w:tr', ns)):
    trpr = row.find('w:trPr', ns)
    for name in ['gridAfter', 'wAfter', 'gridBefore', 'wBefore', 'trHeight']:
        for el in trpr.findall('w:' + name, ns):
            trpr.remove(el)
    col = 0
    for cell in row.findall('w:tc', ns):
        cp = cell.find('w:tcPr', ns)
        for cm in cp.findall('w:tcMar', ns):
            cp.remove(cm)
        span = 2 if i == 0 and col >= 2 else 1
        cp.find('w:tcW', ns).set(q('w'), str(sum(widths[col:col + span])))
        for run in cell.findall('.//w:r', ns):
            rp = run.find('w:rPr', ns)
            if rp is None:
                rp = etree.Element(q('rPr'))
                run.insert(0, rp)
            for name in ['sz', 'szCs']:
                sz = rp.find('w:' + name, ns)
                if sz is None:
                    sz = etree.SubElement(rp, q(name))
                sz.set(q('val'), '17' if i >= 2 and col in [2, 4] else '18')
        col += span
for other in tables:
    if other is table:
        continue
    other_pr = other.find('w:tblPr', ns)
    for name in ['tblpPr', 'tblOverlap']:
        for el in other_pr.findall('w:' + name, ns):
            other_pr.remove(el)
    other_widths = [1000, 1200, 2410, 640, 2410, 640]
    other_pr.find('w:tblW', ns).set(q('w'), str(sum(other_widths)))
    other_grid = other.find('w:tblGrid', ns)
    other_grid.clear()
    for width in other_widths:
        etree.SubElement(other_grid, q('gridCol')).set(q('w'), str(width))
    for other_row in other.findall('w:tr', ns):
        cells = other_row.findall('w:tc', ns)
        assert len(cells) == 6
        for col, cell in enumerate(cells):
            cell_pr = cell.find('w:tcPr', ns)
            for cm in cell_pr.findall('w:tcMar', ns):
                cell_pr.remove(cm)
            cell.find('w:tcPr/w:tcW', ns).set(q('w'), str(other_widths[col]))
            for run in cell.findall('.//w:r', ns):
                rp = run.find('w:rPr', ns)
                if rp is None:
                    rp = etree.Element(q('rPr'))
                    run.insert(0, rp)
                for name in ['sz', 'szCs']:
                    sz = rp.find('w:' + name, ns)
                    if sz is None:
                        sz = etree.SubElement(rp, q(name))
                    sz.set(q('val'), '16')
for section in root.findall('.//w:sectPr', ns):
    size = section.find('w:pgSz', ns)
    if int(size.get(q('w'))) > int(size.get(q('h'))):
        size.set(q('w'), '11906')
        size.set(q('h'), '16838')
        size.set(q('orient'), 'portrait')
for paragraph in root.findall('.//w:p', ns):
    if any(a.tag == q('tbl') for a in paragraph.iterancestors()):
        continue
    value = text(paragraph)
    if value.startswith('共26项功能'):
        set_text(paragraph, '共26项新增/编辑操作，按内容合并为15行。纯空格23项未通过、3项通过，首尾空格26项未通过。')
    elif value.startswith('纯空格通过仅表示'):
        set_text(paragraph, '新增/编辑结论一致时合并，JSON展示新增记录的原始断言，编辑记录号同时保留，两者仅测试标识不同。更新日志content附存储回读断言。\n纯空格通过仅表示组合请求被拒绝，不代表每个字段均已独立校验。执行记录号可在autotest核对。')

content_types = etree.Element('{' + CT + '}Types', nsmap={None: CT})
with ZipFile(work / 'merged-layout.docx', 'w', ZIP_DEFLATED) as out:
    for part in root.findall('pkg:part', ns):
        name = part.get('{' + PKG + '}name')
        kind = part.get('{' + PKG + '}contentType')
        etree.SubElement(content_types, '{' + CT + '}Override', PartName=name, ContentType=kind)
        xml = part.find('pkg:xmlData', ns)
        if xml is not None:
            data = etree.tostring(xml[0], encoding='UTF-8', xml_declaration=True, standalone=True)
        else:
            data = base64.b64decode(part.find('pkg:binaryData', ns).text)
        out.writestr(name.lstrip('/'), data)
    out.writestr('[Content_Types].xml', etree.tostring(content_types, encoding='UTF-8', xml_declaration=True, standalone=True))
(work / 'merge-map.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'merged_pairs': len(merged), 'body_rows': 15, 'features': merged}, ensure_ascii=False))
