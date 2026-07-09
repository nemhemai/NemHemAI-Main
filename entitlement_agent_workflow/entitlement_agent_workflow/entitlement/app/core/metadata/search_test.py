import os
import sys
import argparse
from pathlib import Path
from qdrant_client import QdrantClient

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

from app.embedding.embedding_engine import EmbeddingEngine


def run_search(query: str, limit: int = 3):
    print(f"Connecting to Qdrant...")
    client = QdrantClient(url="http://localhost:6333")
    
    print("Loading embedding model...")
    engine = EmbeddingEngine()
    
    print(f"Encoding query: '{query}'...")
    dense_vec, _ = engine.embed_query(query)
    
    collection_name = "schemes"
    print(f"Searching Qdrant collection '{collection_name}'...")
    response = client.query_points(
        collection_name=collection_name,
        query=dense_vec.tolist(),
        limit=limit
    )
    results = response.points
    
    print(f"\nTop {len(results)} matches for query '{query}':")
    print("=" * 80)
    for idx, hit in enumerate(results):
        payload = hit.payload
        print(f"Match #{idx + 1} | Score: {hit.score:.4f}")
        print(f"Scheme ID:   {payload.get('scheme_id')}")
        print(f"Scheme Name: {payload.get('scheme_name')}")
        print(f"Category:    {payload.get('category')}")
        print(f"Authority:   {payload.get('issuing_authority')}")
        print(f"Rules count: {len(payload.get('eligibility_rules', []))}")
        print(f"Required Documents: {', '.join(payload.get('required_documents', []))}")
        print("-" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Qdrant semantic search for dynamic schemes")
    parser.add_argument("--query", type=str, default="schemes for street vendors needing loans", help="Search query")
    parser.add_argument("--limit", type=int, default=3, help="Max matches to return")
    args = parser.parse_args()
    
    run_search(args.query, args.limit)
