import time
from app.core.database import get_db_conn
from app.agents.entitlement.services.entitlement_service import update_llm_explanation_async
import traceback
import logging
import sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

conn = get_db_conn()
cur = conn.cursor()
cur.execute("SELECT query_id, citizen_id, raw_query, extracted_profile, status, determination FROM entitlement_queries WHERE determination IS NOT NULL LIMIT 1")
row = cur.fetchone()
if row:
    query_id, citizen_id, raw_query, profile, status, det = row
    if 'explanation' in det:
        del det['explanation']
    import json
    cur.execute("UPDATE entitlement_queries SET determination = %s WHERE query_id = %s", (json.dumps(det), query_id))
    conn.commit()
    print(f'Testing with query_id {query_id}')
    start = time.time()
    try:
        update_llm_explanation_async(
            query_id, citizen_id, raw_query, profile,
            det.get('decision_status', 'ELIGIBLE'), det.get('schemes', []), det.get('edge_cases', {})
        )
        print(f'FINISHED in {time.time() - start} seconds')
    except Exception as e:
        traceback.print_exc()
else:
    print('No query found')
