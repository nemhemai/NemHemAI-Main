import psycopg2
from app.core.config import settings

conn = psycopg2.connect(
    dbname=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASS,
    host=settings.DB_HOST,
    port=settings.DB_PORT
)
cur = conn.cursor()
try:
    cur.execute("SELECT text FROM document_chunks WHERE text ILIKE '%RailConnect%';")
    results = cur.fetchall()
    print(f"Found {len(results)} chunks mentioning RailConnect.")
    for row in results:
        print(row[0][:200])
except Exception as e:
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
