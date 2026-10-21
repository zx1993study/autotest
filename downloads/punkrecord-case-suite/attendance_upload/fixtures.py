"""Prepare document fixtures without changing the supplied Word document."""
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HERE = Path(__file__).resolve().parent


def change_member(content, name, present):
    source = zipfile.ZipFile(io.BytesIO(content))
    document = ET.fromstring(source.read("word/document.xml"))
    for parent in document.iter():
        for paragraph in list(parent):
            if paragraph.tag == WORD + "p":
                text = "".join(paragraph.itertext())
                if text.strip().startswith((name + ":", name + "：")):
                    parent.remove(paragraph)
    if present:
        body = document.find(WORD + "body")
        paragraph = ET.Element(WORD + "p")
        run = ET.SubElement(paragraph, WORD + "r")
        ET.SubElement(run, WORD + "t").text = name + ": morning meeting attendance test"
        body.insert(0, paragraph)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            target.writestr(item, ET.tostring(document, encoding="utf-8", xml_declaration=True)
                            if item.filename == "word/document.xml" else source.read(item.filename))
    return output.getvalue()


def speakers(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    names = []
    for paragraph in document.iter(WORD + "p"):
        text = "".join(node.text or "" for node in paragraph.iter(WORD + "t")).strip()
        name = text.replace("：", ":").partition(":")[0]
        if ":" in text.replace("：", ":") and name and name not in names:
            names.append(name)
    return names
