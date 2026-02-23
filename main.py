from dotenv import load_dotenv
import os

from fastapi import FastAPI
from pydantic import BaseModel

from app.llm.groq_client import get_llm
from app.retrieval.vectorstore import get_vectorstore
from app.retrieval.retrieve import retrieve_json_and_pdf
from app.rag.rag_engine import rag_answer
from app.routes.ingest import router as ingest_router

app = FastAPI(title="NemHem Policy RAG")
app.include_router(ingest_router)

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
async def health():
    return {"status": "NemHem backend active"}

@app.post("/query")
async def query_rag(request: QueryRequest):
    llm = get_llm()
    vectorstore = get_vectorstore()

    docs = retrieve_json_and_pdf(vectorstore, request.query)
    result = rag_answer(request.query, docs, llm)

    return {"answer": result["answer"]}


# CLI mode remains unchanged
def main():
    llm = get_llm()
    vectorstore = get_vectorstore()

    print("System ready.")
    print("Documents:", vectorstore.count())

    while True:
        query = input("\nEnter query (or 'exit'): ")
        if query.lower() == "exit":
            break

        docs = retrieve_json_and_pdf(vectorstore, query)
        result = rag_answer(query, docs, llm)

        print("\n--- RESPONSE ---")
        print(result["answer"])


if __name__ == "__main__":
    main()
