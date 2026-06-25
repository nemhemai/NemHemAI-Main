import os
import glob
import json
import fitz

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.extraction_service import get_extraction_llm

TARGET_DIR = r"d:\NH_RAG\data\chattisgarh docs"

# The schema we want the LLM to fill out
TARGET_SCHEMA = """
{
  "title": "string (The official title of the document)",
  "jurisdiction": "string (e.g. 'Chhattisgarh' or 'Central')",
  "department": "string (e.g. 'Commerce and Industries Department')",
  "effective_date": "string (e.g. '2024-11-01' or '2024' or null)",
  "document_type": "string (e.g. 'Policy', 'Act', 'Notification', 'Rule')"
}
"""

PROMPT = f"""You are a precise document metadata extractor.
Analyze the following text (from the first few pages of a document) and extract the metadata into a JSON object matching this exact schema:
{TARGET_SCHEMA}

Return ONLY valid JSON. Do not include markdown fences (```json).
"""

def extract_first_pages_text(pdf_path, num_pages=2):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for i in range(min(num_pages, len(doc))):
            text += doc[i].get_text() + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def main():
    llm = get_extraction_llm()
    pdf_files = glob.glob(os.path.join(TARGET_DIR, "*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files in {TARGET_DIR}.")
    
    for pdf_path in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        json_path = os.path.join(TARGET_DIR, f"{base_name}.json")
        
        if os.path.exists(json_path):
            print(f"Skipping {base_name}, JSON already exists.")
            continue
            
        print(f"Processing: {base_name}")
        
        # Extract text
        text = extract_first_pages_text(pdf_path, num_pages=3)
        if not text:
            print("  No text found, using fallback metadata.")
            data = {"title": base_name, "jurisdiction": "Chhattisgarh"}
        else:
            # Ask LLM
            messages = [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Filename: {base_name}.pdf\n\nDocument Text:\n{text[:3000]}"}
            ]
            
            try:
                response = llm.create_chat_completion(
                    messages, 
                    temperature=0.1, 
                    max_tokens=1024, 
                    format="json"
                )
                raw_json = response["choices"][0]["message"]["content"].strip()
                if raw_json.startswith("```json"): raw_json = raw_json[7:]
                if raw_json.endswith("```"): raw_json = raw_json[:-3]
                
                data = json.loads(raw_json.strip())
            except Exception as e:
                print(f"  LLM Extraction failed: {e}. Using fallback.")
                data = {
                    "title": base_name,
                    "jurisdiction": "Chhattisgarh",
                    "department": "Government",
                    "document_type": "Policy"
                }
                
        # Write to file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(f"  Saved metadata to {json_path}")

if __name__ == "__main__":
    main()
