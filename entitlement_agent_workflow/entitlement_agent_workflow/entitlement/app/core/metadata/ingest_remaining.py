import os
import sys
import uuid
import json
from pathlib import Path

# Configure stdout to use UTF-8 to handle emojis and special characters in print statements
sys.stdout.reconfigure(encoding='utf-8')

# Load .env file using dotenv if possible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.core.database import get_db_conn, release_db_conn

# run_full_pipeline is loaded optionally in standalone mode
try:
    from app.ingestion_orchestrator.ingestion_orchestrator import run_full_pipeline
except ImportError:
    run_full_pipeline = None


def get_or_create_system_user(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, username FROM users LIMIT 1;")
        row = cur.fetchone()
        if row:
            return str(row[0]), row[1]
        
        system_user_id = str(uuid.uuid4())
        system_username = "system_cli"
        dummy_hash = "dummy_password_hash_not_for_auth"
        
        cur.execute("""
            INSERT INTO users (user_id, username, password_hash, role, full_name, email)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (system_user_id, system_username, dummy_hash, "admin", "System CLI", "system_cli@gov.in"))
        conn.commit()
        return system_user_id, system_username


def get_already_ingested_files(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT file_name FROM documents")
        rows = cur.fetchall()
        return {r[0] for r in rows}


def ingest_file(pdf_path: Path, user_id: str, username: str) -> bool:
    print(f"\nIngesting: {pdf_path.name}")
    
    # Load metadata if JSON exists
    metadata = {}
    json_path = pdf_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            print(f"Loaded metadata from: {json_path.name}")
        except Exception as e:
            print(f"Warning: Failed to load metadata JSON: {e}")
            
    # Fill defaults for missing metadata keys
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
            
    job_id = str(uuid.uuid4())
    metadata["user_id"] = user_id
    metadata["uploaded_by"] = username
    metadata["job_id"] = job_id
    
    # Insert job tracking row in ingestion_jobs to avoid constraints error
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
        return False
    finally:
        release_db_conn(conn)
        
    # Run pipeline
    try:
        print(f"Starting pipeline for Job ID: {job_id}")
        run_full_pipeline(job_id, str(pdf_path), metadata)
        
        # Check status
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status, error FROM ingestion_jobs WHERE job_id = %s;", (job_id,))
                row = cur.fetchone()
                if row:
                    status, err = row
                    if status == "COMPLETED":
                        print(f"Successfully ingested {pdf_path.name}!")
                        return True
                    else:
                        print(f"Ingestion finished with status: {status}. Error: {err}")
                        return False
        finally:
            release_db_conn(conn)
    except Exception as e:
        print(f"Pipeline crashed for {pdf_path.name}: {e}")
        return False


def main():
    entitlement_dir = Path(__file__).resolve().parents[3] / "data" / "entitlement"
    if not entitlement_dir.exists():
        print(f"Directory not found: {entitlement_dir}")
        sys.exit(1)
        
    pdf_files = list(entitlement_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in guidelines directory.")

    conn = get_db_conn()
    try:
        user_id, username = get_or_create_system_user(conn)
        ingested_files = get_already_ingested_files(conn)
    except Exception as e:
        print(f"Failed database setup: {e}")
        sys.exit(1)
    finally:
        release_db_conn(conn)

    print(f"Currently ingested files in database: {len(ingested_files)}")
    
    to_ingest = []
    for pdf_file in pdf_files:
        # Skip OCR file or other specific duplicates if needed, but here we ingest it if missing
        if pdf_file.name in ingested_files:
            print(f"Already ingested (skipping): {pdf_file.name}")
        else:
            to_ingest.append(pdf_file)
            
    print(f"Identified {len(to_ingest)} files to ingest.")
    
    success_count = 0
    for pdf_file in to_ingest:
        success = ingest_file(pdf_file, user_id, username)
        if success:
            success_count += 1
            
    print(f"\nCompleted! Ingested {success_count}/{len(to_ingest)} files successfully.")


if __name__ == "__main__":
    main()
