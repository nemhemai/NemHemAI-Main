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
    # Set a sensible response for the streetlights grievance
    good_draft = "Dear Citizen, we have received your grievance regarding the dead streetlights in Lane 7, Vasant Vihar. We understand this is a major safety issue and have escalated this to the local electricity board for immediate repair. We will update you once power is restored."
    
    cur.execute("""
        UPDATE grievances 
        SET ai_draft_response = %s 
        WHERE ai_draft_response ILIKE '%%RailConnect%%';
    """, (good_draft,))
    
    print(f"Updated {cur.rowcount} grievances.")
except Exception as e:
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
