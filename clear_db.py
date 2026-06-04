import psycopg2
from app.core.config import settings

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
    print("Terminating other connections...")
    cur.execute(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{settings.DB_NAME}' AND pid != pg_backend_pid();")
    print("Truncating tables...")
    cur.execute('TRUNCATE documents CASCADE;')
    cur.execute('TRUNCATE ingestion_jobs CASCADE;')
    print('Successfully truncated documents table and all related records (chunks, elements, embeddings).')
except Exception as e:
    print(f'Error: {e}')
finally:
    cur.close()
    conn.close()
