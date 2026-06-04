import sys
sys.path.insert(0, '.')
from app.core.database import get_db_conn, release_db_conn

conn = get_db_conn()
with conn.cursor() as cur:
    cur.execute("UPDATE ingestion_jobs SET status='UPLOADED', progress=0, error=NULL, updated_at=NOW() WHERE status='EXTRACTING'")
    print('Rows reset:', cur.rowcount)
conn.commit()
release_db_conn(conn)
print("Done. Refresh the dashboard and retry the files.")
