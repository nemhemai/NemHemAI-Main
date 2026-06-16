import os
import sys
import uuid
import json
import argparse
from pathlib import Path
import psycopg2

# 1. Resolve imports from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file using dotenv if possible
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from app.core.database import get_db_conn, release_db_conn
from app.ingestion_orchestrator.ingestion_orchestrator import run_full_pipeline

def get_or_create_system_user(conn):
    """
    Ensure at least one user exists in the database to satisfy foreign key constraints.
    Returns (user_id, username).
    """
    with conn.cursor() as cur:
        # Check if any user exists
        cur.execute("SELECT user_id, username FROM users LIMIT 1;")
        row = cur.fetchone()
        if row:
            return str(row[0]), row[1]
        
        # If no user exists, create a default system CLI user
        system_user_id = str(uuid.uuid4())
        system_username = "system_cli"
        dummy_hash = "dummy_password_hash_not_for_auth"
        
        cur.execute("""
            INSERT INTO users (
                user_id,
                username,
                password_hash,
                role,
                full_name,
                email
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            system_user_id,
            system_username,
            dummy_hash,
            "admin",
            "System CLI",
            "system_cli@gov.in"
        ))
        conn.commit()
        print(f"Created system user: {system_username} ({system_user_id})")
        return system_user_id, system_username

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI Document Ingestion tool for Entitlement Agent")
    parser.add_argument(
        "--file", 
        type=str, 
        help="Path to a specific PDF file to ingest."
    )
    parser.add_argument(
        "--dir", 
        type=str, 
        default=str(PROJECT_ROOT / "data" / "entitlement"),
        help="Path to a directory containing PDF files and optional JSON metadata files."
    )
    args = parser.parse_args()

    conn = get_db_conn()
    try:
        user_id, username = get_or_create_system_user(conn)
    except Exception as e:
        print(f"Error ensuring system user exists in DB: {e}")
        release_db_conn(conn)
        sys.exit(1)
    finally:
        release_db_conn(conn)

    # Resolve PDF file paths
    pdf_files = []
    if args.file:
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        if file_path.suffix.lower() != ".pdf":
            print(f"Error: File must be a PDF: {file_path}")
            sys.exit(1)
        pdf_files.append(file_path)
    else:
        dir_path = Path(args.dir).resolve()
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"Error: Directory not found: {dir_path}")
            sys.exit(1)
        
        # Find all PDF files
        pdf_files = list(dir_path.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files in directory: {dir_path}")

    if not pdf_files:
        print("No PDF files found to ingest.")
        sys.exit(0)

    for pdf_path in pdf_files:
        print("\n" + "="*80)
        print(f"Processing PDF: {pdf_path.name}")
        print("="*80)
        
        # 1. Load metadata if JSON exists
        metadata = {}
        json_path = pdf_path.with_suffix(".json")
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                print(f"Loaded metadata from: {json_path.name}")
            except Exception as e:
                print(f"Warning: Failed to load metadata JSON: {e}")
        
        # 2. Fill defaults for missing metadata keys
        defaults = {
            "title": pdf_path.stem.replace("_", " ").replace("-", " "),
            "document_number": f"CLI-INGEST-{pdf_path.stem[:20].upper()}",
            "issuing_authority": "Government",
            "jurisdiction": "central",
            "document_type": "guideline",
            "primary_language": "en",
            "security_level": "public",
            "version_label": "1.0"
        }
        for k, v in defaults.items():
            if k not in metadata or metadata[k] is None:
                metadata[k] = v
        
        # 3. Add system/job context
        job_id = str(uuid.uuid4())
        metadata["user_id"] = user_id
        metadata["uploaded_by"] = username
        metadata["job_id"] = job_id
        
        # 4. Insert job tracking row in ingestion_jobs to avoid constraints error
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ingestion_jobs (job_id, file_name, status)
                    VALUES (%s, %s, %s)
                """, (job_id, pdf_path.name, "UPLOADED"))
            conn.commit()
        except Exception as e:
            print(f"Failed to insert ingestion job record: {e}")
            release_db_conn(conn)
            continue
        finally:
            release_db_conn(conn)
            
        # 5. Run full pipeline (registers doc, chunking, embedding, etc.)
        try:
            print(f"Starting ingestion pipeline with Job ID: {job_id}")
            run_full_pipeline(job_id, str(pdf_path), metadata)
            
            # Check final job status
            conn = get_db_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT status, error FROM ingestion_jobs WHERE job_id = %s;", (job_id,))
                    row = cur.fetchone()
                    if row:
                        status, err = row
                        if status == "COMPLETED":
                            print(f"Successfully ingested {pdf_path.name}!")
                        else:
                            print(f"Ingestion finished with status: {status}. Error: {err}")
                    else:
                        print("Failed to check final job status: Job record not found.")
            finally:
                release_db_conn(conn)
                
        except Exception as e:
            print(f"Pipeline execution crashed for {pdf_path.name}: {e}")

if __name__ == "__main__":
    main()
