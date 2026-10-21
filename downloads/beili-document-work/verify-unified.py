"""Check evidence retention and reject concurrent edits before publishing."""
from collections import Counter
from pathlib import Path
from lxml import etree
import base64
import hashlib
import json
import re
import sys

work = Path(__file__).parent
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "pkg": "http://schemas.microsoft.com/office/2006/xmlPackage"}
pkg = "{" + ns["pkg"] + "}"
source = etree.parse(str(work / "unify-input-flat.xml"))
target = etree.parse(str(work / (sys.argv[1] if len(sys.argv) > 1 else "unified-final-flat.xml")))
plain = lambda node: "".join(node.xpath(".//w:t/text()", namespaces=ns))

def media(tree):
    return sorted(hashlib.sha256(base64.b64decode(p.find("pkg:binaryData", ns).text)).hexdigest()
                  for p in tree.findall("pkg:part", ns) if p.find("pkg:binaryData", ns) is not None)

def ids(tree):
    return set(re.findall(r"#\s*(\d+)", plain(tree)))

def paragraphs(cell):
    return ["".join((n.text or "") if n.tag.endswith("}t") else "\n" if n.tag.endswith("}br") else ""
                    for n in p.iter()) for p in cell.findall("w:p", ns)]

tables = target.findall(".//w:tbl", ns)
assert len(tables) == 1
rows = tables[0].findall("w:tr", ns)
assert len(rows) == 43
assert all(len(r.findall("w:tc", ns)) == 5 for r in rows)
manifest = json.loads((work / "unified-manifest.json").read_text(encoding="utf-8"))
assert len({(m["feature"], m["point"]) for m in manifest}) == 42
assert len({m["feature"] for m in manifest}) == 16
assert sum(m["evidence_blocks"] for m in manifest) == 52
assert ids(source) == ids(target)
assert media(source) == media(target)
old = Counter()
for table in [source.findall(".//w:tbl", ns)[i] for i in (0, 2)]:
    for row in table.findall("w:tr", ns)[1:]:
        old.update(paragraphs(row.findall("w:tc", ns)[3]))
new = Counter()
for row in rows[1:]:
    new.update(paragraphs(row.findall("w:tc", ns)[3]))
assert all(new[p] >= 1 for p in old if p.strip()), "Missing evidence paragraph"
for size in target.findall(".//w:sectPr/w:pgSz", ns):
    w = int(size.get("{" + ns["w"] + "}w"))
    h = int(size.get("{" + ns["w"] + "}h"))
    assert h > w

if (work / "unify-presave-flat.xml").exists():
    current = etree.parse(str(work / "unify-presave-flat.xml"))
    def parts(tree):
        for node in tree.xpath("//*[local-name()='TotalTime']"):
            node.text = "0"
        return {p.get(pkg + "name"): etree.tostring(p, method="c14n") for p in tree.findall("pkg:part", ns)}
    a, b = parts(source), parts(current)
    changed = [key for key in a.keys() | b.keys() if a.get(key) != b.get(key)]
    assert not changed, "Concurrent changes: " + str(changed)
print(json.dumps({"tables": 1, "columns": 5, "features": 16, "unique_test_points": 42,
                  "evidence_blocks": 52, "record_ids": len(ids(target)), "images": len(media(target)),
                  "portrait": True, "live_source_unchanged": True}))
