# app/generation/pipeline.py

import re
from app.generation.context_builder import build_context
from app.generation.prompt_builder import build_prompt, _lang_line
from app.generation.citation_builder import build_citations
from app.generation.response_builder import build_final_response
from app.generation.query_analyzer import analyze_query
from app.generation.validator import validate_answer


def get_system_prompt(query_analysis: dict) -> str:
    """
    Dynamic system instruction based on query type + user language.
    """

    qtype = query_analysis.get("query_type", "mixed")
    lang  = query_analysis.get("language", "en")
    lang_line = _lang_line(lang)

    base = {
        "numeric": (
            "You are a precise data-grounded assistant.\n"
            "Extract exact values and explain them briefly.\n"
            "Do not modify numbers or units.\n"
            "Do not hallucinate.\n"
        ),
        "policy_lookup": (
            "You are a legal document assistant.\n"
            "Extract exact provisions and sections.\n"
            "Avoid hallucination.\n"
            "Keep answers precise and grounded.\n"
        ),
        "procedure": (
            "You are a government process assistant.\n"
            "Provide clear step-by-step instructions.\n"
            "Use only given context.\n"
        ),
        "eligibility": (
            "You are an eligibility extraction assistant.\n"
            "List criteria clearly.\n"
            "Do not infer missing information.\n"
        ),
        "financial": (
            "You are a financial data assistant.\n"
            "Extract exact financial values.\n"
            "Do not round or summarize.\n"
        ),
        "explanation": (
            "You are a document explanation assistant.\n"
            "Explain clearly using only context.\n"
            "Do not hallucinate.\n"
        ),
    }

    system = base.get(qtype, (
        "You are a precise document assistant.\n"
        "Answer using only the given context.\n"
        "Do not hallucinate.\n"
    ))

    # Append language instruction to system prompt
    return (
        system
        + "\n"
        + "IMPORTANT:\n"
        + "You MUST respond ONLY in the user's language.\n"
        + "Do NOT switch to English.\n"
        + lang_line
        + "\n"
    )


def query_overlap_score(chunk_text: str, query: str) -> float:
    STOPWORDS = {
        "the", "is", "in", "of", "for", "to", "and", "or",
        "on", "with", "by", "as", "at", "an", "be", "this",
        "that", "are", "from", "what", "how", "when", "where"
    }

    query_words = set(re.findall(r"\b\w+\b", query.lower())) - STOPWORDS
    text_words  = set(re.findall(r"\b\w+\b", (chunk_text or "").lower())) - STOPWORDS

    if not query_words:
        return 0.0

    overlap = len(query_words & text_words)
    return overlap / len(query_words)


def generate_answer(llm, query, chunks, query_lang="en"):

    # ─────────────────────────────────────────────────────────────
    # 🧠 STEP 0: QUERY ANALYSIS
    # ─────────────────────────────────────────────────────────────

    query_analysis = analyze_query(query)

    print("\n===== QUERY ANALYSIS =====\n")
    print(query_analysis)

    if not chunks:
        return {
            "query": query,
            "answer_original": "No relevant information found",
            "answer_translated": "",
            "citations": [],
            "confidence": "low"
        }

    scored_chunks = []
    for c in chunks:
        score = query_overlap_score(c.get("text", ""), query)
        c["_overlap_score"] = score
        scored_chunks.append(c)

    filtered = [c for c in scored_chunks if c["_overlap_score"] >= 0.4]

    if not filtered:
        filtered = scored_chunks

    chunks = filtered
    chunks.sort(key=lambda x: x["_overlap_score"], reverse=True)

    TOP_K = 4
    chunks = chunks[:TOP_K]
    
    # 🔥 FIX: Ensure file_name exists for citation building
    from app.core.database import get_db_conn, release_db_conn

    conn = get_db_conn()
    try:
        chunks = attach_file_names(conn, chunks)
    finally:
        release_db_conn(conn)

    context = build_context(chunks, query_analysis)

    # ✅ build_prompt now receives full query_analysis including language
    prompt = build_prompt(query, context, query_analysis)

    print("\n===== CONTEXT SENT TO LLM =====\n")
    print(context)

    try:
        # ✅ get_system_prompt now receives full query_analysis including language
        system_prompt = get_system_prompt(query_analysis)

        output = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.0,
            max_tokens=512,
            top_p=1.0,
            top_k=1,
            repeat_penalty=1.2
        )

        answer = output["choices"][0]["message"]["content"].strip()

        # ─────────────────────────────────────────────────────────────
        # 🔒 POST-VALIDATION (GROUNDING CHECK)
        # ─────────────────────────────────────────────────────────────

        validation = validate_answer(answer, context, query_analysis)

        if not validation["is_valid"]:
            print("WARN: VALIDATION FAILED:", validation["reason"])
            return {
                "query": query,
                "answer_original": "Answer could not be reliably generated from documents",
                "answer_translated": "",
                "citations": [],
                "confidence": "low",
                "error": validation["reason"]
            }

        if "not available in the provided documents" in answer.lower():
            return {
                "query": query,
                "answer_original": "No relevant information found in documents",
                "answer_translated": "",
                "citations": [],
                "confidence": "low"
            }

    except Exception as e:
        return {
            "query": query,
            "answer_original": "Error generating answer",
            "answer_translated": "",
            "citations": [],
            "confidence": "low",
            "error": str(e)
        }

    response = build_final_response(
        query=query,
        answer=answer,
        chunks=chunks
    )

    response["query_analysis"] = query_analysis

    return response


def attach_file_names(conn, chunks):
    """
    Ensure each chunk has file_name using document_id lookup.
    Safe fallback layer (does not affect retrieval logic).
    """
    if not chunks:
        return chunks

    doc_ids = list({c.get("document_id") for c in chunks if c.get("document_id")})

    if not doc_ids:
        return chunks

    placeholders = ",".join(["%s"] * len(doc_ids))

    query = f"""
        SELECT document_id, file_name, title
        FROM documents
        WHERE document_id IN ({placeholders})
    """

    with conn.cursor() as cur:
        cur.execute(query, doc_ids)
        rows = cur.fetchall()

    doc_map = {
        row[0]: {"file_name": row[1], "title": row[2]}
        for row in rows
    }

    # 🔥 Attach file_name + correct title
    for c in chunks:
        doc_id = c.get("document_id")
        if doc_id in doc_map:
            c["file_name"] = doc_map[doc_id]["file_name"]

            # Fix wrong document_name if needed
            if c.get("document_name", "").endswith(".pdf"):
                c["document_name"] = doc_map[doc_id]["title"]

    return chunks