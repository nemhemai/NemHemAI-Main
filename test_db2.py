from app.core.database import get_db_conn
conn = get_db_conn()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM document_chunks c JOIN documents d ON c.document_id = d.document_id WHERE d.metadata->>'agent_domain' = 'entitlement';")
print('Entitlement Chunks:', cur.fetchone()[0])

cur.execute("SELECT status FROM ingestion_jobs ORDER BY created_at DESC LIMIT 8;")
print('Recent job statuses:')
[print(r) for r in cur.fetchall()]
