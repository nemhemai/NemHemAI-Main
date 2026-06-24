import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_conn, release_db_conn

def check_documents():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT file_name FROM documents;")
            rows = cur.fetchall()
            print(f"Total documents in DB: {len(rows)}")
            for row in rows:
                print(f"- {row[0]} (Status: {row[1]})")
    except Exception as e:
        print(f"Error checking db: {e}")
    finally:
        release_db_conn(conn)

if __name__ == "__main__":
    check_documents()
