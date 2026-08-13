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
    cur.execute("SELECT COUNT(*) FROM grievances;")
    count = cur.fetchone()[0]
    print(f"Total grievances: {count}")
except Exception as e:
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
