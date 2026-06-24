import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_conn, release_db_conn

def check_status():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 'Ingested', COUNT(*) 
                FROM documents;
            """)
            doc_status = cur.fetchall()
            
            print("=== Document Status ===")
            if not doc_status:
                print("No documents found in the database.")
            for row in doc_status:
                print(f"{row[0]}: {row[1]}")
                
            print("\n=== Ingestion Jobs ===")
            cur.execute("""
                SELECT status, COUNT(*) 
                FROM ingestion_jobs 
                GROUP BY status;
            """)
            job_status = cur.fetchall()
            if not job_status:
                print("No ingestion jobs found.")
            for row in job_status:
                print(f"{row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"Error checking status: {e}")
    finally:
        release_db_conn(conn)

if __name__ == "__main__":
    check_status()
