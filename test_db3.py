from app.core.database import get_db_conn
conn = get_db_conn()
cur = conn.cursor()
cur.execute("SELECT c.text, c.fts_tokens FROM document_chunks c JOIN documents d ON c.document_id = d.document_id WHERE d.metadata->>'scheme_name' = 'PM SVANidhi' LIMIT 2;")
rows = cur.fetchall()
for r in rows:
    print("TEXT:", r[0][:200])
    print("FTS_TOKENS:", str(r[1])[:200])
