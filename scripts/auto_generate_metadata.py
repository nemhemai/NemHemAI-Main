import os
import json
import re
from pathlib import Path

# Path to the raw data folder
DATA_RAW_DIR = Path(r"d:\NH_RAG\data\raw")

def generate_title_from_filename(filename: str) -> str:
    """Convert a filename like 'My_Document-File.pdf' to 'My Document File'."""
    name_without_ext = Path(filename).stem
    # Replace underscores and hyphens with spaces
    title = re.sub(r'[-_]', ' ', name_without_ext)
    # Title case it
    return title.title()

def create_default_metadata(pdf_path: Path):
    """Creates a default metadata JSON file for a given PDF."""
    json_path = pdf_path.with_suffix('.json')
    
    if json_path.exists():
        print(f"Skipping {pdf_path.name} - JSON already exists.")
        return

    title = generate_title_from_filename(pdf_path.name)
    
    # Default metadata structure based on existing files in data/raw
    metadata = {
        "title": title,
        "document_number": "UNKNOWN",
        "issuing_authority": "Government of India",
        "department_code": "GENERAL",
        "jurisdiction": "central",
        "state_origin": None,
        "document_type": "manual",
        "security_level": "public",
        "primary_language": "en",
        "version_label": "2024"
    }

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Success: Generated metadata for: {pdf_path.name} -> {json_path.name}")
    except Exception as e:
        print(f"Error: Failed to generate metadata for {pdf_path.name}: {e}")

def main():
    print(f"Scanning {DATA_RAW_DIR} for PDF files without metadata...")
    if not DATA_RAW_DIR.exists():
        print(f"Error: Directory {DATA_RAW_DIR} does not exist.")
        return

    pdf_files = list(DATA_RAW_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the directory.")
        return
        
    count = 0
    for pdf_path in pdf_files:
        json_path = pdf_path.with_suffix('.json')
        if not json_path.exists():
            create_default_metadata(pdf_path)
            count += 1
            
    print(f"\nDone! Generated {count} missing metadata JSON files.")

if __name__ == "__main__":
    main()
