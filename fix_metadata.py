import json
import os
from glob import glob
from app.core.database import get_db_conn, release_db_conn

conn = get_db_conn()
try:
    with conn.cursor() as cur:
        json_files = glob("d:/NH_RAG/gov-entitlement-ai/data/entitlement/*.json")
        for j_path in json_files:
            base_name = os.path.basename(j_path).replace(".json", "")
            pdf_name = f"{base_name}.pdf"
            with open(j_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            cur.execute("UPDATE documents SET metadata = %s WHERE file_name = %s", (json.dumps(meta), pdf_name))
            if cur.rowcount > 0:
                print(f"Fixed metadata for {pdf_name}")
            else:
                print(f"Document not found in DB: {pdf_name}")
        
    conn.commit()
finally:
    release_db_conn(conn)
