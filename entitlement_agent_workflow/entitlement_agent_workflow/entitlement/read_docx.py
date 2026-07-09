import zipfile
import xml.etree.ElementTree as ET

def extract_text(docx_filename):
    with zipfile.ZipFile(docx_filename) as zf:
        xml_content = zf.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for paragraph in tree.findall('.//w:p', namespace):
            texts = [node.text for node in paragraph.findall('.//w:t', namespace) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
        return '\n'.join(paragraphs)

with open('plan.txt', 'w', encoding='utf-8') as f:
    f.write(extract_text("Entitlement_Agent_7Day_Plan.docx"))
