import os
import json
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter
from app.services.ollama_service import OllamaLLM

# Dedicated smaller model for extraction (avoids memory contention with main LLM)
_extraction_llm = None

def get_extraction_llm():
    global _extraction_llm
    if _extraction_llm is None:
        print("Initializing extraction LLM (llama3.2:3b)...")
        _extraction_llm = OllamaLLM(model="llama3.2:3b")
    return _extraction_llm

def enforce_page_limit(file_path: str, max_pages: int = 5) -> str:
    """If the file is a PDF and has more than max_pages, create a truncated version."""
    if not file_path.lower().endswith(".pdf"):
        return file_path

    try:
        doc = fitz.open(file_path)
        if len(doc) <= max_pages:
            doc.close()
            return file_path

        print(f"Truncating PDF {file_path} to {max_pages} pages...")
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=0, to_page=max_pages - 1)
        
        base, ext = os.path.splitext(file_path)
        new_path = f"{base}_truncated{ext}"
        new_doc.save(new_path)
        new_doc.close()
        doc.close()
        
        return new_path
    except Exception as e:
        print(f"Failed to truncate PDF: {e}")
        return file_path


def parse_document_to_markdown(file_path: str) -> str:
    """Use docling to convert document (PDF, DOCX, CSV, etc.) to markdown."""
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_markdown()
    except Exception as e:
        print(f"Docling conversion failed: {e}. Falling back to basic text extraction.")
        
        # Basic fallback for PDFs
        if file_path.lower().endswith(".pdf"):
            try:
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
                return text
            except Exception as e2:
                return f"Error reading PDF: {e2}"
                
        # Basic fallback for TXT
        if file_path.lower().endswith(".txt") or file_path.lower().endswith(".csv"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
                
        return f"Unsupported or unreadable file format. Error: {e}"


def run_extraction_agent(text_content: str, target_schema: str = None) -> dict:
    """Run Llama 3 to extract structured JSON from the markdown text."""
    
    system_prompt = """You are a precise data extraction agent. Your sole job is to convert the provided document text into clean, structured JSON.

## Your Workflow
1. UNDERSTAND the content — identify what entities, fields, and relationships exist.
2. INFER a logical JSON schema that best represents the document's structure.
   - If the user has provided a target schema, use it exactly.
   - If no schema is given, infer the most natural one.
3. EXTRACT all data from the document and map it to the schema.
4. RETURN only the final JSON object or array. No prose, no explanation, no markdown fences.

## Rules
- NEVER hallucinate values. If a field's value is missing or unreadable, use `null`.
- NEVER skip records. Extract every row, entry, or item present.
- Normalize data where obvious: trim whitespace, standardize date formats to ISO 8601 (YYYY-MM-DD), lowercase boolean strings to actual booleans.
- For tabular data (CSV/tables), always produce an array of objects — one object per row.
- For documents with mixed content (text + tables), create a top-level object with named sections.
- Preserve original field names where clear; convert to snake_case if messy.
- DO NOT wrap the output in ```json tags. Just output raw JSON.

"""
    
    if target_schema:
        system_prompt += f"\n## Target Schema\nYou MUST strictly follow this JSON schema:\n{target_schema}\n"
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Document content to extract:\n\n{text_content}"}
    ]
    
    llm = get_extraction_llm()
    
    # We allow up to 2 retries if parsing fails
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # We ask for a massive token output if it's a huge table
            response = llm.create_chat_completion(
                messages, 
                temperature=0.1, 
                max_tokens=4096, 
                format="json"
            )
            
            raw_content = response["choices"][0]["message"]["content"]
            
            # Simple cleanup in case the LLM ignored the "no markdown fences" rule
            raw_content = raw_content.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()
            
            # Verify it's actually valid JSON
            parsed_json = json.loads(raw_content)
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed on attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                return {"error": "Failed to generate valid JSON from document", "raw_output": raw_content}
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return {"error": f"LLM error: {str(e)}"}
            
    return {"error": "Failed after max retries."}
