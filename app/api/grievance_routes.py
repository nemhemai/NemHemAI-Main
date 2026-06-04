from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List, Optional
import uuid
import os
import logging
from datetime import datetime

from app.core.database import get_db_conn, release_db_conn
from app.authentication.dependencies import get_current_user
from app.ingestion_orchestrator.pipeline_executor import start_pipeline_async
from app.generation.draft_generator import generate_draft_response

router = APIRouter()
logger = logging.getLogger(__name__)

def process_ai_draft_background(ticket_id: str, citizen_id: str, category: str, description: str):
    """Background task to generate and save AI draft response."""
    try:
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
                        intent = %s
                    WHERE id = %s
                """, (
                    result["draft_response"], 
                    result["openhuman"]["urgency"], 
                    result["openhuman"]["tone"], 
                    result["openhuman"]["intent"], 
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
    description: str = Form(...),
    
    # Optional Fields
    priority: str = Form("MEDIUM"),
    attachments: Optional[List[UploadFile]] = File(None),
    
    # Auth
    user: dict = Depends(get_current_user)
):
    """
    Intake endpoint for Grievance Agent.
    Saves grievance to Postgres and triggers background OCR pipeline for any attachments.
    """
    conn = get_db_conn()
    ticket_id = str(uuid.uuid4())
    citizen_id = str(user.get("user_id", "anonymous"))
    
    try:
        # 1. Save Grievance to Postgres
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO grievances (id, citizen_id, category, description, status, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (ticket_id, citizen_id, category, description, "OPEN", priority))
        
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
