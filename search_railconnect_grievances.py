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
    cur.execute("SELECT description, ai_draft_response FROM grievances WHERE description ILIKE '%RailConnect%' OR ai_draft_response ILIKE '%RailConnect%';")
    results = cur.fetchall()
    print(f"Found {len(results)} grievances mentioning RailConnect.")
    for row in results:
        print(f"Description: {row[0][:100]}... Draft: {row[1][:100]}...")
except Exception as e:
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
