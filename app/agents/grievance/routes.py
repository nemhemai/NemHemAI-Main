from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
import json
import logging
import glob
from datetime import datetime
from fastapi.responses import FileResponse
from PIL import Image
import pytesseract

from app.core.database import get_db_conn, release_db_conn
from app.authentication.dependencies import get_optional_user
from app.core.ocr_config import OCRConfig
from app.ingestion_orchestrator.pipeline_executor import start_pipeline_async
from app.generation.draft_generator import generate_draft_response

router = APIRouter()
logger = logging.getLogger(__name__)

def process_ai_draft_background(ticket_id: str, citizen_id: str, category: str, description: str):
    """Background task to generate and save AI draft response."""
    try:
        # Check if an image was attached and extract text via OCR
        try:
            files = glob.glob(f"storage/{ticket_id}_*")
            if files:
                file_path = files[0]
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    OCRConfig.configure()
                    img = Image.open(file_path)
                    ocr_text = pytesseract.image_to_string(img, lang=OCRConfig.OCR_LANGUAGES).strip()
                    if ocr_text:
                        description += f"\n\n[Text OCR'd from Attached Image]:\n{ocr_text}"
                        logger.info(f"Successfully extracted OCR text from image for ticket {ticket_id}")
        except Exception as ocr_e:
            logger.error(f"Failed to extract OCR from image for ticket {ticket_id}: {ocr_e}")

        result = generate_draft_response(citizen_id, category, description)
        
        # Save back to Postgres
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE grievances 
                    SET ai_draft_response = %s,
                        urgency = %s,
                        tone = %s,
                        intent = %s,
                        severity_score = %s,
                        retrieved_context = %s,
                        description = %s
                    WHERE id = %s
                """, (
                    result["draft_response"], 
                    result["openhuman"]["urgency"], 
                    result["openhuman"]["tone"], 
                    result["openhuman"]["intent"],
                    result["openhuman"].get("severity_score", 5),
                    json.dumps(result.get("retrieved_context", [])),
                    description,
                    ticket_id
                ))
            conn.commit()
            logger.info(f"AI draft response saved for ticket {ticket_id}")
        except Exception as db_e:
            conn.rollback()
            logger.error(f"Failed to save AI response to DB for ticket {ticket_id}: {db_e}")
        finally:
            release_db_conn(conn)
            
    except Exception as e:
        logger.error(f"Background AI drafting failed for ticket {ticket_id}: {e}")

@router.post("/")
async def create_grievance(
    background_tasks: BackgroundTasks,
    # Required Fields
    category: str = Form(...),
    description: str = Form(""),
    
    # Optional Fields
    attachments: Optional[List[UploadFile]] = File(None),
    
    # Auth
    user: dict = Depends(get_optional_user)
):
    """
    Intake endpoint for Grievance Agent.
    Saves grievance to Postgres and triggers background OCR pipeline for any attachments.
    """
    conn = get_db_conn()
    ticket_id = str(uuid.uuid4())
    citizen_id = str(user.get("user_id", "anonymous")) if user else "anonymous"
    
    try:
        # 1. Save Grievance to Postgres
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO grievances (id, citizen_id, category, description, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticket_id, citizen_id, category, description, "OPEN"))
        
        # 2. Process Attachments via existing Ingestion Pipeline
        if attachments and len(attachments) > 0 and attachments[0].filename:
            os.makedirs("storage", exist_ok=True)
            for file in attachments:
                if not file.filename:
                    continue
                
                # Save attachment locally
                safe_filename = f"{ticket_id}_{os.path.basename(file.filename)}"
                file_path = os.path.join("storage", safe_filename)
                
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                    
                # Create Metadata for the attachment
                metadata = {
                    "title": f"Grievance Attachment - {safe_filename}",
                    "document_type": "grievance_attachment",
                    "user_id": citizen_id,
                    "grievance_id": ticket_id,
                    "job_id": str(uuid.uuid4()) # each attachment gets a job_id for the pipeline
                }
                
                # Trigger the existing Celery Pipeline!
                start_pipeline_async(metadata["job_id"], file_path, metadata)

        conn.commit()
        
        # 3. Trigger Day 4 LLM Generation Pipeline in the Background
        background_tasks.add_task(process_ai_draft_background, ticket_id, citizen_id, category, description)
        
        return {
            "message": "Grievance submitted successfully.",
            "ticket_id": ticket_id
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit grievance: {str(e)}")
    finally:
        release_db_conn(conn)


@router.get("/")
async def get_grievances():
    """
    Fetch all grievances for the official dashboard.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, citizen_id, category, description, status, priority,
                       ai_draft_response, urgency, tone, intent, created_at,
                       severity_score, retrieved_context, official_response
                FROM grievances
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            
            grievances = []
            for row in rows:
                ticket_id_str = str(row[0])
                has_image = len(glob.glob(f"storage/{ticket_id_str}_*")) > 0
                
                grievances.append({
                    "id": ticket_id_str,
                    "citizen_id": row[1],
                    "category": row[2],
                    "description": row[3],
                    "status": row[4],
                    "priority": row[5],
                    "ai_draft_response": row[6],
                    "urgency": row[7],
                    "tone": row[8],
                    "intent": row[9],
                    "created_at": row[10].isoformat() if row[10] else None,
                    "severity_score": row[11],
                    "retrieved_context": row[12] if row[12] else [],
                    "official_response": row[13] if len(row) > 13 else None,
                    "has_image": has_image
                })
            return grievances
    except Exception as e:
        logger.error(f"Failed to fetch grievances: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch grievances")
    finally:
        release_db_conn(conn)


@router.get("/{ticket_id}")
async def get_grievance(ticket_id: str):
    """
    Fetch a single grievance by its ID (for the citizen tracking portal).
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, category, description, status, official_response, created_at
                FROM grievances
                WHERE id = %s
            """, (ticket_id,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Grievance not found. Please check your Ticket ID.")
                
            return {
                "id": str(row[0]),
                "category": row[1],
                "description": row[2],
                "status": row[3],
                "official_response": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch grievance {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch grievance")
    finally:
        release_db_conn(conn)


class ApprovePayload(BaseModel):
    official_response: str

@router.put("/{ticket_id}/approve")
async def approve_grievance(ticket_id: str, payload: ApprovePayload):
    """
    Mark a grievance response as approved by a human official.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE grievances 
                SET status = 'APPROVED', official_response = %s
                WHERE id = %s
            """, (payload.official_response, ticket_id))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Grievance not found")
        conn.commit()
        return {"message": "Grievance response approved successfully."}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to approve grievance: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve grievance")
    finally:
        release_db_conn(conn)

@router.get("/{ticket_id}/image")
async def get_grievance_image(ticket_id: str):
    """
    Serve the uploaded attachment image for a grievance.
    """
    files = glob.glob(f"storage/{ticket_id}_*")
    if not files:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(files[0])
