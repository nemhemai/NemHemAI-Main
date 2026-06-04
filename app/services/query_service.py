# app/services/query_service.py

import os
os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"
from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
from app.generation.pipeline import generate_answer
from app.generation.query_analyzer import detect_language   # ✅ NEW IMPORT
from app.services.ollama_service import get_ollama_llm
import threading
import time
from app.monitoring.query_audit import log_query_event


# ─────────────────────────────────────────────────────────────
# 🌐 LANGUAGE-AWARE OOD MESSAGES
# ─────────────────────────────────────────────────────────────

_OOD_MESSAGES = {
    "en": (
        "I am a Government RAG system assistant. "
        "I can only answer questions based on the uploaded government documents. "
        "Please ask a question related to those documents."
    ),
    "hi": (
        "मैं एक सरकारी RAG प्रणाली सहायक हूँ। "
        "मैं केवल अपलोड किए गए सरकारी दस्तावेज़ों के आधार पर प्रश्नों का उत्तर दे सकता हूँ। "
        "कृपया उन दस्तावेज़ों से संबंधित प्रश्न पूछें।"
    ),
    "mr": (
        "मी एक शासकीय RAG प्रणाली सहाय्यक आहे. "
        "मी केवळ अपलोड केलेल्या शासकीय दस्तऐवजांवर आधारित प्रश्नांची उत्तरे देऊ शकतो. "
        "कृपया त्या दस्तऐवजांशी संबंधित प्रश्न विचारा."
    ),
    "gu": (
        "હું એક સરકારી RAG સિસ્ટમ સહાયક છું. "
        "હું ફક્ત અપલોડ કરેલા સરકારી દસ્તાવેજો પર આધારિત પ્રશ્નોના જ જવાબ આપી શકું છું. "
        "કૃપા કરીને તે દસ્તાવેજો સંબંધિત પ્રશ્ન પૂછો."
    ),
    "ta": (
        "நான் ஒரு அரசு RAG அமைப்பு உதவியாளர். "
        "நான் பதிவேற்றப்பட்ட அரசு ஆவணங்களின் அடிப்படையில் மட்டுமே கேள்விகளுக்கு பதிலளிக்க முடியும். "
        "தயவுசெய்து அந்த ஆவணங்கள் தொடர்பான கேள்வியைக் கேளுங்கள்."
    ),
    "te": (
        "నేను ఒక ప్రభుత్వ RAG వ్యవస్థ సహాయకుడిని. "
        "నేను అప్‌లోడ్ చేసిన ప్రభుత్వ పత్రాల ఆధారంగా మాత్రమే సమాధానాలు ఇవ్వగలను. "
        "దయచేసి ఆ పత్రాలకు సంబంధించిన ప్రశ్న అడగండి."
    ),
    "kn": (
        "ನಾನು ಒಂದು ಸರ್ಕಾರಿ RAG ವ್ಯವಸ್ಥೆ ಸಹಾಯಕ. "
        "ನಾನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಸರ್ಕಾರಿ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ ಮಾತ್ರ ಉತ್ತರಿಸಬಲ್ಲೆ. "
        "ದಯವಿಟ್ಟು ಆ ದಾಖಲೆಗಳಿಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಶ್ನೆ ಕೇಳಿ."
    ),
}


def _get_ood_message(query: str) -> str:
    lang = detect_language(query)
    return _OOD_MESSAGES.get(lang, _OOD_MESSAGES["en"])


# ─────────────────────────────────────────────────────────────
# 🔍 STRICT RETRIEVAL VALIDATION CONFIG
# ─────────────────────────────────────────────────────────────

USE_OLLAMA = True
MIN_SCORE = 0.3
MIN_STRONG_CHUNKS = 2

# ─────────────────────────────────────────────────────────────
# 🔒 SINGLETON LLM
# ─────────────────────────────────────────────────────────────

_llm_instance = None
_llm_lock = threading.Lock()

def get_llm():
    global _llm_instance
    if _llm_instance is None:
        with _llm_lock:
            if _llm_instance is None:
                from llama_cpp import Llama
                _llm_instance = Llama(
                    model_path="models/sarvam-1-Q4_K_M.gguf",
                    n_ctx=4096,
                    n_threads=os.cpu_count(),
                    n_gpu_layers=0,
                    repeat_penalty=1.2,
                    temperature=0.0,
                    log_level="error",
                    verbose=False,
                    seed=42,
                    max_tokens=256,
                    top_p=1.0,
                    top_k=1,
                )
    return _llm_instance


