import sys
import os
import json
sys.path.append(os.getcwd())
from app.core.db import get_db_pool_sync

pool = get_db_pool_sync()
with pool.connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT metadata FROM documents WHERE document_id=86")
        row = cur.fetchone()
        print(json.dumps(row[0], indent=2) if row else 'Not found')
