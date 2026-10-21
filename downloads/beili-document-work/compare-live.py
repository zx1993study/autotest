from pathlib import Path
from lxml import etree
import difflib
work = Path(__file__).parent
ns = {"pkg": "http://schemas.microsoft.com/office/2006/xmlPackage"}
a = etree.parse(str(work / "unify-input-flat.xml"))
b = etree.parse(str(work / "unify-presave-flat.xml"))
def part(root, name):
    p = next(p for p in root.findall("pkg:part", ns) if p.get("{" + ns["pkg"] + "}name") == name)
    return etree.tostring(p.find("pkg:xmlData", ns)[0], pretty_print=True, encoding="unicode").splitlines()
for name in ["/word/document.xml", "/docProps/app.xml"]:
    print(name)
    print("\n".join(difflib.unified_diff(part(a,name),part(b,name),n=2)))
