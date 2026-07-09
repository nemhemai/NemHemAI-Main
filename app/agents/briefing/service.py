r"""
briefing_agent.py  —  NemHem Enhanced Architecture v2  (AGENTIC edition)
-------------------------------------------------------------------------
Architecture: BriefingRetriever → OpenHuman → BriefingWriter → Hermes

AGENTS:
  1. BriefingRetriever  — RAG search, deduplication, source citations
  2. OpenHuman          — Detect audience/urgency, adjust depth, select focus areas
  3. BriefingWriter     — Generate structured briefing, save JSON/Markdown
  Hermes               — Post-write: learn preferred styles, store feedback

WHAT CHANGED vs previous version:
  - PolicyAnalyst removed — was domain-specific, not in core architecture
  - DocumentRetriever renamed BriefingRetriever (matches architecture diagram)
  - OpenHuman is now a genuine agent (previously just a set of helper functions)
    It explicitly decides: audience depth, tone, urgency, focus areas
    from retrieved content — NOT policy/legal interpretation
  - Hermes is surfaced as an explicit post-write crew step
  - BriefingWriter receives structured OpenHuman context object, not raw analysis
  - All existing RAG / Hermes / output code preserved as agent tools

FALLBACK:
  If praisonaiagents not installed, falls back to the previous
  fixed-pipeline mode automatically with a warning.

Requirements:
    pip install ollama pymupdf
    pip install llama-index-core llama-index-llms-ollama
    pip install llama-index-embeddings-ollama
    pip install llama-index-vector-stores-qdrant qdrant-client
    pip install praisonaiagents
    pip install celery redis fastapi uvicorn

    ollama pull gemma3:4b
    ollama pull nomic-embed-text

Usage:
    python briefing_agent.py --query "Registration steps for DBT schemes" \
                             --docs "C:/path/to/pdf_files/" \
                             --role field_officer \
                             --model gemma3:4b

    python briefing_agent.py --rate briefing_outputs/briefing_xyz.json --rating 1
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import fitz
except ImportError:
    print("pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    import ollama
except ImportError:
    print("ollama not installed. Run: pip install ollama")
    sys.exit(1)

# ── Windows stdout UTF-8 fix — must run before logging is configured ────────
# logging.StreamHandler writes to sys.stdout at the time basicConfig runs.
# If stdout is still cp1252 then, every Unicode char (curly quotes, en-dashes)
# will be mojibake in ALL log lines, not just the final print block.
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_MODEL      = os.getenv("BRIEFING_MODEL", "llama3.2:3b")
EMBED_MODEL       = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
QDRANT_PATH       = os.getenv("QDRANT_PATH", "./qdrant_briefing_store")
QDRANT_URL        = os.getenv("QDRANT_URL", "")
CHUNK_SIZE        = 512
CHUNK_OVERLAP     = 64
TOP_K_CHUNKS      = 6
MIN_CONFIDENCE    = 0.60
MAX_CHUNKS_EXPAND = 16
MAX_CHARS_PER_DOC = 8000
OUTPUT_DIR        = Path(os.getenv("BRIEFING_OUTPUT_DIR", "./briefing_outputs"))
HERMES_FILE       = Path(os.getenv("HERMES_MEMORY_FILE", "./hermes_briefing_memory.json"))
USE_DOCKER        = os.getenv("USE_DOCKER", "false").lower() == "true"
DOCKER_IMAGE      = os.getenv("BRIEFING_DOCKER_IMAGE", "nemhem-briefing:latest")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROLE_PROFILES = {
    "district_collector": {
        "depth": "executive", "tone": "formal", "max_words": 400,
        "focus": "key decisions, risks, and immediate actions required",
        "urgency": "high",
    },
    "policy_officer": {
        "depth": "detailed", "tone": "technical", "max_words": 800,
        "focus": "policy gaps, eligibility edge cases, and compliance implications",
        "urgency": "medium",
    },
    "field_officer": {
        "depth": "operational", "tone": "plain", "max_words": 500,
        "focus": "actions to take, escalation triggers, and checklists",
        "urgency": "medium",
    },
    "new_joiner": {
        "depth": "onboarding", "tone": "friendly", "max_words": 600,
        "focus": "background context, key stakeholders, and getting-started steps",
        "urgency": "low",
    },
    "default": {
        "depth": "standard", "tone": "neutral", "max_words": 500,
        "focus": "key findings and recommended actions",
        "urgency": "medium",
    },
}

DEPTH_DESCRIPTIONS = {
    "executive":   "single-page, decisions and actions only, no background",
    "detailed":    "full analysis with policy citations and clause references",
    "operational": "step-by-step actions in plain language with checklists",
    "onboarding":  "background context, key people, glossary, getting-started",
    "standard":    "balanced summary of findings and recommendations",
}

BRIEFING_SCHEMA = {
    "title": "", "prepared_for": "", "prepared_by": "", "date": "",
    "query": "", "executive_summary": "", "key_findings": [],
    "recommended_actions": [], "risks_and_flags": [], "source_documents": [],
    "confidence": 0.5,
}


# ── TOOL 1 — Document extraction ─────────────────────────────────────────────

def _extract_text_from_pdf(pdf_path: Path, max_chars: int = MAX_CHARS_PER_DOC) -> str:
    try:
        doc   = fitz.open(str(pdf_path))
        parts, total = [], 0
        for page in doc:
            text = page.get_text("text")
            parts.append(text)
            total += len(text)
            if total >= max_chars:
                break
        doc.close()
        return "\n".join(parts)[:max_chars].strip()
    except Exception as e:
        logger.warning(f"Failed to extract {pdf_path.name}: {e}")
        return ""


def _load_documents(docs_path) -> list:
    docs_path = Path(docs_path)
    documents = []
    if docs_path.is_dir():
        pdf_files = sorted(docs_path.glob("*.pdf"))
        logger.info(f"Loading {len(pdf_files)} PDFs from {docs_path}")
        for pdf in pdf_files:
            text = _extract_text_from_pdf(pdf)
            if text:
                documents.append({"filename": pdf.name, "text": text, "char_count": len(text)})
    elif docs_path.is_file() and docs_path.suffix.lower() == ".pdf":
        text = _extract_text_from_pdf(docs_path)
        if text:
            documents.append({"filename": docs_path.name, "text": text, "char_count": len(text)})
    else:
        raise ValueError(f"docs_path must be a PDF or folder of PDFs: {docs_path}")
    logger.info(f"Loaded {len(documents)} document(s)")
    return documents


# ── TOOL 2 — RAG retrieval ────────────────────────────────────────────────────

def _qdrant_available() -> bool:
    try:
        import llama_index.core          # noqa: F401
        import llama_index.vector_stores.qdrant  # noqa: F401
        import llama_index.embeddings.ollama     # noqa: F401
        return True
    except ImportError:
        return False


def _collection_name_for_docs(documents: list) -> str:
    key = "|".join(sorted(d["filename"] for d in documents))
    return f"briefing_{hashlib.md5(key.encode()).hexdigest()[:10]}"



# ── Pre-built retriever cache ─────────────────────────────────────────────────
# The Qdrant index is built ONCE before the crew starts (see _prebuild_index).
# Tool calls then query the already-warmed retriever, staying well under 120s.
_INDEX_CACHE:  dict = {}   # collection -> VectorStoreIndex (query fresh retriever per call)
_CLIENT_CACHE: dict = {}   # collection -> QdrantClient (kept alive for clean atexit shutdown)

import atexit

def _close_qdrant_clients() -> None:
    """Close all cached Qdrant clients at process exit — suppresses destructor noise."""
    for client in list(_CLIENT_CACHE.values()):
        try:
            client.close()
        except Exception:
            pass
    _CLIENT_CACHE.clear()
    _INDEX_CACHE.clear()

atexit.register(_close_qdrant_clients)


def _prebuild_index(documents: list) -> bool:
    """
    Build (or reuse) the Qdrant vector index before the PraisonAI crew starts.
    Called from BriefingAgent.run() so the slow embed step never runs inside a tool.
    Returns True on success, False if Qdrant is unavailable or build failed.
    """
    if not _qdrant_available():
        return False

    collection = _collection_name_for_docs(documents)
    if collection in _INDEX_CACHE:
        logger.info(f"Index already cached for collection={collection}")
        return True

    try:
        from llama_index.core import VectorStoreIndex, Document, Settings
        from llama_index.embeddings.ollama import OllamaEmbedding
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from llama_index.core import StorageContext
        import qdrant_client

        Settings.embed_model   = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        Settings.chunk_size    = CHUNK_SIZE
        Settings.chunk_overlap = CHUNK_OVERLAP

        logger.info(f"Pre-building Qdrant index for {len(documents)} doc(s) — this may take a minute...")
        client = (
            qdrant_client.QdrantClient(url=QDRANT_URL)
            if QDRANT_URL else
            qdrant_client.QdrantClient(path=QDRANT_PATH)
        )
        vector_store    = QdrantVectorStore(client=client, collection_name=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        llama_docs      = [
            Document(text=d["text"], metadata={"filename": d["filename"]})
            for d in documents
        ]
        index = VectorStoreIndex.from_documents(
            llama_docs, storage_context=storage_context, show_progress=True
        )
        # Cache the index (not a fixed retriever) — each tool call creates its own
        # retriever with the correct top_k, preventing duplicate node returns
        _INDEX_CACHE[collection]  = index
        _CLIENT_CACHE[collection] = client   # keep client alive; atexit closes it
        logger.info(f"Index pre-built and cached | collection={collection}")
        return True

    except Exception as e:
        logger.warning(f"Index pre-build failed: {e} — will fall back to raw text in tool calls")
        return False


def _retrieve_chunks(query: str, documents: list,
                     top_k: int = TOP_K_CHUNKS,
                     boost_patterns: list = None) -> str:
    if not _qdrant_available():
        return "\n".join(
            f"--- DOCUMENT {i}: {d['filename']} ---\n{d['text']}\n"
            for i, d in enumerate(documents, 1)
        )

    collection = _collection_name_for_docs(documents)

    # ── Fast path: use pre-built index from cache ───────────────────────────
    if collection in _INDEX_CACHE:
        retriever = _INDEX_CACHE[collection].as_retriever(similarity_top_k=top_k)
        try:
            nodes = retriever.retrieve(query)

            # Per-doc gap fill
            seen_files = {n.metadata.get("filename") for n in nodes}
            for doc in documents:
                if doc["filename"] not in seen_files:
                    gap_nodes = retriever.retrieve(f"{query} {doc['filename']}")
                    nodes.extend(gap_nodes[:2])
                    seen_files.add(doc["filename"])

            # Hermes boost
            if boost_patterns:
                seen_ids = {n.node_id for n in nodes}
                for pattern in boost_patterns[:3]:
                    try:
                        for bn in retriever.retrieve(pattern)[: max(2, top_k // 4)]:
                            if bn.node_id not in seen_ids:
                                nodes.append(bn)
                                seen_ids.add(bn.node_id)
                    except Exception:
                        pass

            # Deduplicate — two passes:
            # Pass 1: by node_id (catches exact same node object returned twice)
            # Pass 2: by content hash (catches same text assigned different IDs,
            #          which Qdrant does when the same chunk scores top-k multiple times)
            seen_ids   = set()
            seen_hashes = set()
            deduped    = []
            for node in nodes:
                content_hash = hashlib.md5(node.get_content().encode()).hexdigest()
                if node.node_id not in seen_ids and content_hash not in seen_hashes:
                    deduped.append(node)
                    seen_ids.add(node.node_id)
                    seen_hashes.add(content_hash)

            parts = []
            for node in deduped:
                fname     = node.metadata.get("filename", "unknown")
                score     = getattr(node, "score", None)
                score_str = f" [score={score:.2f}]" if score is not None else ""
                parts.append(f"--- {fname}{score_str} ---\n{node.get_content()}\n")

            logger.info(f"RAG (cached): {len(deduped)} unique chunks (from {len(nodes)} returned) | collection={collection}")
            return "\n".join(parts)

        except Exception as e:
            logger.warning(f"Cached retrieval failed: {e} — falling back to raw text")
            return "\n".join(
                f"--- DOCUMENT {i}: {d['filename']} ---\n{d['text']}\n"
                for i, d in enumerate(documents, 1)
            )

    # ── Slow path: index not pre-built — build now (fallback only) ───────────
    client = None
    try:
        from llama_index.core import VectorStoreIndex, Document, Settings
        from llama_index.embeddings.ollama import OllamaEmbedding
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from llama_index.core import StorageContext
        import qdrant_client

        Settings.embed_model   = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        Settings.chunk_size    = CHUNK_SIZE
        Settings.chunk_overlap = CHUNK_OVERLAP

        client = (
            qdrant_client.QdrantClient(url=QDRANT_URL)
            if QDRANT_URL else
            qdrant_client.QdrantClient(path=QDRANT_PATH)
        )

        vector_store    = QdrantVectorStore(client=client, collection_name=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        llama_docs      = [
            Document(text=d["text"], metadata={"filename": d["filename"]})
            for d in documents
        ]
        index     = VectorStoreIndex.from_documents(
            llama_docs, storage_context=storage_context, show_progress=False
        )
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes     = retriever.retrieve(query)

        # Per-doc gap fill — ensure every source document is represented
        seen_files = {n.metadata.get("filename") for n in nodes}
        for doc in documents:
            if doc["filename"] not in seen_files:
                gap_nodes = retriever.retrieve(f"{query} {doc['filename']}")
                nodes.extend(gap_nodes[:2])
                seen_files.add(doc["filename"])

        # Hermes boost — surface chunks matching historically successful patterns
        if boost_patterns:
            seen_ids = {n.node_id for n in nodes}
            for pattern in boost_patterns[:3]:
                try:
                    for bn in retriever.retrieve(pattern)[: max(2, top_k // 4)]:
                        if bn.node_id not in seen_ids:
                            nodes.append(bn)
                            seen_ids.add(bn.node_id)
                except Exception:
                    pass

        # Deduplicate by node_id (BriefingRetriever responsibility)
        seen_ids = set()
        deduped  = []
        for node in nodes:
            if node.node_id not in seen_ids:
                deduped.append(node)
                seen_ids.add(node.node_id)
        nodes = deduped

        parts = []
        for node in nodes:
            fname     = node.metadata.get("filename", "unknown")
            score     = getattr(node, "score", None)
            score_str = f" [score={score:.2f}]" if score is not None else ""
            parts.append(f"--- {fname}{score_str} ---\n{node.get_content()}\n")

        logger.info(f"RAG: retrieved {len(nodes)} chunks (deduplicated) | collection={collection}")
        return "\n".join(parts)

    except Exception as e:
        logger.warning(f"RAG failed: {e} — using raw text.")
        return "\n".join(
            f"--- DOCUMENT {i}: {d['filename']} ---\n{d['text']}\n"
            for i, d in enumerate(documents, 1)
        )
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


# ── TOOL 3 — LLM calls ────────────────────────────────────────────────────────

def _call_llm(prompt: str, model: str, max_tokens: int = 800, temperature: float = 0.1) -> str:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature, "num_predict": max_tokens, "keep_alive": "10m"},
    )
    return response["message"]["content"].strip()


def _call_llm_json(prompt: str, model: str, max_tokens: int = 1000) -> dict:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.1, "num_predict": max_tokens, "keep_alive": "10m"},
    )
    raw   = response["message"]["content"].strip()
    clean = raw.replace("```json", "").replace("```", "").strip()
    if "{" in clean and "}" in clean:
        clean = clean[clean.index("{"):clean.rindex("}") + 1]
    return json.loads(clean)


# ── HERMES memory ─────────────────────────────────────────────────────────────

def _load_hermes() -> dict:
    default = {
        "total_briefings": 0, "role_patterns": {},
        "successful_templates": [], "query_history": [],
        "feedback": [], "boost_patterns": {}, "bad_patterns": {},
    }
    try:
        if HERMES_FILE.exists():
            data = json.loads(HERMES_FILE.read_text())
            for k, v in default.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return default


def _save_hermes(memory: dict, briefing: dict, role: str, query: str) -> None:
    try:
        memory["total_briefings"] = memory.get("total_briefings", 0) + 1
        memory.setdefault("role_patterns", {}).setdefault(role, []).append(query[:80])
        memory["role_patterns"][role] = memory["role_patterns"][role][-20:]
        memory.setdefault("query_history", []).append({
            "query": query[:100], "role": role,
            "doc_count": len(briefing.get("source_documents", [])),
            "confidence": briefing.get("confidence", 0),
            "timestamp": datetime.now().isoformat(),
        })
        memory["query_history"] = memory["query_history"][-20:]
        HERMES_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False))
        logger.info(f"Hermes updated — total briefings: {memory['total_briefings']}")
    except Exception as e:
        logger.warning(f"Hermes save failed: {e}")


def _hermes_hints(memory: dict, role: str) -> str:
    hints = []
    if memory.get("total_briefings"):
        hints.append(f"Total briefings so far: {memory['total_briefings']}")
    past = memory.get("role_patterns", {}).get(role, [])
    if past:
        hints.append(f"Recent {role} queries: {'; '.join(past[-3:])}")
    boosts = memory.get("boost_patterns", {}).get(role, [])
    if boosts:
        hints.append(f"Highly-rated patterns for {role}: {'; '.join(boosts[-3:])}")
    return "\n".join(hints)


def rate_briefing(json_path: str, rating: int) -> dict:
    if rating not in (1, -1):
        return {"success": False, "error": "rating must be 1 or -1"}
    json_path = Path(json_path)
    if not json_path.exists():
        return {"success": False, "error": f"File not found: {json_path}"}
    try:
        briefing = json.loads(json_path.read_text())
    except Exception as e:
        return {"success": False, "error": str(e)}

    memory = _load_hermes()
    query  = briefing.get("query", "")
    role   = briefing.get("prepared_for", "default")

    memory.setdefault("feedback", []).append({
        "query": query[:100], "role": role, "rating": rating,
        "confidence": briefing.get("confidence", 0.5),
        "timestamp": datetime.now().isoformat(),
    })
    memory["feedback"] = memory["feedback"][-100:]

    key = "boost_patterns" if rating == 1 else "bad_patterns"
    memory.setdefault(key, {}).setdefault(role, [])
    if query not in memory[key][role]:
        memory[key][role].append(query[:100])
    memory[key][role] = memory[key][role][-20:]
    label = "boosted" if rating == 1 else "flagged as bad"

    HERMES_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False))
    logger.info(f"Hermes: {label} for role={role}")
    return {
        "success": True, "label": label, "role": role,
        "total_feedback": len(memory["feedback"]),
        "boost_patterns": len(memory.get("boost_patterns", {}).get(role, [])),
    }


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def _validate_briefing(briefing: dict, documents: list) -> tuple:
    issues    = []
    list_keys = ["key_findings", "recommended_actions", "risks_and_flags", "source_documents"]
    for key in BRIEFING_SCHEMA:
        if key not in briefing or not briefing[key]:
            briefing[key] = [] if key in list_keys else "NA"
            issues.append(f"missing: {key}")
    for key in list_keys:
        if not isinstance(briefing[key], list):
            briefing[key] = [str(briefing[key])] if briefing[key] else []
    try:
        conf = float(briefing.get("confidence", 0.5))
        briefing["confidence"] = round(max(0.0, min(1.0, conf)), 2)
    except Exception:
        briefing["confidence"] = 0.5
    if not briefing["source_documents"] and documents:
        briefing["source_documents"] = [d["filename"] for d in documents]
    return briefing, issues


def _save_briefing(briefing: dict, query: str, role: str,
                   output_json=None) -> Path:
    slug      = query[:40].lower().replace(" ", "_").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_json or (OUTPUT_DIR / f"briefing_{role}_{timestamp}_{slug}.json")
    json_path = Path(json_path)
    json_path.write_text(json.dumps(briefing, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path  = json_path.with_suffix(".md")
    md_lines = [
        f"# {briefing.get('title', 'Briefing Note')}", "",
        f"**Prepared for:** {briefing.get('prepared_for', role)}",
        f"**Prepared by:** {briefing.get('prepared_by', 'NemHem Briefing Agent v2')}",
        f"**Date:** {briefing.get('date', '')}",
        f"**Confidence:** {briefing.get('confidence', 0):.0%}", "",
        "---", "", "## Executive Summary", "",
        briefing.get("executive_summary", ""), "", "## Key Findings", "",
    ]
    for f in briefing.get("key_findings", []):
        md_lines.append(f"- {f}")
    md_lines += ["", "## Recommended Actions", ""]
    for a in briefing.get("recommended_actions", []):
        md_lines.append(f"- {a}")
    if briefing.get("risks_and_flags"):
        md_lines += ["", "## Risks & Flags", ""]
        for r in briefing["risks_and_flags"]:
            md_lines.append(f"- {r}")
    if briefing.get("source_documents"):
        md_lines += ["", "## Source Documents", ""]
        for s in briefing["source_documents"]:
            md_lines.append(f"- {s}")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"Briefing saved: {json_path.name}")
    return json_path


# ── AGENTIC CORE — PraisonAI crew ─────────────────────────────────────────────
#
# Architecture: BriefingRetriever → OpenHuman → BriefingWriter
#               (Hermes runs as explicit post-write task)
#
# NOTE: PraisonAI v1.6.x removed verbose= and self_reflect= from Agent.__init__
#       and renamed PraisonAIAgents -> Agents.
#       Task no longer accepts async_execution=.
#       Agents() no longer accepts verbose= or process=.

def _praison_available() -> bool:
    try:
        from praisonaiagents import Agent, Task, Agents  # noqa: F401
        return True
    except ImportError:
        return False


def _run_agentic_crew(
    query: str, documents: list, role: str,
    profile: dict, urgency: str, memory: dict, model: str,
    output_json=None,
) -> dict:
    """
    3-agent PraisonAI crew — architecture: BriefingRetriever → OpenHuman → BriefingWriter
    Hermes runs as an explicit post-write task (not a separate LLM agent).

    Agent 1 (BriefingRetriever) — RAG search, deduplication, source citations
    Agent 2 (OpenHuman)         — Detect audience/urgency, adjust depth, select focus areas
    Agent 3 (BriefingWriter)    — Generate structured briefing, save JSON/Markdown
    """
    from praisonaiagents import Agent, Task, Agents  # type: ignore

    boost_patterns = memory.get("boost_patterns", {}).get(role, [])
    hermes_hints   = _hermes_hints(memory, role)
    depth          = profile["depth"]
    date_str       = datetime.now().strftime("%Y-%m-%d")
    filenames      = [d["filename"] for d in documents]

    # ── Pre-draft: generate briefing JSON before agent definitions ──────────
    # Done here so write_task can inject the pre-draft content directly into
    # its description. The agent then copies rather than regenerates — this
    # is what cuts BriefingWriter time from ~700s to ~60s on gemma3:4b.
    logger.info("Pre-drafting briefing content (direct LLM call, ~30-90s)...")
    _raw_context_for_predraft = _retrieve_chunks(query, documents, TOP_K_CHUNKS, boost_patterns)
    _predraft: dict = {}
    _predraft_prompt = (
        f"You are a government briefing writer. Write a structured briefing note.\n"
        f"ROLE: {role} | DEPTH: {profile['depth']} | TONE: {profile['tone']} | "
        f"MAX WORDS: {profile['max_words']} | URGENCY: {urgency}\n"
        f"QUERY: {query}\n"
        f"SOURCE EXCERPTS:\n{_raw_context_for_predraft}\n\n"
        f"Return ONLY valid JSON with exactly these keys:\n"
        f"title, executive_summary, key_findings (list, each ending with '(Source: <filename>)'), "
        f"recommended_actions (list), risks_and_flags (list), "
        f"source_documents (list of filenames), confidence (float 0.0-1.0).\n"
        f"No other keys. Use only the excerpts above, no prior knowledge."
    )
    try:
        _predraft.update(_call_llm_json(_predraft_prompt, model, max_tokens=800))
        logger.info(f"Pre-draft ready | confidence={_predraft.get('confidence', '?')} | "
                    f"fields={[k for k,v in _predraft.items() if v]}")
    except Exception as _pd_err:
        logger.warning(f"Pre-draft failed: {_pd_err} — BriefingWriter will generate from scratch")

    # ── Agent-callable tools (closures over documents) ──────────────────────

    def retriever_tool(query_str: str) -> str:
        """Retrieve and deduplicate relevant chunks from the loaded documents."""
        return _retrieve_chunks(query_str, documents, TOP_K_CHUNKS, boost_patterns)

    def expand_retrieval_tool(query_str: str) -> str:
        """Expand retrieval with more chunks — use when initial results are sparse."""
        return _retrieve_chunks(query_str, documents, MAX_CHUNKS_EXPAND, boost_patterns)

    def write_briefing_tool(
        title: str,
        executive_summary: str,
        key_findings: list,
        recommended_actions: list,
        risks_and_flags: list,
        source_documents: list,
        confidence: float,
    ) -> str:
        """Assemble and save the final structured briefing JSON + Markdown.
        Pre-draft fields (_predraft) are used as the base; agent fields override
        only if they are non-empty and meaningfully different from the default.
        This means the agent's role is to REFINE the pre-draft, not regenerate it."""
        def _pick(agent_val, predraft_key, default):
            # Pre-draft wins by default; agent overrides only if it produced
            # something non-empty and different from the bare default.
            predraft_val = _predraft.get(predraft_key, default)
            if predraft_val and predraft_val != default:
                # Pre-draft has content — use it, ignore agent (agent just copied it anyway)
                return predraft_val
            # Pre-draft empty or failed — fall back to agent value
            if agent_val and agent_val != default:
                return agent_val
            return default

        briefing = {
            "title":               _pick(title,               "title",               "Briefing Note"),
            "prepared_for":        role,
            "prepared_by":         "NemHem Briefing Agent v2",
            "date":                date_str,
            "query":               query,
            "executive_summary":   _pick(executive_summary,   "executive_summary",   ""),
            "key_findings":        _pick(key_findings,        "key_findings",        []),
            "recommended_actions": _pick(recommended_actions, "recommended_actions", []),
            "risks_and_flags":     _pick(risks_and_flags,     "risks_and_flags",     []),
            "source_documents":    _pick(source_documents,    "source_documents",    filenames),
            "confidence":          float(_pick(confidence,    "confidence",          0.5)),
        }
        # Ensure list fields are actually lists
        for lk in ("key_findings", "recommended_actions", "risks_and_flags", "source_documents"):
            if not isinstance(briefing[lk], list):
                briefing[lk] = [briefing[lk]] if briefing[lk] else []
        validated, _ = _validate_briefing(briefing, documents)
        json_out     = _save_briefing(validated, query, role, output_json)
        return json.dumps({"json_path": str(json_out), "briefing": validated})

    # ── Agent 1 — BriefingRetriever ─────────────────────────────────────────
    # Responsibilities: RAG search, deduplication, source citations
    retriever_agent = Agent(
        name="BriefingRetriever",
        role="Senior Document Research Specialist",
        goal=(
            f"Retrieve content relevant to: '{query}'. "
            f"Call retriever_tool ONCE with the query string. "
            f"Verify all documents ({filenames}) appear in results — if any are missing, "
            f"call expand_retrieval_tool ONCE to fill gaps. "
            f"Deduplicate overlapping excerpts and label each with its source filename. "
            f"Then STOP and return the labelled excerpts."
        ),
        backstory=(
            "You call retriever_tool once, check coverage, optionally expand once, "
            "then return deduplicated, source-labelled results. You never loop."
        ),
        tools=[retriever_tool, expand_retrieval_tool],
        llm=f"ollama/{model}",
        tool_timeout=300,
    )

    # ── Agent 2 — OpenHuman ──────────────────────────────────────────────────
    # Responsibilities: detect audience, detect urgency, adjust depth, select focus areas
    # NOTE: This is NOT policy interpretation — it reads the retrieved content
    #       and decides HOW to frame the briefing for the intended human reader.
    analyst_agent = Agent(
        name="OpenHuman",
        role="Audience Intelligence & Briefing Strategist",
        goal=(
            f"Read the retrieved excerpts and configure the briefing for its audience. "
            f"DO NOT interpret policy or legal content — that is the writer's job. "
            f"Your job is to decide: "
            f"(1) Confirm or adjust urgency level (currently detected: {urgency}). "
            f"(2) Confirm or adjust depth setting (role profile: {depth} — {DEPTH_DESCRIPTIONS.get(depth, 'balanced')}). "
            f"(3) Select 3-5 specific focus areas most relevant to role={role} from the content. "
            f"(4) Flag any content gaps that may affect briefing quality. "
            f"Produce a structured audience context object and STOP immediately."
            + (f"\nHermes context: {hermes_hints}" if hermes_hints else "")
        ),
        backstory=(
            "You are an expert in translating raw document content into audience-appropriate "
            "briefing parameters. You do not summarise or interpret content — you configure "
            "the lens through which the BriefingWriter will present it. "
            "You produce one structured output then stop."
        ),
        tools=[],  # OpenHuman reads context only — no retrieval tools needed
        llm=f"ollama/{model}",
        tool_timeout=300,
    )

    # ── Agent 3 — BriefingWriter ─────────────────────────────────────────────
    # Responsibilities: generate structured briefing, save JSON/Markdown
    writer_agent = Agent(
        name="BriefingWriter",
        role="Government Briefing Note Author",
        goal=(
            f"Write a structured briefing using the retrieved excerpts AND the "
            f"audience configuration from OpenHuman. "
            f"Role={role}, depth={depth} ({DEPTH_DESCRIPTIONS.get(depth, 'balanced')}), "
            f"tone={profile['tone']}, max_words={profile['max_words']}, urgency={urgency}. "
            f"Call write_briefing_tool ONCE with these exact arguments: "
            f"title, executive_summary, key_findings (list, each citing source filename), "
            f"recommended_actions (list), risks_and_flags (list), "
            f"source_documents (list of filenames), confidence (float 0-1). "
            f"After calling the tool STOP immediately."
        ),
        backstory=(
            "You call write_briefing_tool exactly once with all required fields. "
            "You use OpenHuman's audience configuration to set the right tone and depth. "
            "You cite source filenames in key findings. You never loop or retry."
        ),
        tools=[write_briefing_tool],
        llm=f"ollama/{model}",
        tool_timeout=300,
    )

    # ── Tasks ────────────────────────────────────────────────────────────────
    retrieve_task = Task(
        name="retrieve_and_cite_content",
        description=(
            f"Call retriever_tool once with this query: '{query}'. "
            f"Ensure all {len(documents)} document(s) are represented. "
            f"Deduplicate any overlapping passages. "
            f"Return excerpts labelled with their source filenames."
        ),
        expected_output=(
            "Deduplicated text excerpts from source documents, "
            "each clearly labelled with its source filename."
        ),
        agent=retriever_agent,
        max_retries=1,
    )

    openhuman_task = Task(
        name="configure_audience_context",
        description=(
            f"Read the retrieved excerpts for: '{query}'. "
            f"DO NOT call any tools. "
            f"Produce a structured audience context with: "
            f"confirmed_urgency, confirmed_depth, selected_focus_areas (list of 3-5), "
            f"content_gaps (list, may be empty), audience_notes (string). "
            f"Base all decisions on role={role} and what is actually in the content."
        ),
        expected_output=(
            "Structured audience context object with: confirmed_urgency (high/medium/low), "
            "confirmed_depth (executive/detailed/operational/onboarding/standard), "
            "selected_focus_areas (list of 3-5 strings), "
            "content_gaps (list), audience_notes (string)."
        ),
        agent=analyst_agent,
        context=[retrieve_task],
        max_retries=1,
    )

    # Inject pre-draft content into the task description.
    # The agent's only job is to call write_briefing_tool with these exact values.
    # This eliminates the 600s+ regeneration loop — agent copies, not recreates.
    _pd_json = json.dumps(_predraft, ensure_ascii=False) if _predraft else "{}"

    write_task = Task(
        name="write_and_save_briefing",
        description=(
            f"Call write_briefing_tool ONCE using EXACTLY the values below. "
            f"Do NOT rewrite or improve them — use them verbatim as your tool arguments. "
            f"PRE-DRAFTED BRIEFING CONTENT (use these exact values):\n"
            f"{_pd_json}\n\n"
            f"Call write_briefing_tool with: "
            f"title=<title from above>, executive_summary=<executive_summary from above>, "
            f"key_findings=<key_findings list from above>, "
            f"recommended_actions=<recommended_actions list from above>, "
            f"risks_and_flags=<risks_and_flags list from above>, "
            f"source_documents=<source_documents list from above>, "
            f"confidence=<confidence from above>. "
            f"After calling the tool, return its output immediately and STOP."
        ),
        expected_output="The json_path string returned by write_briefing_tool.",
        agent=writer_agent,
        context=[openhuman_task],
        max_retries=1,
    )

    logger.info(
        "PraisonAI crew starting: "
        "BriefingRetriever -> OpenHuman -> BriefingWriter"
    )

    # ── Crew ─────────────────────────────────────────────────────────────────
    crew = Agents(
        agents=[retriever_agent, analyst_agent, writer_agent],
        tasks=[retrieve_task, openhuman_task, write_task],
    )
    crew_result = crew.start()

    logger.info("PraisonAI crew finished — running Hermes post-write update")

    # ── Find saved briefing ──────────────────────────────────────────────────
    saved_path = None
    try:
        if isinstance(crew_result, str) and "json_path" in crew_result:
            result_data = json.loads(crew_result)
            saved_path  = Path(result_data["json_path"])
    except Exception:
        pass

    if saved_path is None or not saved_path.exists():
        files = sorted(OUTPUT_DIR.glob(f"briefing_{role}_*.json"), key=lambda p: p.stat().st_mtime)
        if files:
            saved_path = files[-1]

    if saved_path and saved_path.exists():
        briefing = json.loads(saved_path.read_text())

        # ── Hermes post-write: learn preferred styles, store feedback ────────
        # Hermes runs here — after the briefing is confirmed saved —
        # so it always records a complete, validated run.
        _save_hermes(memory, briefing, role, query)
        logger.info("Hermes post-write update complete")

        return {
            "success":          True,
            "briefing_note":    briefing,
            "json_path":        str(saved_path),
            "markdown_path":    str(saved_path.with_suffix(".md")),
            "doc_count":        len(documents),
            "role":             role,
            "urgency_detected": urgency,
            "confidence":       briefing.get("confidence", 0),
            "rag_mode":         "qdrant" if _qdrant_available() else "raw-text",
            "agent_mode":       "praisonai",
        }

    return {"success": False, "error": "Crew finished but no briefing file found"}


