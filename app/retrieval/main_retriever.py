# app/retrieval/main_retriever.py

from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
from app.generation.pipeline import generate_answer
from llama_cpp import Llama

llm = Llama(
    model_path="models/sarvam-1-Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=0
)

query = "Duties of municipal authority?"

retriever = HybridRetriever()

conn = get_db_conn()

try:
    results = retriever.retrieve(conn, query)
    
    
    response = generate_answer(llm, query, results)
    print("\nFINAL RESPONSE:\n", response)

    if results:
        for i, r in enumerate(results[:5]):
            print(f"\nRank {i+1}")
            print("Score:", r["final_score"])
            print("Text:", r["text"][:1000])
    else:
        print("No results found")

finally:
    release_db_conn(conn)   # ✅ MUST release connection back to pool when done
    
#penalty for waste segregation
#What is solid waste?
#Define bulk waste generator
#What is waste processing facility?
#Explain segregation of waste
#Duties of muncipal authority