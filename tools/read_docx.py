"""Print DOCX paragraphs and tables in document order using the Python standard library."""

import sys
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")


NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def text_of(element):
    return "".join(node.text or "" for node in element.iter(NS + "t")).strip()


with zipfile.ZipFile(sys.argv[1]) as archive:
    root = ET.fromstring(archive.read("word/document.xml"))

body = root.find(NS + "body")
for child in body:
    if child.tag == NS + "p":
        line = text_of(child)
        if line:
            print(line)
    elif child.tag == NS + "tbl":
        print("[TABLE]")
        for row in child.findall(NS + "tr"):
            cells = [text_of(cell) for cell in row.findall(NS + "tc")]
            print(" | ".join(cells))
        print("[/TABLE]")
