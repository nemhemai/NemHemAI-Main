import json
from app.core.database import get_db_conn

conn = get_db_conn()
cur = conn.cursor()
cur.execute("SELECT query_id, determination FROM entitlement_queries WHERE query_id = '1cd48607-d8f0-40a1-898e-ed337ae63a95';")
row = cur.fetchone()
if row:
    qid, det = row
    if isinstance(det, str):
        det = json.loads(det)
    print("Keys:", det.keys())
    schemes = det.get("schemes", [])
    print("Schemes length:", len(schemes))
    if schemes:
        print("First scheme:", list(schemes[0].keys()))
    optimized = det.get("optimized_benefit_plan", [])
    print("Optimized plan:", optimized)
