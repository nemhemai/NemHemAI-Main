import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional

from app.authentication.dependencies import get_current_user
from app.services.extraction_service import enforce_page_limit, parse_document_to_markdown, run_extraction_agent

router = APIRouter()

@router.post("/extract/document")
async def extract_document_data(
    file: UploadFile = File(...),
    target_schema: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """
    Extract structured data (JSON) from an uploaded document.
    Enforces a 5-page limit for PDFs to prevent LLM context overflow.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # 1. Save file temporarily
    os.makedirs("storage/temp_extraction", exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join("storage/temp_extraction", temp_filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    try:
        # 2. Enforce limits and parse
        limited_path = enforce_page_limit(file_path, max_pages=5)
        markdown_text = parse_document_to_markdown(limited_path)
        
        if not markdown_text or not markdown_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from document.")
            
        # 3. Ask LLM to extract JSON
        extracted_data = run_extraction_agent(markdown_text, target_schema)
        
        # If it returned an error dictionary, pass it up
        if "error" in extracted_data:
            raise HTTPException(status_code=500, detail=extracted_data["error"])
            
        return {
            "status": "success",
            "extracted_data": extracted_data
        }
        
    finally:
        # Cleanup temp files
        if os.path.exists(file_path):
            os.remove(file_path)
        if 'limited_path' in locals() and limited_path != file_path and os.path.exists(limited_path):
            os.remove(limited_path)
