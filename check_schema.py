from app.core.database import get_db_conn, release_db_conn
conn = get_db_conn()
with conn.cursor() as cur:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'document_chunks';")
    print('document_chunks columns:', cur.fetchall())
release_db_conn(conn)
