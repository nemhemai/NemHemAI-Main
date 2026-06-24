import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_conn, release_db_conn

def check_chunks():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM document_chunks;")
            chunks_count = cur.fetchone()[0]
            print(f"Total chunks: {chunks_count}")

            cur.execute("SELECT COUNT(*) FROM document_embeddings;")
            embed_count = cur.fetchone()[0]
            print(f"Total embeddings: {embed_count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        release_db_conn(conn)

if __name__ == "__main__":
    check_chunks()
