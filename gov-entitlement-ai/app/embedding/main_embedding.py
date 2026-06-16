# app/embedding/main_embedding.py

from app.core.database import get_db_conn, release_db_conn
from app.embedding.chunk_fetcher import load_chunks_for_embedding
from app.embedding.embedding_engine import EmbeddingEngine
from app.embedding.embedding_store import store_embeddings
import time

def run_embedding_pipeline(document_id: int, batch_size: int = 200):

    conn = get_db_conn()
    engine = EmbeddingEngine()

    total_processed = 0

    try:
        print(f"\n--- START EMBEDDING document_id={document_id} ---")

        while True:

            # FETCH
            chunks = load_chunks_for_embedding(conn, document_id, batch_size)
            print(f'Step 1: Loaded {len(chunks)} chunks for embedding')

            if not chunks:
                break

            print(f"\n--- BATCH START ({len(chunks)} chunks) ---")
            start_time = time.time()
            # PREPARE
            chunk_ids = [c["chunk_id"] for c in chunks]
            token_counts = [c.get("token_count", 0) for c in chunks]
            print(f'Step 2: Prepared chunk_ids and token_counts')

            try:
                # EMBED
                print(f"Step 3: Generating embeddings for {len(chunks)} chunks...")
                dense_vecs, sparse_vecs = engine.generate_embeddings(chunks)

                print(f"Step 4: Generated embeddings for {len(chunks)} chunks")

                # STORE
                store_embeddings(
                    conn,
                    document_id,
                    chunk_ids,
                    dense_vecs,
                    sparse_vecs,
                    token_counts
                )

                total_processed += len(chunks)
                print(f"Step 5: Stored embeddings in DB")
                end_time = time.time()
                print(f"Batch time: {round(end_time - start_time, 2)} sec")

            except Exception as e:
                print(f"❌ Batch failed for document {document_id}: {e}")
                raise e

        print(f"--- DONE: {total_processed} chunks embedded ---\n")
            
        return total_processed

    except Exception as e:
        print("Embedding pipeline failed:", e)
        raise

    finally:
        release_db_conn(conn)
        

def run_embedding_for_all_documents(batch_size: int = 200):
    
    global_total = 0
    pipeline_start = time.time()
    import torch
    print("Using device:", "cuda" if torch.cuda.is_available() else "cpu")

    conn = get_db_conn()

    try:
        print("\n--- START FULL EMBEDDING PIPELINE ---")

        # 🔹 STEP 1: get all document_ids from chunks
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT c.document_id
                FROM document_chunks c
                LEFT JOIN document_embeddings e
                ON c.chunk_id = e.chunk_id
                WHERE e.chunk_id IS NULL;
            """)
            docs = cur.fetchall()

        print(f"Found {len(docs)} documents")

        # 🔹 STEP 2: iterate each document
        for (doc_id,) in docs:
            print(f"\n====== PROCESSING DOCUMENT {doc_id} ======")

            doc_processed = run_embedding_pipeline(
            document_id=doc_id,
            batch_size=batch_size
        )
            global_total += doc_processed
            print(f"Document {doc_id} processed: {doc_processed} chunks")
            print(f"TOTAL PROCESSED SO FAR: {global_total}")

        print("\n--- ALL DOCUMENTS PROCESSED ---")
        total_time = round(time.time() - pipeline_start, 2)
        print(f"TOTAL PIPELINE TIME: {total_time} sec")

    finally:
        release_db_conn(conn)
        
if __name__ == "__main__":
    run_embedding_for_all_documents(batch_size=200)