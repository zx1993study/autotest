"""Preserve live Word content, add API paths and actual required-text results."""
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
Q = lambda n: "{" + W + "}" + n
root = etree.parse(str(WORK / "required-input-flat.xml"))
previous = json.loads((WORK.parent / "punkrecord-case-suite/reports/last-manual-evidence.json").read_text(encoding="utf-8"))
current = json.loads((WORK.parent / "punkrecord-case-suite/reports/required-text-20261020.json").read_text(encoding="utf-8"))


def text(el):
    return "".join(el.xpath(".//w:t/text()", namespaces=NS))


def path_template(path):
    return re.sub(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", "{id}", path)


def lines(cell, value, size=18, font="宋体", bold=False, color="000000"):
    for child in list(cell):
        if child.tag not in {Q("tcPr"), Q("pPr")}:
            cell.remove(child)
    p = cell if cell.tag == Q("p") else etree.SubElement(cell, Q("p"))
    pp = p.find("w:pPr", NS)
    if pp is None:
        pp = etree.SubElement(p, Q("pPr"))
    etree.SubElement(pp, Q("spacing"), {Q("after"): "0", Q("before"): "0", Q("line"): "210", Q("lineRule"): "exact"})
    etree.SubElement(pp, Q("snapToGrid"), {Q("val"): "0"})
    rp = etree.SubElement(etree.SubElement(p, Q("r")), Q("rPr"))
    etree.SubElement(rp, Q("rFonts"), {Q("ascii"): font, Q("hAnsi"): font, Q("eastAsia"): "宋体"})
    etree.SubElement(rp, Q("sz"), {Q("val"): str(size)})
    etree.SubElement(rp, Q("szCs"), {Q("val"): str(size)})
    etree.SubElement(rp, Q("color"), {Q("val"): color})
    if bold:
        etree.SubElement(rp, Q("b"))
    run = rp.getparent()
    for index, line in enumerate(value.split("\n")):
        if index:
            etree.SubElement(run, Q("br"))
        node = etree.SubElement(run, Q("t"))
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = line
    return p


def dimensions(table, widths):
    pr = table.find("w:tblPr", NS)
    for name in ["tblpPr", "tblOverlap"]:
        for el in pr.findall("w:" + name, NS):
            pr.remove(el)
    tw = pr.find("w:tblW", NS)
    tw.set(Q("w"), str(sum(widths)))
    tw.set(Q("type"), "dxa")
    grid = table.find("w:tblGrid", NS)
    grid.clear()
    for width in widths:
        etree.SubElement(grid, Q("gridCol"), {Q("w"): str(width)})
    for row in table.findall("w:tr", NS):
        cursor = 0
        for cell in row.findall("w:tc", NS):
            tcpr = cell.find("w:tcPr", NS)
            span = tcpr.find("w:gridSpan", NS)
            count = int(span.get(Q("val"))) if span is not None else 1
            width = tcpr.find("w:tcW", NS)
            width.set(Q("w"), str(sum(widths[cursor:cursor + count])))
            width.set(Q("type"), "dxa")
            cursor += count
            for no_wrap in tcpr.findall("w:noWrap", NS):
                tcpr.remove(no_wrap)


api = OrderedDict()
for row in previous["results"]:
    feature, op = row["feature"].rsplit(" ", 1)
    api.setdefault(feature, {})[op] = row["request"]["method"] + " /api/v1" + path_template(row["request"]["path"])

tables = root.findall(".//w:tbl", NS)
main = next(t for t in tables if len(t.findall("w:tr", NS)) == 17)
updates = []
for table in tables:
    for row in table.findall("w:tr", NS):
        cell = row.find("w:tc", NS)
        old = text(cell)
        feature = next((f for f in sorted(api, key=len, reverse=True) if old.replace("\n", "").startswith(f)), None)
        if not feature:
            continue
        operations = [op for op in ["新增", "编辑"] if op in old]
        value = feature + "\n" + "/".join(operations)
        value += "\n" + "\n".join(api[feature][op] for op in operations)
        lines(cell, value, size=17)
        updates.append({"feature": feature, "operations": operations, "paths": [api[feature][op] for op in operations]})
dimensions(main, [1600, 1200, 2900, 933, 2900, 933])

# Reuse the prior six-column comparison structure for the additional findings.
new = deepcopy(main)
all_rows = new.findall("w:tr", NS)
row_template = deepcopy(all_rows[2])
for row in all_rows[2:]:
    new.remove(row)
headers = new.findall("w:tr", NS)
for i, value in enumerate(["功能 / API", "必填字段", "空文本（\"\"）", "纯空格（3个空格）"]):
    lines(headers[0].findall("w:tc", NS)[i], value, bold=True)
groups = OrderedDict()
for row in current["results"]:
    if row["variant"] not in {"empty", "spaces"} or row["status"] == "success":
        continue
    feature, op = row["feature"].rsplit(" ", 1)
    groups.setdefault(feature, {}).setdefault(op, {})[row["variant"]] = row

for feature, operations in groups.items():
    row = deepcopy(row_template)
    cells = row.findall("w:tc", NS)
    methods = []
    for op, variants in operations.items():
        sample = next(iter(variants.values()))
        request = sample["request"]
        methods.append(request["method"] + " /api/v1" + path_template(request["path"]))
    value = feature + "\n" + "/".join(operations) + "\n" + "\n".join(methods)
    lines(cells[0], value, size=17)
    fields = next(iter(next(iter(operations.values())).values()))["fields"]
    lines(cells[1], "\n".join(fields), size=18)
    for variant, col in [("empty", 2), ("spaces", 4)]:
        records = [(op, variants[variant]) for op, variants in operations.items() if variant in variants]
        if not records:
            lines(cells[col], "该项校验通过，见执行记录。", size=18)
            lines(cells[col + 1], "通过", color="008040")
            continue
        representative = records[0][1]
        assert all(item["assertions"] == representative["assertions"] for _, item in records)
        heading = "\n".join(op + " #" + str(item["record_id"]) for op, item in records)
        body = {f: representative["request"]["body"].get(f) for f in fields}
        details = heading + "\n输入：\n" + json.dumps(body, ensure_ascii=False, indent=2)
        details += "\nHTTP 200 / code 0\n断言：\n" + json.dumps(representative["assertions"], ensure_ascii=False, indent=2)
        lines(cells[col], details, size=17, font="Consolas")
        lines(cells[col + 1], "未通过", size=18, color="C00000")
    for tc in cells:
        tcpr = tc.find("w:tcPr", NS)
        align = tcpr.find("w:vAlign", NS)
        if align is not None:
            align.set(Q("val"), "top")
    new.append(row)

body = main.getparent()
last_section = body.find("w:sectPr", NS)
index = list(body).index(last_section)
old_section = etree.Element(Q("p"))
old_props = etree.SubElement(old_section, Q("pPr"))
old_end = deepcopy(last_section)
etree.SubElement(old_end, Q("type"), {Q("val"): "continuous"})
old_props.append(old_end)
body.insert(index, old_section)
index += 1
title = etree.Element(Q("p"))
pp = etree.SubElement(title, Q("pPr"))
etree.SubElement(pp, Q("pageBreakBefore"))
lines(title, "2026-10-20 手动必填文本补测", size=24, bold=True)
body.insert(index, title)
summary = etree.Element(Q("p"))
run = etree.SubElement(summary, Q("r"))
etree.SubElement(run, Q("t")).text = (
    "23项操作，91条必填校验：54通过、37未通过；另27条对照、回读及恢复通过。"
    "仅手动必填普通字符串；自动编号、枚举、下拉及特殊格式不参与。员工新增未造账号，编辑姓名已恢复。"
    "下表只列异常，新增/编辑结论一致时合并；记录号均可在autotest核对。")
body.insert(index + 1, summary)
body.insert(index + 2, new)
ending = etree.Element(Q("p"))
run = etree.SubElement(ending, Q("r"))
etree.SubElement(run, Q("t")).text = "完整请求、返回及断言保存在项目知识 #20982；更新日志 content 回读记录 #20979、#20980、#20981。"
body.insert(index + 3, ending)
last_section.find("w:pgMar", NS).set(Q("left"), "720")
last_section.find("w:pgMar", NS).set(Q("right"), "720")
last_section.find("w:pgMar", NS).set(Q("top"), "640")
last_section.find("w:pgMar", NS).set(Q("bottom"), "640")

content_types = etree.Element("{" + CT + "}Types", nsmap={None: CT})
with ZipFile(WORK / "api-required-layout.docx", "w", ZIP_DEFLATED) as out:
    for part in root.findall("pkg:part", NS):
        name, kind = part.get("{" + PKG + "}name"), part.get("{" + PKG + "}contentType")
        etree.SubElement(content_types, "{" + CT + "}Override", PartName=name, ContentType=kind)
        xml = part.find("pkg:xmlData", NS)
        data = etree.tostring(xml[0], encoding="UTF-8", xml_declaration=True, standalone=True) if xml is not None else base64.b64decode(part.find("pkg:binaryData", NS).text)
        out.writestr(name.lstrip("/"), data)
    out.writestr("[Content_Types].xml", etree.tostring(content_types, encoding="UTF-8", xml_declaration=True, standalone=True))
(WORK / "api-path-updates.json").write_text(json.dumps(updates, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"updated_function_cells": len(updates), "new_abnormal_groups": len(groups)}, ensure_ascii=False))
