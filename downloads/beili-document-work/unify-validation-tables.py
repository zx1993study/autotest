"""Unify existing evidence by feature and test point, preserving all unique results."""
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import base64
import json
import re
from lxml import etree

WORK = Path(__file__).parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG = "http://schemas.microsoft.com/office/2006/xmlPackage"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W, "pkg": PKG}
Q = lambda name: "{" + W + "}" + name
root = etree.parse(str(WORK / "unify-input-flat.xml"))
tables = root.findall(".//w:tbl", NS)
assert len(tables) == 3


def plain(el):
    return "".join(el.xpath(".//w:t/text()", namespaces=NS))


def text_lines(cell):
    paragraphs = []
    for p in cell.findall("w:p", NS):
        value = ""
        for node in p.iter():
            if node.tag == Q("t"):
                value += node.text or ""
            elif node.tag in {Q("br"), Q("cr")}:
                value += "\n"
        paragraphs.append(value)
    return "\n".join(paragraphs)


def set_text(cell, value, bold=False):
    for node in list(cell):
        if node.tag != Q("tcPr"):
            cell.remove(node)
    p = etree.SubElement(cell, Q("p"))
    pp = etree.SubElement(p, Q("pPr"))
    etree.SubElement(pp, Q("spacing"), {Q("before"): "0", Q("after"): "0", Q("line"): "220", Q("lineRule"): "exact"})
    etree.SubElement(pp, Q("snapToGrid"), {Q("val"): "0"})
    run = etree.SubElement(p, Q("r"))
    rp = etree.SubElement(run, Q("rPr"))
    etree.SubElement(rp, Q("rFonts"), {Q("ascii"): "Arial", Q("hAnsi"): "Arial", Q("eastAsia"): "宋体"})
    etree.SubElement(rp, Q("sz"), {Q("val"): "18"})
    etree.SubElement(rp, Q("szCs"), {Q("val"): "18"})
    if bold:
        etree.SubElement(rp, Q("b"))
    for i, line in enumerate(value.split("\n")):
        if i:
            etree.SubElement(run, Q("br"))
        node = etree.SubElement(run, Q("t"))
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = line


def blank_like(cell):
    result = deepcopy(cell)
    set_text(result, "")
    return result


def first_json(cell):
    value = text_lines(cell)
    start = value.find("[")
    assert start >= 0
    return json.JSONDecoder().raw_decode(value[start:])[0]


groups = OrderedDict()
duplicates = 0
for index, table in enumerate(tables):
    current = None
    fields = None
    for row in table.findall("w:tr", NS)[1:]:
        cells = row.findall("w:tc", NS)
        assert len(cells) == 5
        if plain(cells[0]):
            name = text_lines(cells[0]).splitlines()[0]
            current = groups.setdefault(name, {"function": deepcopy(cells[0]), "points": OrderedDict()})
        assert current is not None
        if plain(cells[1]):
            fields = deepcopy(cells[1])
        label = plain(cells[2])
        point = "spaces" if "纯空格" in label else "trim" if "首尾" in label else "empty"
        entry = {"category": "手动必填校验" if index == 2 else "普通文本校验", "fields": deepcopy(fields),
                 "result": deepcopy(cells[3]), "status": deepcopy(cells[4])}
        matches = current["points"].setdefault(point, [])
        if index == 1:
            record_ids = set(re.findall(r"#\s*(\d+)", plain(cells[3])))
            duplicate = next((old for old in matches if record_ids <= set(re.findall(r"#\s*(\d+)", plain(old["result"])))
                              and first_json(cells[3]) == first_json(old["result"])
                              and plain(old["status"]) == plain(cells[4])), None)
            assert duplicate, "The manually added sample contains new evidence; retain it instead"
            duplicates += 1
            continue
        matches.append(entry)

main = tables[0]
header = deepcopy(main.findall("w:tr", NS)[0])
template = deepcopy(main.findall("w:tr", NS)[1])
for row in list(main.findall("w:tr", NS)):
    main.remove(row)
