import sys
sys.path.insert(0, '.')
from app.core.database import get_db_conn, release_db_conn
import json

conn = get_db_conn()
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, citizen_id, category, description, status,
                   ai_draft_response, urgency, tone, intent, created_at,
                   severity_score
            FROM grievances
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        for row in rows:
            print("====================================")
            print("ID:", row[0])
            print("Citizen ID:", row[1])
            print("Category:", row[2])
            print("Description:", row[3])
            print("Status:", row[4])
            print("AI Draft:", row[5])
            print("Urgency:", row[6])
            print("Tone:", row[7])
            print("Intent:", row[8])
            print("Created At:", row[9])
            print("Severity Score:", row[10])
finally:
    release_db_conn(conn)
