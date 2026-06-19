import time
from app.core.database import get_db_conn
from app.retrieval.retriever import HybridRetriever

query = "What are the rules for bulk waste generators?"
print(f"Testing retrieval only for: '{query}'")

conn = get_db_conn()
retriever = HybridRetriever()

# First call (includes model load time for embedding query)
t0 = time.time()
chunks = retriever.retrieve(conn, query, use_rerank=False)
t1 = time.time()
print(f"First retrieval (cold): {t1 - t0:.4f} seconds")

# Second call (warm)
t2 = time.time()
chunks = retriever.retrieve(conn, query, use_rerank=False)
t3 = time.time()
print(f"Second retrieval (warm): {t3 - t2:.4f} seconds")

print(f"Retrieved {len(chunks)} chunks.")