main.append(header)
manifest = []
for name, group in groups.items():
    points = [(point, group["points"][point]) for point in ["spaces", "trim", "empty"] if point in group["points"]]
    for ordinal, (point, entries) in enumerate(points):
        row = deepcopy(template)
        for child in list(row):
            if child.tag == Q("tc"):
                row.remove(child)
        base_cells = template.findall("w:tc", NS)
        function = deepcopy(group["function"]) if ordinal == 0 else blank_like(base_cells[0])
        cp = function.find("w:tcPr", NS)
        for vm in cp.findall("w:vMerge", NS):
            cp.remove(vm)
        etree.SubElement(cp, Q("vMerge"), {Q("val"): "restart" if ordinal == 0 else "continue"})
        same_fields = len({plain(entry["fields"]) for entry in entries}) == 1
        field = deepcopy(entries[0]["fields"])
        for vm in field.findall("w:tcPr/w:vMerge", NS):
            vm.getparent().remove(vm)
        if not same_fields:
            set_text(field, "\n\n".join(entry["category"] + "\n" + text_lines(entry["fields"]) for entry in entries))
        point_cell = blank_like(base_cells[2])
        set_text(point_cell, {"spaces": "纯空格\n（3个空格）", "trim": "首尾空格\n（各2空格）", "empty": "空文本\n（\"\"）"}[point])
        result_cell = blank_like(base_cells[3])
        for p in list(result_cell.findall("w:p", NS)):
            result_cell.remove(p)
        for i, entry in enumerate(entries):
            if len(entries) > 1:
                title_cell = blank_like(base_cells[3])
                set_text(title_cell, entry["category"], bold=True)
                if i:
                    spacer = blank_like(base_cells[3])
                    result_cell.append(spacer.find("w:p", NS))
                result_cell.append(title_cell.find("w:p", NS))
            for p in entry["result"].findall("w:p", NS):
                result_cell.append(deepcopy(p))
        status = deepcopy(entries[0]["status"])
        assert len({plain(entry["status"]) for entry in entries}) == 1, "Mixed results need explicit per-scope statuses"
        for cell in [function, field, point_cell, result_cell, status]:
            row.append(cell)
        main.append(row)
        manifest.append({"feature": name, "point": point, "evidence_blocks": len(entries)})

body = main.getparent()
summary = next(p for p in body.findall("w:p", NS) if plain(p).startswith("23项操作，91条必填校验"))
ending = next(p for p in body.findall("w:p", NS) if plain(p).startswith("完整请求、返回及断言"))
body.remove(summary)
body.insert(list(body).index(main), summary)
for p in body.findall("w:p", NS):
    value = plain(p)
    replacement = None
    if value == "普通文本空格校验异常结果":
        replacement = "普通文本与必填字段校验结果"
    elif value.startswith("共26项新增/编辑操作，按内容合并为15行"):
        replacement = "普通文本校验覆盖26项新增/编辑操作：纯空格23项未通过、3项通过，首尾空格26项未通过。"
    elif value.startswith("新增/编辑结论一致时合并"):
        replacement = value + "同一功能合并展示，相同测试点只占一行；普通文本与必填字段范围不同的结果在该行内分别保留。"
    if replacement is not None:
        old_pr = deepcopy(p.find("w:pPr", NS))
        holder = etree.Element(Q("tc"))
        set_text(holder, replacement)
        new_p = holder.find("w:p", NS)
        if old_pr is not None:
            new_p.remove(new_p.find("w:pPr", NS))
            new_p.insert(0, old_pr)
        body.replace(p, new_p)
start, end = list(body).index(main), list(body).index(ending)
for node in list(body)[start + 1:end]:
    assert node.tag == Q("tbl") or not plain(node) or plain(node) == "2026-10-20 手动必填文本补测"
    body.remove(node)

types = etree.Element("{" + CT + "}Types", nsmap={None: CT})
with ZipFile(WORK / "unified-layout.docx", "w", ZIP_DEFLATED) as output:
    for part in root.findall("pkg:part", NS):
        name, kind = part.get("{" + PKG + "}name"), part.get("{" + PKG + "}contentType")
        etree.SubElement(types, "{" + CT + "}Override", PartName=name, ContentType=kind)
        xml = part.find("pkg:xmlData", NS)
        data = etree.tostring(xml[0], encoding="UTF-8", xml_declaration=True, standalone=True) if xml is not None else base64.b64decode(part.find("pkg:binaryData", NS).text)
        output.writestr(name.lstrip("/"), data)
    output.writestr("[Content_Types].xml", etree.tostring(types, encoding="UTF-8", xml_declaration=True, standalone=True))
(WORK / "unified-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"features": len(groups), "test_points": len(manifest), "evidence_blocks": sum(m["evidence_blocks"] for m in manifest), "duplicate_sample_cells": duplicates}))
