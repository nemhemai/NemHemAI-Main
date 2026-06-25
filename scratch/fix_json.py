import os
import glob
import json

TARGET_DIR = r"d:\NH_RAG\data\chattisgarh docs"

def main():
    for f in glob.glob(os.path.join(TARGET_DIR, "*.json")):
        with open(f, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
            except Exception as e:
                print(f"Skipping {f}, not valid JSON")
                continue
                
        # Safely get string values or fallbacks
        title = data.get('title') or os.path.basename(f)
        dept = data.get('department') or 'CG-GOV'
        if not isinstance(dept, str): dept = 'CG-GOV'
        
        doc_type = data.get('document_type') or 'policy'
        if not isinstance(doc_type, str): doc_type = 'policy'
        
        version = data.get('effective_date') or '2024'
        if not isinstance(version, str): version = '2024'
        
        new_data = {
            "title": title,
            "document_number": "CG-DOC-2024",
            "issuing_authority": "Government of Chhattisgarh",
            "department_code": dept[:50],
            "jurisdiction": "state",
            "state_origin": "Chhattisgarh",
            "document_type": doc_type.lower()[:20],
            "security_level": "public",
            "primary_language": "en",
            "version_label": version[:20]
        }
        
        with open(f, 'w', encoding='utf-8') as out_file:
            json.dump(new_data, out_file, indent=2)
            
    print("Successfully reformatted all JSON files.")

if __name__ == "__main__":
    main()
