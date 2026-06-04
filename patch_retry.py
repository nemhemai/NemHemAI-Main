import re

path = r'app\ingestion_orchestrator\ingestion_orchestrator.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """        # --------------------------------------------------
        # CHECK IF ELEMENTS ALREADY EXIST
        # --------------------------------------------------
        if ingestor.elements_exist(document_id):"""

new = """        # --------------------------------------------------
        # CHECK IF ELEMENTS ALREADY EXIST
        # On retry (previously failed/stuck), clear old partial elements
        # so extraction runs fresh instead of being skipped
        # --------------------------------------------------
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM ingestion_jobs WHERE job_id = %s", (str(job_id),))
            _row = cur.fetchone()
            _prev_status = _row[0] if _row else None

        if _prev_status in ("failed", "FAILED", "extracting", "EXTRACTING"):
            print(f"RETRY detected (prev={_prev_status}) -- clearing old elements for fresh extraction")
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_elements WHERE document_id = %s", (document_id,))
            conn.commit()

        if ingestor.elements_exist(document_id):"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS")
else:
    print("NOT FOUND - printing current section:")
    idx = content.find("CHECK IF ELEMENTS")
    print(repr(content[idx-10:idx+200]))