# ─────────────────────────────────────────────────────────────
# 🔍 QUERY EXECUTION SERVICE
# ─────────────────────────────────────────────────────────────

def run_query(query: str, user: dict) -> dict:

    start_time = time.time()

    if not query or not query.strip():
        log_query_event({
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "query": query,
            "response": "",
            "chunks": [],
            "documents": [],
            "confidence": "low",
            "latency": 0,
            "llm_model": "llama3-ollama" if USE_OLLAMA else "sarvam-1",
            "status": "failed",
            "error": "Empty query"
        })
        return {
            "query": query,
            "answer_original": "",
            "answer_translated": "",
            "citations": [],
            "confidence": "low",
            "user_id": user["user_id"],
            "error": "Empty query"
        }

    conn = get_db_conn()
    retriever = HybridRetriever()

    if USE_OLLAMA:
        llm = get_ollama_llm()
        print("Using Ollama Llama3")
    else:
        llm = get_llm()
        print("Using Sarvam")

    try:
        # 🔍 Step 1: Retrieval
        chunks = retriever.retrieve(conn, query)

        print("TOP SCORE DEBUG:", chunks[0:5] if chunks else "NO CHUNKS")

        if not chunks:
            is_ood = True
        else:
            top_score = chunks[0].get("final_score", 0)
            is_ood = top_score < MIN_SCORE

        print("TOP SCORE", top_score)

        chunk_ids = []
        document_ids = set()
        for c in chunks:
            if isinstance(c, dict):
                if c.get("chunk_id"):
                    chunk_ids.append(c["chunk_id"])
                if c.get("document_id"):
                    document_ids.add(c["document_id"])
        document_ids = list(document_ids)

        # ─────────────────────────────────────────────────────────────
        # 🚫 HANDLE OUT-OF-DOMAIN QUERIES
        # ─────────────────────────────────────────────────────────────

        if is_ood:
            latency = int((time.time() - start_time) * 1000)

            # ✅ Language-aware OOD message
            response_text = _get_ood_message(query)

            log_query_event({
                "user_id": user.get("user_id"),
                "username": user.get("username"),
                "query": query,
                "response": response_text,
                "chunks": [],
                "documents": [],
                "confidence": "low",
                "latency": latency,
                "llm_model": "llama3-ollama" if USE_OLLAMA else "sarvam-1",
                "status": "success"
            })
            return {
                "query": query,
                "answer_original": response_text,
                "answer_translated": "",
                "citations": [],
                "confidence": "low"
            }

        # 🧠 Step 2: Generation
        response = generate_answer(llm, query, chunks)

        answer = response.get("answer_original", "")

        answer_lower = answer.lower()
        if (
            "not available in the provided documents" in answer_lower
            or "no relevant information found in documents" in answer_lower
        ):
            is_valid_answer = False
        else:
            is_valid_answer = True

        # ─────────────────────────────────────────────────────────────
        # 🚫 HANDLE INVALID / NON-GROUNDED ANSWERS
        # ─────────────────────────────────────────────────────────────

        if not is_valid_answer:
            latency = int((time.time() - start_time) * 1000)

            # ✅ Language-aware fallback message
            response_text = _get_ood_message(query)

            log_query_event({
                "user_id": user.get("user_id"),
                "username": user.get("username"),
                "query": query,
                "response": response_text,
                "chunks": [],
                "documents": [],
                "confidence": "low",
                "latency": latency,
                "llm_model": "llama3-ollama" if USE_OLLAMA else "sarvam-1",
                "status": "success"
            })
            return {
                "query": query,
                "answer_original": response_text,
                "answer_translated": "",
                "citations": [],
                "confidence": "low"
            }

        confidence = response.get("confidence", "low")
        latency = int((time.time() - start_time) * 1000)

        log_query_event({
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "query": query,
            "response": answer,
            "chunks": chunk_ids,
            "documents": document_ids,
            "confidence": confidence,
            "latency": latency,
            "llm_model": "llama3-ollama" if USE_OLLAMA else "sarvam-1",
            "status": "success"
        })

        return response

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        log_query_event({
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "query": query,
            "response": "",
            "chunks": [],
            "documents": [],
            "confidence": "low",
            "latency": latency,
            "llm_model": "llama3-ollama" if USE_OLLAMA else "sarvam-1",
            "status": "failed",
            "error": str(e)
        })
        return {
            "query": query,
            "answer_original": "",
            "answer_translated": "",
            "citations": [],
            "confidence": "low",
            "error": str(e)
        }

    finally:
        release_db_conn(conn)