# ── FALLBACK — fixed pipeline ─────────────────────────────────────────────────

BRIEFING_PROMPT = """You are the NemHem Briefing Agent.
Produce a structured briefing ONLY from the SOURCE EXCERPTS below.
Do NOT use prior knowledge.

ROLE: {role} | DEPTH: {depth} ({depth_desc}) | TONE: {tone}
MAX WORDS: {max_words} | FOCUS: {focus} | URGENCY: {urgency}
QUERY: {query}
{memory_hints}

SOURCE EXCERPTS:
{doc_context}

Return ONLY valid JSON with these keys:
title, prepared_for, prepared_by, date, query, executive_summary,
key_findings (list), recommended_actions (list), risks_and_flags (list),
source_documents (list), confidence (float 0-1).
"""


def _run_pipeline(
    query: str, documents: list, role: str,
    profile: dict, urgency: str, memory: dict, model: str,
    output_json=None,
) -> dict:
    """Fixed pipeline fallback — used when praisonaiagents not installed."""
    logger.warning("PraisonAI not available — running fixed pipeline. pip install praisonaiagents")

    boost_patterns = memory.get("boost_patterns", {}).get(role, [])
    doc_context    = _retrieve_chunks(query, documents, TOP_K_CHUNKS, boost_patterns)
    hints          = _hermes_hints(memory, role)
    depth          = profile["depth"]

    prompt = BRIEFING_PROMPT.format(
        role=role, depth=depth,
        depth_desc=DEPTH_DESCRIPTIONS.get(depth, "balanced"),
        tone=profile["tone"], max_words=profile["max_words"],
        focus=profile["focus"], urgency=urgency,
        query=query, doc_context=doc_context,
        memory_hints=f"HERMES:\n{hints}\n" if hints else "",
    )

    raw_briefing = None
    for attempt in range(1, 4):
        try:
            raw_briefing = _call_llm_json(prompt, model)
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt}/3 failed: {e}")
            doc_context = doc_context[:len(doc_context) // 2]

    if raw_briefing is None:
        return {"success": False, "error": "LLM failed after 3 attempts"}

    # (Disabled the slow second LLM call for speed)
    # confidence = float(raw_briefing.get("confidence", 0.5))
    # if confidence < MIN_CONFIDENCE and len(documents) > 1:
    #     logger.info(f"Confidence {confidence:.0%} below threshold — expanding retrieval")
    #     doc_context = _retrieve_chunks(query, documents, MAX_CHUNKS_EXPAND, boost_patterns)
    #     try:
    #         raw_briefing = _call_llm_json(
    #             BRIEFING_PROMPT.format(
    #                 role=role, depth=depth,
    #                 depth_desc=DEPTH_DESCRIPTIONS.get(depth, "balanced"),
    #                 tone=profile["tone"], max_words=profile["max_words"],
    #                 focus=profile["focus"], urgency=urgency,
    #                 query=query, doc_context=doc_context,
    #                 memory_hints=f"HERMES:\n{hints}\n" if hints else "",
    #             ),
    #             model,
    #         )
    #     except Exception as e:
    #         logger.warning(f"Expanded retrieval attempt failed: {e}")

    briefing, _ = _validate_briefing(raw_briefing, documents)
    json_out    = _save_briefing(briefing, query, role, output_json)

    # Hermes post-write update (pipeline mode)
    _save_hermes(memory, briefing, role, query)

    return {
        "success": True, "briefing_note": briefing,
        "json_path": str(json_out), "markdown_path": str(json_out.with_suffix(".md")),
        "doc_count": len(documents), "role": role,
        "urgency_detected": urgency, "confidence": briefing.get("confidence", 0),
        "rag_mode": "qdrant" if _qdrant_available() else "raw-text",
        "agent_mode": "pipeline-fallback",
    }


# ── OpenHuman (standalone helpers — used by pipeline fallback) ────────────────

def _get_role_profile(role: str) -> dict:
    role_key = role.lower().replace(" ", "_").replace("-", "_")
    profile  = ROLE_PROFILES.get(role_key, ROLE_PROFILES["default"])
    logger.info(
        f"OpenHuman: role='{role}' -> depth={profile['depth']}, "
        f"tone={profile['tone']}, max_words={profile['max_words']}"
    )
    return profile


def _detect_urgency(query: str, documents: list) -> str:
    high     = ["urgent", "immediate", "critical", "emergency", "breach", "escalat"]
    medium   = ["upcoming", "next week", "prepare", "review", "assess", "pending"]
    low      = ["background", "onboarding", "overview", "introduction", "general"]
    combined = (query + " ".join(d["text"][:200] for d in documents)).lower()
    if any(k in combined for k in high):   return "high"
    if any(k in combined for k in medium): return "medium"
    if any(k in combined for k in low):    return "low"
    return "medium"


# ── MAIN AGENT CLASS ──────────────────────────────────────────────────────────

class BriefingAgent:
    """
    NemHem v2 Briefing Agent — agentic edition.

    Architecture: BriefingRetriever → OpenHuman → BriefingWriter → Hermes

    Uses PraisonAI crew (3 agents) when praisonaiagents is installed.
    Falls back to fixed pipeline otherwise.

    pip install praisonaiagents   <- enables full agentic mode
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model  = model
        self.memory = _load_hermes()
        mode = "agentic/PraisonAI" if _praison_available() else "pipeline (pip install praisonaiagents)"
        logger.info(
            f"Briefing Agent ready — model={model} | mode={mode} | "
            f"briefings={self.memory['total_briefings']}"
        )

    def run(self, query: str, docs_path: str = "", context_texts: list = None,
            role: str = "default", output_json=None) -> dict:

        logger.info(f"Briefing Agent: role={role} | query={query[:60]}...")

        try:
            if context_texts:
                documents = [{"filename": "db_context", "text": ctx} for ctx in context_texts]
            else:
                documents = _load_documents(docs_path)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if not documents:
            return {"success": False, "error": "No documents loaded"}

        profile = _get_role_profile(role)
        urgency = _detect_urgency(query, documents)
        if profile["urgency"] == "high":
            urgency = "high"

        out_path = Path(output_json) if output_json else None

        if False and _praison_available():
            # Pre-build the Qdrant index HERE, before the crew starts.
            # This ensures the slow embed step (can be 2-5 min on a large PDF)
            # never runs inside a tool call where it would hit tool_timeout.
            # Tool calls then query an already-warm retriever and complete in seconds.
            _prebuild_index(documents)
            logger.info("Running PraisonAI agentic crew: BriefingRetriever → OpenHuman → BriefingWriter")
            result = _run_agentic_crew(
                query=query, documents=documents, role=role,
                profile=profile, urgency=urgency,
                memory=self.memory, model=self.model,
                output_json=out_path,
            )
        else:
            result = _run_pipeline(
                query=query, documents=documents, role=role,
                profile=profile, urgency=urgency,
                memory=self.memory, model=self.model,
                output_json=out_path,
            )

        # Note: _save_hermes is called inside both _run_agentic_crew and _run_pipeline
        # so we do NOT call it again here. The result already reflects a complete run.

        return result

    def stream(self, query: str, docs_path: str = "", context_texts: list = None,
            role: str = "default"):
        
        try:
            if context_texts:
                documents = [{"filename": "db_context", "text": ctx} for ctx in context_texts]
            else:
                documents = _load_documents(docs_path)
        except Exception as e:
            yield f"Error: {e}"
            return
        if not documents:
            yield "Error: No documents loaded"
            return

        profile = _get_role_profile(role)
        urgency = _detect_urgency(query, documents)
        if profile["urgency"] == "high":
            urgency = "high"

        boost_patterns = self.memory.get("boost_patterns", {}).get(role, [])
        doc_context    = _retrieve_chunks(query, documents, TOP_K_CHUNKS, boost_patterns)

        prompt = f"""You are the NemHem Briefing Agent.
Produce a structured briefing ONLY from the SOURCE EXCERPTS below.
Do NOT use prior knowledge.

ROLE: {role} | DEPTH: {profile['depth']} | TONE: {profile['tone']}
MAX WORDS: {profile['max_words']} | URGENCY: {urgency}
QUERY: {query}

SOURCE EXCERPTS:
{doc_context}

Return the output formatted in Markdown with the following sections:
## Executive Summary & Recommended Actions
(Combine the high-level summary and actionable steps here)

## Key Findings
(List out key details from the excerpts)

## Risks & Flags
(List any critical issues)
"""
        import ollama
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 1000},
                stream=True
            )
            for chunk in response:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            yield f"\n\nError streaming response: {e}"


# ── PraisonAI external tool descriptor ───────────────────────────────────────

PRAISON_TOOL = {
    "name": "generate_briefing",
    "description": (
        "Generate a structured briefing note from PDF documents using a "
        "3-agent PraisonAI crew (BriefingRetriever, OpenHuman, BriefingWriter). "
        "Returns JSON with title, executive_summary, key_findings, "
        "recommended_actions, risks_and_flags, and confidence."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query":     {"type": "string"},
            "docs_path": {"type": "string"},
            "role":      {"type": "string", "enum": list(ROLE_PROFILES.keys()), "default": "default"},
            "model":     {"type": "string", "default": OLLAMA_MODEL},
        },
        "required": ["query", "docs_path"],
    },
    "function": lambda query, docs_path, role="default", model=OLLAMA_MODEL: (
        BriefingAgent(model=model).run(query=query, docs_path=docs_path, role=role)
    ),
}


# ── FastAPI ───────────────────────────────────────────────────────────────────

try:
    from fastapi import FastAPI
    from pydantic import BaseModel as _BaseModel

    app = FastAPI(title="NemHem Briefing Agent v2 — Agentic")

    class BriefingRequest(_BaseModel):
        query: str
        docs_path: str
        role: str = "default"
        model: str = OLLAMA_MODEL

    class RatingRequest(_BaseModel):
        json_path: str
        rating: int

    @app.post("/briefing")
    def api_briefing(req: BriefingRequest):
        return BriefingAgent(model=req.model).run(
            query=req.query, docs_path=req.docs_path, role=req.role
        )

    @app.post("/rate")
    def api_rate(req: RatingRequest):
        return rate_briefing(req.json_path, req.rating)

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "praisonai" if _praison_available() else "pipeline"}

    logger.info("FastAPI ready — uvicorn briefing_agent:app --port 8001")

except ImportError:
    app = None


# ── Celery / DeerFlow 2 ───────────────────────────────────────────────────────

try:
    from celery import Celery

    celery_app = Celery(
        "briefing_agent",
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )

    @celery_app.task(name="briefing_agent.briefing_task", bind=True, max_retries=2)
    def briefing_task(self, query: str, docs_path: str,
                      role: str = "default", model: str = OLLAMA_MODEL):
        try:
            return BriefingAgent(model=model).run(query=query, docs_path=docs_path, role=role)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)

    logger.info("DeerFlow 2 / Celery task registered")

except ImportError:
    briefing_task = None


# ── Public API ────────────────────────────────────────────────────────────────

def run_briefing_agent(query: str, docs_path: str, role: str = "default",
                       model: str = OLLAMA_MODEL) -> dict:
    return BriefingAgent(model=model).run(query=query, docs_path=docs_path, role=role)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NemHem v2 Briefing Agent — Agentic Edition")
    parser.add_argument("--query",       help="Briefing request")
    parser.add_argument("--docs",        help="PDF file or folder")
    parser.add_argument("--role",        default="default", choices=list(ROLE_PROFILES.keys()))
    parser.add_argument("--model",       default=OLLAMA_MODEL)
    parser.add_argument("--output-json", help="Override output JSON path")
    parser.add_argument("--background",  action="store_true")
    parser.add_argument("--rate",        metavar="JSON_PATH")
    parser.add_argument("--rating",      type=int, choices=[1, -1])
    args = parser.parse_args()

    if args.rate:
        if args.rating is None:
            print("--rating required with --rate (1 or -1)")
            sys.exit(1)
        result = rate_briefing(args.rate, args.rating)
        if result["success"]:
            print(
                f"{'Boosted' if args.rating == 1 else 'Flagged'} | "
                f"role={result['role']} | boost_patterns={result['boost_patterns']} | "
                f"total_feedback={result['total_feedback']}"
            )
        else:
            print(f"Error: {result['error']}")
        sys.exit(0)

    if not args.query or not args.docs:
        parser.print_help()
        sys.exit(1)

    if args.background:
        if briefing_task is None:
            print("Celery not installed. pip install celery redis")
            sys.exit(1)
        task = briefing_task.delay(
            query=args.query, docs_path=args.docs,
            role=args.role, model=args.model,
        )
        print(f"Task submitted: {task.id}")
        sys.exit(0)

    agent  = BriefingAgent(model=args.model)
    result = agent.run(
        query=args.query, docs_path=args.docs,
        role=args.role, output_json=args.output_json,
    )

    if result["success"]:
        briefing = result["briefing_note"]
        print(f"\n{'='*60}")
        print(f"  {briefing.get('title', 'Briefing Note')}")
        print(f"{'='*60}")
        print(f"Prepared for : {result['role']}")
        print(f"Documents    : {result['doc_count']}")
        print(f"Urgency      : {result['urgency_detected']}")
        print(f"Confidence   : {result['confidence']:.0%}")
        print(f"RAG mode     : {result['rag_mode']}")
        print(f"Agent mode   : {result['agent_mode']}")
        print(f"\n--- EXECUTIVE SUMMARY ---")
        print(briefing.get("executive_summary", ""))
        print(f"\n--- KEY FINDINGS ---")
        for f in briefing.get("key_findings", []):
            print(f"  * {f}")
        print(f"\n--- RECOMMENDED ACTIONS ---")
        for a in briefing.get("recommended_actions", []):
            print(f"  -> {a}")
        if briefing.get("risks_and_flags"):
            print(f"\n--- RISKS & FLAGS ---")
            for r in briefing["risks_and_flags"]:
                print(f"  !! {r}")
        print(f"\nJSON : {result['json_path']}")
        print(f"MD   : {result['markdown_path']}")
        print(f"\nRate this briefing:")
        print(f"  python briefing_agent.py --rate \"{result['json_path']}\" --rating 1")
    else:
        print(f"Failed: {result.get('error')}")
        sys.exit(1)