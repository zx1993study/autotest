from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree

work = Path(__file__).parent
root = etree.parse(str(work / 'after-flat.xml'))
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PKG = 'http://schemas.microsoft.com/office/2006/xmlPackage'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
ns = {'w': W, 'pkg': PKG}
q = lambda local: '{' + W + '}' + local
table = root.find('.//w:tbl', ns)
pr = table.find('w:tblPr', ns)
for name in ['tblpPr', 'tblOverlap']:
    for el in pr.findall('w:' + name, ns):
        pr.remove(el)
widths = [1660, 1880, 4940, 980, 4940, 998]
pr.find('w:tblW', ns).set(q('w'), str(sum(widths)))
grid = table.find('w:tblGrid', ns)
grid.clear()
for width in widths:
    etree.SubElement(grid, q('gridCol')).set(q('w'), str(width))
for index, row in enumerate(table.findall('w:tr', ns)):
    trpr = row.find('w:trPr', ns)
    for name in ['gridAfter', 'wAfter', 'gridBefore', 'wBefore', 'trHeight']:
        for el in trpr.findall('w:' + name, ns):
            trpr.remove(el)
    cells = row.findall('w:tc', ns)
    spans = [1, 1, 2, 2] if index == 0 else [1] * 6
    assert len(cells) == len(spans), (index, len(cells))
    col = 0
    for cell, span in zip(cells, spans):
        cp = cell.find('w:tcPr', ns)
        cell_col = col
        cp.find('w:tcW', ns).set(q('w'), str(sum(widths[col:col + span])))
        for el in cp.findall('w:gridSpan', ns):
            cp.remove(el)
        if span > 1:
            etree.SubElement(cp, q('gridSpan')).set(q('val'), str(span))
        col += span
        if index < 2:
            shade = cp.find('w:shd', ns)
            if shade is None:
                shade = etree.SubElement(cp, q('shd'))
            shade.set(q('fill'), 'E7E6E6')
            align = cp.find('w:vAlign', ns)
            if align is None:
                align = etree.SubElement(cp, q('vAlign'))
            align.set(q('val'), 'center')
            if cell_col < 2:
                vm = cp.find('w:vMerge', ns)
                if vm is None:
                    vm = etree.SubElement(cp, q('vMerge'))
                vm.set(q('val'), 'restart' if index == 0 else 'continue')
        for p in cell.findall('.//w:p', ns):
            pp = p.find('w:pPr', ns)
            if pp is None:
                pp = etree.Element(q('pPr'))
                p.insert(0, pp)
            snap = pp.find('w:snapToGrid', ns)
            if snap is None:
                snap = etree.SubElement(pp, q('snapToGrid'))
            snap.set(q('val'), '0')
            spacing = pp.find('w:spacing', ns)
            if spacing is None:
                spacing = etree.SubElement(pp, q('spacing'))
            spacing.set(q('line'), '240')
            spacing.set(q('lineRule'), 'auto')
            spacing.set(q('before'), '0')
            spacing.set(q('after'), '0')
            if index < 2:
                jc = pp.find('w:jc', ns)
                if jc is None:
                    jc = etree.SubElement(pp, q('jc'))
                jc.set(q('val'), 'center')
content_types = etree.Element('{' + CT + '}Types', nsmap={None: CT})
with ZipFile(work / 'fixed-layout.docx', 'w', ZIP_DEFLATED) as out:
    for part in root.findall('pkg:part', ns):
        name = part.get('{' + PKG + '}name')
        content_type = part.get('{' + PKG + '}contentType')
        etree.SubElement(content_types, '{' + CT + '}Override', PartName=name, ContentType=content_type)
        xml = part.find('pkg:xmlData', ns)
        if xml is not None:
            data = etree.tostring(xml[0], encoding='UTF-8', xml_declaration=True, standalone=True)
        else:
            import base64
            data = base64.b64decode(part.find('pkg:binaryData', ns).text)
        out.writestr(name.lstrip('/'), data)
    out.writestr('[Content_Types].xml', etree.tostring(content_types, encoding='UTF-8', xml_declaration=True, standalone=True))
print('Repaired table positioning, grid, repeating headers and line spacing')
