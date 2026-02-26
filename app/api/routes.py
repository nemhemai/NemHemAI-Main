from fastapi import APIRouter, UploadFile, File, HTTPException
from app.ingest.persistence_service import persist_to_graph
from app.services.extraction import extract_structure
from app.utils.pdf_reader import extract_text_from_pdf

router = APIRouter()


@router.post("/ingest")
async def ingest_pdf(file: UploadFile = File(...)):

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    try:
        # Step 1: Read file
        contents = await file.read()

        # Step 2: Extract raw text
        raw_text = extract_text_from_pdf(contents)

        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in PDF."
            )

        # Step 3: Structured extraction
        structured_json = extract_structure(raw_text)

        # Step 4: Persist to graph
        ingestion_summary = persist_to_graph(structured_json)

        return {
            "status": "success",
            "data": structured_json,
            "ingestion_summary": ingestion_summary
        }

    except ValueError as ve:
        # Validation errors from persistence_service
        raise HTTPException(status_code=400, detail=str(ve))

    except HTTPException:
        # Re-raise known HTTP errors
        raise

    except Exception as e:
        # Unexpected system failure
        raise HTTPException(
            status_code=500,
            detail="Internal server error during ingestion."
        )