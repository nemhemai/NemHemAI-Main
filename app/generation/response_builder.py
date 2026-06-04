# app/generation/response_builder.py

from .citation_builder import build_citations

def build_final_response(query: str, answer: str, chunks: list[dict]):

    citations = build_citations(
        chunks,
        list(range(1, len(chunks) + 1))
    )

    return {
        "query": query,
        "answer_original": answer,
        "answer_translated": "",
        "citations": citations[:3],
        "confidence": "medium"
    }