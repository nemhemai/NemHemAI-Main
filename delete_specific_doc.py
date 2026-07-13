
import psycopg2
from app.core.config import settings

def delete_pm_awas():
    print("Connecting to database...")
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    try:
        doc_name = 'Operational-Guidelines-of-PMAY-U-2.pdf'
        
        # Check if it exists, order by ID to delete older ones
        cur.execute("SELECT document_id, file_name FROM documents WHERE file_name = %s ORDER BY document_id", (doc_name,))
        rows = cur.fetchall()
        
        if len(rows) > 1:
            # We have duplicates, keep the newest (last) one, delete others
            for row in rows[:-1]: # All except the last one
                doc_id = row[0]
                print(f"Found older duplicate document: {row[1]} (ID: {doc_id})")
                
                print(f"Deleting document ID {doc_id} and its associated chunks to prevent duplicate retrieval...")
                cur.execute("DELETE FROM documents WHERE document_id = %s", (doc_id,))
                print(f"Successfully deleted duplicate!")
        else:
            print(f"No duplicates found for {doc_name}.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    delete_pm_awas()
