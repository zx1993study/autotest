"""Reshape comparison tables without changing their evidence text."""
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import base64
import json
from lxml import etree

WORK = Path(__file__).parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG = "http://schemas.microsoft.com/office/2006/xmlPackage"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W, "pkg": PKG}
Q = lambda name: "{" + W + "}" + name
root = etree.parse(str(WORK / "five-input-flat.xml"))


def plain(cell):
    return "".join(cell.xpath(".//w:t/text()", namespaces=NS))


def prop(parent, name, **values):
    node = parent.find("w:" + name, NS)
    if node is None:
        node = etree.SubElement(parent, Q(name))
    for key, value in values.items():
        node.set(Q(key), str(value))
    return node


def new_cell(value):
    cell = etree.Element(Q("tc"))
    etree.SubElement(cell, Q("tcPr"))
    p = etree.SubElement(cell, Q("p"))
    run = etree.SubElement(p, Q("r"))
    for index, line in enumerate(value.split("\n")):
        if index:
            etree.SubElement(run, Q("br"))
        text = etree.SubElement(run, Q("t"))
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = line
    return cell


def style_cell(cell, width, column, header=False, merge=None):
    cp = prop(cell, "tcPr")
    for name in ["gridSpan", "vMerge", "hMerge", "noWrap", "tcFitText", "tcMar"]:
        for node in cp.findall("w:" + name, NS):
            cp.remove(node)
    prop(cp, "tcW", w=width, type="dxa")
    if header and column == 4:
        prop(cp, "noWrap")
    if merge:
        prop(cp, "vMerge", val=merge)
    prop(cp, "vAlign", val="center" if header or column == 4 else "top")
    prop(cp, "shd", val="clear", color="auto", fill="E7E6E6" if header else "FFFFFF")
    borders = prop(cp, "tcBorders")
    for edge in ["top", "left", "bottom", "right"]:
        prop(borders, edge, val="single", sz=4, color="A6A6A6")
    margins = prop(cp, "tcMar")
    for edge, value in [("top", 65), ("bottom", 65), ("left", 75), ("right", 75)]:
        prop(margins, edge, w=value, type="dxa")
    for p in cell.findall("w:p", NS):
        pp = prop(p, "pPr")
        for name in ["pStyle", "spacing", "ind", "jc", "keepNext", "keepLines", "snapToGrid", "pageBreakBefore"]:
            for node in pp.findall("w:" + name, NS):
                pp.remove(node)
        prop(pp, "spacing", before=0, after=0, line=220, lineRule="exact")
        prop(pp, "snapToGrid", val=0)
        prop(pp, "jc", val="center" if header or column == 4 else "left")
        for run in p.findall("w:r", NS):
            rp = prop(run, "rPr")
            for name in ["rFonts", "sz", "szCs", "b", "bCs"]:
                for node in rp.findall("w:" + name, NS):
                    rp.remove(node)
            font = "Consolas" if column == 3 and not header else "Arial"
            prop(rp, "rFonts", ascii=font, hAnsi=font, eastAsia="宋体")
            prop(rp, "sz", val=18)
            prop(rp, "szCs", val=18)
            if header:
                prop(rp, "b")
                prop(rp, "color", val="000000")


tables = root.findall(".//w:tbl", NS)
evidence_before = []
evidence_after = []
summary = []
for index, table in enumerate(tables):
    rows = table.findall("w:tr", NS)
    data_rows = rows[2:] if len(rows) > 1 else rows
    old_widths = [int(c.get(Q("w"))) for c in table.findall("w:tblGrid/w:gridCol", NS)]
    total = sum(old_widths)
    ratio = [1900, 1400, 1400, 4666, 1100]
    widths = [round(total * value / sum(ratio)) for value in ratio]
    widths[-1] += total - sum(widths)
    tp = prop(table, "tblPr")
    for name in ["tblpPr", "tblOverlap", "tblInd", "tblCellSpacing"]:
        for node in tp.findall("w:" + name, NS):
            tp.remove(node)
    prop(tp, "tblW", w=total, type="dxa")
    prop(tp, "tblLayout", type="fixed")
    prop(tp, "jc", val="center")
    grid = table.find("w:tblGrid", NS)
    grid.clear()
    for width in widths:
        etree.SubElement(grid, Q("gridCol"), {Q("w"): str(width)})
    for row in rows:
        table.remove(row)
    header = etree.SubElement(table, Q("tr"))
    hr = etree.SubElement(header, Q("trPr"))
    prop(hr, "tblHeader")
    prop(hr, "cantSplit")
    for column, title in enumerate(["功能", "字段", "测试点", "返回结果", "是否通过"]):
        cell = new_cell(title)
        style_cell(cell, widths[column], column, header=True)
        header.append(cell)
    points = ["空文本\n（\"\"）", "纯空格\n（3个空格）"] if index == 2 else ["纯空格\n（3个空格）", "首尾空格\n（各2空格）"]
    for old_row in data_rows:
        cells = old_row.findall("w:tc", NS)
        assert len(cells) == 6
        evidence_before.extend([plain(cells[2]), plain(cells[4])])
        for variant, source in enumerate([2, 4]):
            row = etree.SubElement(table, Q("tr"))
            rp = etree.SubElement(row, Q("trPr"))
            prop(rp, "cantSplit")
            new_cells = [deepcopy(cells[0]) if variant == 0 else new_cell(""),
                         deepcopy(cells[1]) if variant == 0 else new_cell(""),
                         new_cell(points[variant]), deepcopy(cells[source]), deepcopy(cells[source + 1])]
            for column, cell in enumerate(new_cells):
                style_cell(cell, widths[column], column,
                           merge=("restart" if variant == 0 else "continue") if column < 2 else None)
                row.append(cell)
            evidence_after.append(plain(new_cells[3]))
    summary.append({"table": index + 1, "groups": len(data_rows), "rows": len(table.findall("w:tr", NS)), "widths": widths})

assert evidence_before == evidence_after, "Evidence changed during table transformation"
types = etree.Element("{" + CT + "}Types", nsmap={None: CT})
with ZipFile(WORK / "five-layout.docx", "w", ZIP_DEFLATED) as output:
    for part in root.findall("pkg:part", NS):
        name, kind = part.get("{" + PKG + "}name"), part.get("{" + PKG + "}contentType")
        etree.SubElement(types, "{" + CT + "}Override", PartName=name, ContentType=kind)
        xml = part.find("pkg:xmlData", NS)
        data = etree.tostring(xml[0], encoding="UTF-8", xml_declaration=True, standalone=True) if xml is not None else base64.b64decode(part.find("pkg:binaryData", NS).text)
        output.writestr(name.lstrip("/"), data)
    output.writestr("[Content_Types].xml", etree.tostring(types, encoding="UTF-8", xml_declaration=True, standalone=True))
(WORK / "five-layout-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
