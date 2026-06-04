# app/generation/prompt_builder.py

# Language label map for prompt instruction
_LANG_INSTRUCTION = {
    "en": "Respond in English.",
    "hi": "अपना उत्तर हिंदी में दें।",
    "mr": "आपले उत्तर मराठीत द्या.",
    "gu": "તમારો જવાબ ગુજરાતીમાં આપો.",
    "ta": "உங்கள் பதிலை தமிழில் கொடுங்கள்.",
    "te": "మీ సమాధానం తెలుగులో ఇవ్వండి.",
    "kn": "ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ.",
}


def _lang_line(lang: str) -> str:
    return _LANG_INSTRUCTION.get(lang, _LANG_INSTRUCTION["en"])


def build_prompt(query: str, context: str, query_analysis: dict) -> str:
    """
    Selects prompt template based on query type.
    Injects language instruction so LLM replies in the user's language.
    """

    qtype = query_analysis.get("query_type", "mixed")
    lang  = query_analysis.get("language", "en")
    lang_line = _lang_line(lang)

    # ─────────────────────────────────────────────────────────────
    # 🔢 NUMERIC TEMPLATE (STRICT)
    # ─────────────────────────────────────────────────────────────
    if qtype == "numeric":
        return f"""
You are a precise data-grounded assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Answer the question using exact values from the context AND provide a brief explanation.

RULES:
- You MUST include exact numeric values from the context
- Do NOT modify numbers or units
- Explanation must be based ONLY on the context
- Do NOT add external knowledge
- Keep explanation concise and relevant
- Clearly associate each value with its entity

OUTPUT FORMAT:
- First state the value(s)
- Then provide a short explanation

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # 📜 POLICY TEMPLATE
    # ─────────────────────────────────────────────────────────────
    elif qtype == "policy_lookup":
        return f"""
You are a government document assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Answer the question clearly using the given context.

RULES:
- Do NOT just list sections or clause numbers
- Extract the actual meaning from the document
- If the query is practical (what should be done), explain it clearly
- Keep answer concise and relevant
- Do NOT hallucinate

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # ⚙️ PROCEDURE TEMPLATE
    # ─────────────────────────────────────────────────────────────
    elif qtype == "procedure":
        return f"""
You are a government process assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Extract step-by-step procedure from the context.

RULES:
- Present answer as numbered steps
- Do NOT invent steps
- Keep instructions clear
- Use only context information

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # 🎯 ELIGIBILITY TEMPLATE
    # ─────────────────────────────────────────────────────────────
    elif qtype == "eligibility":
        return f"""
You are an eligibility criteria extraction system.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Extract eligibility conditions from the context.

RULES:
- List criteria as bullet points
- Do NOT infer missing conditions
- Do NOT explain beyond text

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # 💰 FINANCIAL TEMPLATE
    # ─────────────────────────────────────────────────────────────
    elif qtype == "financial":
        return f"""
You are a financial data extraction assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Extract financial figures and allocations.

RULES:
- Preserve exact numbers and units
- Do NOT round values
- Do NOT summarize
- Present clearly

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # 📘 EXPLANATION TEMPLATE
    # ─────────────────────────────────────────────────────────────
    elif qtype == "explanation":
        return f"""
You are a document explanation assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Explain the concept using ONLY the given context.

RULES:
- Keep answer concise
- Do NOT add external knowledge
- Do NOT hallucinate
- Use simple structured explanation

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""

    # ─────────────────────────────────────────────────────────────
    # 🔀 MIXED TEMPLATE (SAFE FALLBACK)
    # ─────────────────────────────────────────────────────────────
    else:
        return f"""
You are a precise document assistant.

IMPORTANT:
You MUST answer strictly in the user's language.
Your entire answer MUST be in that language.
{lang_line}

TASK:
Answer using ONLY the given context.

RULES:
- Extract facts accurately
- Do NOT hallucinate
- Keep answer structured

Question:
{query}

Context:
{context}

IMPORTANT:
- Do NOT explain what you are doing
- Do NOT say "Based on the context"
- Directly answer the question

Answer (direct):
"""