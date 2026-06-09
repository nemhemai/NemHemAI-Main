from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
import json

def backfill():
    conn = get_db_conn()
    retriever = HybridRetriever()
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, category, description FROM grievances WHERE status = 'OPEN'")
            rows = cur.fetchall()
            
            for row in rows:
                ticket_id, cat, desc = row
                query = f"{cat} {desc}"
                print(f"Retrieving context for {ticket_id}...")
                try:
                    results = retriever.retrieve(conn, query, top_k=3)
                    if results:
                        cur.execute("""
                            UPDATE grievances 
                            SET retrieved_context = %s 
                            WHERE id = %s
                        """, (json.dumps(results), ticket_id))
                        print(f"Updated {ticket_id} with {len(results)} contexts.")
                    else:
                        print(f"No context found for {ticket_id}.")
                    # Commit per successful row to save progress
                    conn.commit()
                except Exception as row_e:
                    conn.rollback()
                    print(f"Error processing {ticket_id}: {row_e}")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        release_db_conn(conn)

if __name__ == "__main__":
    backfill()
