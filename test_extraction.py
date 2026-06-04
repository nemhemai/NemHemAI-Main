import os
import json
import asyncio
from app.services.extraction_service import parse_document_to_markdown, run_extraction_agent

def run_test():
    test_file = "test_extract.txt"
    with open(test_file, "w") as f:
        f.write("Title: Aaple Sarkar DBT Portal User Guidelines and Help File\n"
                "Document Number: MAHA-DBT-GUIDE-2025\n"
                "Issuing Authority: Government of Maharashtra\n"
                "Department: MAHA-IT\n"
                "Jurisdiction: state\n"
                "State Origin: Maharashtra\n"
                "Type: manual\n"
                "Security Level: public\n"
                "Language: en\n"
                "Version Label: 2024-25\n"
                "---\n"
                "Invoice #12345\nDate: 2023-01-15\nVendor: Acme Corp\nTotal: $150.00\nItems:\n- Widget A, 2, $50.00\n- Widget B, 1, $50.00")
        
    print("Extracting markdown...")
    md = parse_document_to_markdown(test_file)
    print("Markdown:", md)
    
    schema = '''{
  "document_metadata": {
    "title": "string",
    "document_number": "string",
    "issuing_authority": "string",
    "department_code": "string",
    "jurisdiction": "string",
    "state_origin": "string",
    "document_type": "string",
    "security_level": "string",
    "primary_language": "string",
    "version_label": "string"
  },
  "invoice": {
    "invoice_id": "string",
    "date": "string",
    "vendor": "string",
    "total": "number",
    "items": [{"name": "string", "quantity": "number", "price": "number"}]
  }
}'''
    print("Extracting JSON...")
    res = run_extraction_agent(md, schema)
    
    print("Result:", json.dumps(res, indent=2))
    
    os.remove(test_file)

if __name__ == "__main__":
    run_test()
