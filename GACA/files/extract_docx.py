import zipfile
import xml.etree.ElementTree as ET
import sys

sys.stdout.reconfigure(encoding='utf-8')

z = zipfile.ZipFile('Governance, Audit & Compliance Agent.docx')
root = ET.fromstring(z.read('word/document.xml'))
ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

paragraphs = []
for p in root.iter(f'{{{ns}}}p'):
    texts = []
    for t in p.iter(f'{{{ns}}}t'):
        if t.text:
            texts.append(t.text)
    line = ''.join(texts)
    if line.strip():
        paragraphs.append(line)

with open('gaca_spec.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(paragraphs))

print(f"Extracted {len(paragraphs)} paragraphs to gaca_spec.txt")
