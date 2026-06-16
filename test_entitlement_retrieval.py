from app.core.database import get_db_conn, release_db_conn
from app.retrieval.entitlement import retrieve_entitlement_clauses
import json

conn = get_db_conn()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT file_name, metadata->>'scheme_name' as scheme FROM documents WHERE metadata->>'agent_domain' = 'entitlement';")
        docs = cur.fetchall()
        print(f"Ingested Entitlement Documents: {len(docs)}")
        for d in docs:
            print(f" - {d[0]} (Scheme: {d[1]})")

    print("\nTesting Retrieval...")
    results = retrieve_entitlement_clauses(conn, "what are the eligibility criteria for PM SVANidhi?", top_k=3, scheme_name="PM SVANidhi", language=None)
    print(f"Retrieved {len(results)} chunks.")
    if results:
        print(f"Top result score: {results[0]['score']}")
        print(f"Top result text snippet: {results[0]['text'][:200]}...")
finally:
    release_db_conn(conn)
