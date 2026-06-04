# app/retrieval/reranker.py

from typing import List, Dict


def rerank_chunks(
    embedder,
    query: str,
    chunks: List[Dict],
) -> dict[str, float]:

    if not chunks:
        return {}

    texts = [c["text"] for c in chunks]

    ranked_pairs = embedder.rerank(query, texts, top_k=len(texts))

    scores = {}
    for idx, score in ranked_pairs:
        if idx < len(chunks):
            cid = chunks[idx]["chunk_id"]
            scores[cid] = score

    return scores