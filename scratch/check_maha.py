import psycopg2

def check():
    conn = psycopg2.connect("dbname=nemhem_db user=postgres password=12345678 host=127.0.0.1 port=5433")
    cur = conn.cursor()
    
    print("--- Document Info ---")
    cur.execute("SELECT document_id, title, metadata->>'uploaded_by' FROM documents WHERE file_name LIKE '%maha_finance%'")
    doc = cur.fetchone()
    if not doc:
        print("Document not found in documents table.")
        return
        
    doc_id, title, uploaded_by = doc
    print(f"ID: {doc_id}")
    print(f"Title: {title}")
    print(f"Uploaded By: {uploaded_by}")
    
    print("\n--- Chunks Extracted ---")
    cur.execute("SELECT count(*) FROM chunks WHERE document_id = %s", (doc_id,))
    print(f"Total Chunks: {cur.fetchone()[0]}")
    
    print("\n--- First 3 Chunks ---")
    cur.execute("SELECT chunk_index, content_text FROM chunks WHERE document_id = %s ORDER BY chunk_index LIMIT 3", (doc_id,))
    for idx, text in cur.fetchall():
        print(f"[{idx}] {text[:100]}...")

if __name__ == "__main__":
    check()
