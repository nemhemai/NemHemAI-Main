from app.core.database import get_db_conn
conn = get_db_conn()
cur = conn.cursor()
cur.execute("UPDATE document_chunks SET fts_tokens = to_tsvector('english', coalesce(text, '')) WHERE fts_tokens IS NULL;")
print('Rows updated:', cur.rowcount)
conn.commit()
