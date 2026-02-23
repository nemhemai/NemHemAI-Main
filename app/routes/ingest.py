from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.extraction import extract_structure
from app.utils.pdf_reader import extract_text_from_pdf

router = APIRouter()

@router.post("/ingest")
async def ingest_pdf(file: UploadFile = File(...)):

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        # Read file
        contents = await file.read()

        # Step 1: Extract raw text from PDF
        raw_text = extract_text_from_pdf(contents)

        if not raw_text:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF.")

        # Step 2: Call structured extraction layer
        structured_data = extract_structure(raw_text)

        # Step 3: Return structured JSON (NO MODIFICATION)
        return {
            "status": "success",
            "data": structured_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))