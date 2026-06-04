"""
metadata_agent.py
-----------------
AGENTIC PDF metadata extractor for NemhemAI government document system.

Unlike the scripted version, this agent:
- DECIDES how to handle each PDF (scanned, Hindi, missing fields, etc.)
- USES TOOLS: OCR, translation, web search, validation
- SELF-CORRECTS: retries with different strategy if extraction fails
- REMEMBERS: learns patterns across documents
- HANDLES EDGE CASES: scanned PDFs, regional languages, forms, missing data

Requirements:
    pip install praisonaiagents pymupdf pytesseract pillow requests ollama

Usage:
    python metadata_agent.py path/to/document.pdf
    python metadata_agent.py path/to/pdf_folder/

Or import:
    from metadata_agent import run_metadata_agent
    result = run_metadata_agent("path/to/document.pdf")
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_MODEL    = os.getenv("METADATA_MODEL", "llama3.1:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MAX_PDF_CHARS   = 8000
MEMORY_FILE     = os.path.join(os.path.dirname(__file__), "metadata_agent_memory.json")

# ── Metadata Schema ─────────────────────────────────────────────────────────────
SCHEMA = {
    "title":             "Full document title as stated in the document",
    "document_number":   "Reference/document number. Infer from content if not explicit.",
    "issuing_authority": "Organization or government body that issued this document",
    "department_code":   "Short department or ministry code. Infer if not explicit.",
    "jurisdiction":      "One of: central | state | local | international",
    "state_origin":      "State or region this document originates from. Use NA if not applicable.",
    "document_type":     "One of: manual | policy | circular | notification | report | form | guideline | act | order",
    "security_level":    "One of: public | restricted | confidential",
    "primary_language":  "ISO 639-1 code (e.g. en, hi, mr, ta, te, bn)",
    "version_label":     "Version number or year label. Use NA if not found."
}

ALLOWED_VALUES = {
    "jurisdiction":  {"central", "state", "local", "international"},
    "document_type": {"manual", "policy", "circular", "notification", "report", "form", "guideline", "act", "order"},
    "security_level": {"public", "restricted", "confidential"},
}

# ══════════════════════════════════════════════════════════════════════════════
# TOOLS — each tool is a function the agent can call
# ══════════════════════════════════════════════════════════════════════════════

def tool_extract_text(pdf_path: str, max_chars: int = MAX_PDF_CHARS) -> dict:
    """
    TOOL: Extract text from PDF using pymupdf.
    Returns text content and whether PDF appears to be scanned (image-based).
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text_parts = []
        total_chars = 0
        has_images = False

        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            text_parts.append(page_text)
            total_chars += len(page_text)
            # Check if page has images (sign of scanned doc)
            if page.get_images():
                has_images = True
            if total_chars >= max_chars:
                break

        doc.close()
        full_text = "\n".join(text_parts)[:max_chars]
        is_scanned = len(full_text.strip()) < 100 and has_images

        return {
            "success": True,
            "text": full_text,
            "char_count": len(full_text),
            "is_scanned": is_scanned,
            "has_images": has_images,
            "pages_read": page_num + 1
        }
    except Exception as e:
        return {"success": False, "error": str(e), "text": "", "is_scanned": False}


def tool_ocr_pdf(pdf_path: str, language: str = "eng+hin") -> dict:
    """
    TOOL: OCR a scanned PDF using Tesseract.
    Used when tool_extract_text returns is_scanned=True.
    Supports English, Hindi, Marathi, and other Indian languages.
    """
    try:
        import fitz
        from PIL import Image
        import pytesseract
        import io

        doc = fitz.open(pdf_path)
        all_text = []

        for page_num, page in enumerate(doc):
            if page_num >= 5:  # OCR first 5 pages max
                break
            # Render page to image at 300 DPI
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            # Run OCR
            text = pytesseract.image_to_string(img, lang=language)
            all_text.append(text)

        doc.close()
        full_text = "\n".join(all_text)[:MAX_PDF_CHARS]

        return {
            "success": True,
            "text": full_text,
            "char_count": len(full_text),
            "ocr_language": language
        }
    except Exception as e:
        return {"success": False, "error": str(e), "text": ""}


def tool_detect_language(text: str) -> dict:
    """
    TOOL: Detect primary language of document text.
    Uses character frequency analysis — no external API needed.
    """
    if not text:
        return {"language": "en", "confidence": 0.0}

    # Count Devanagari characters (Hindi, Marathi, Sanskrit, Nepali)
    devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    # Count Bengali characters
    bengali = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    # Count Tamil characters
    tamil = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    # Count Telugu characters
    telugu = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    # Count Gujarati characters
    gujarati = sum(1 for c in text if '\u0A80' <= c <= '\u0AFF')
    # Count Arabic characters (Urdu)
    arabic = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    # ASCII letters (likely English)
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())

    total = len(text)
    scores = {
        "hi": devanagari / total if total > 0 else 0,
        "bn": bengali / total if total > 0 else 0,
        "ta": tamil / total if total > 0 else 0,
        "te": telugu / total if total > 0 else 0,
        "gu": gujarati / total if total > 0 else 0,
        "ur": arabic / total if total > 0 else 0,
        "en": ascii_letters / total if total > 0 else 0,
    }

    detected = max(scores, key=scores.get)
    confidence = scores[detected]

    # Mixed document — if devanagari and english both significant
    if scores["hi"] > 0.1 and scores["en"] > 0.3:
        detected = "hi"  # Bilingual — mark as Hindi primary

    return {
        "language": detected,
        "confidence": round(confidence, 2),
        "scores": {k: round(v, 3) for k, v in scores.items()}
    }


def tool_search_issuing_authority(clues: str) -> dict:
    """
    TOOL: Search for issuing authority when not found in document text.
    Uses DuckDuckGo — no API key needed.
    """
    try:
        import urllib.request
        import urllib.parse
        import re

        query = f"India government department {clues} issuing authority circular"
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract text snippets from results
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)
        clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]

        return {
            "success": True,
            "results": clean,
            "query": query
        }
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


def tool_validate_metadata(metadata: dict) -> dict:
    """
    TOOL: Validate metadata against schema and fix invalid values.
    Returns corrected metadata + list of issues found.
    """
    issues = []
    corrected = dict(metadata)

    # Check all required fields exist
    for key in SCHEMA:
        if key not in corrected or not str(corrected.get(key, "")).strip():
            corrected[key] = "NA"
            issues.append(f"Missing field: {key} — set to NA")

    # Validate enum fields
    for field, valid in ALLOWED_VALUES.items():
        val = str(corrected.get(field, "")).lower().strip()
        if val not in valid:
            default = "public" if field == "security_level" else sorted(valid)[0]
            issues.append(f"Invalid {field}='{val}' — corrected to '{default}'")
            corrected[field] = default
        else:
            corrected[field] = val

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "corrected_metadata": corrected
    }


def tool_load_memory() -> dict:
    """
    TOOL: Load agent memory — patterns learned from previous extractions.
    Helps agent make better decisions for similar documents.
    """
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "total_processed": 0,
        "department_patterns": {},
        "state_patterns": {},
        "common_authorities": [],
        "extraction_history": []
    }


def tool_save_memory(memory: dict, new_metadata: dict) -> dict:
    """
    TOOL: Update agent memory with new extraction results.
    Agent learns patterns for future extractions.
    """
    try:
        # Update counters
        memory["total_processed"] = memory.get("total_processed", 0) + 1

        # Learn department patterns
        dept = new_metadata.get("department_code", "")
        auth = new_metadata.get("issuing_authority", "")
        state = new_metadata.get("state_origin", "")

        if dept and dept != "NA":
            memory["department_patterns"][dept] = memory["department_patterns"].get(dept, 0) + 1

        if state and state != "NA":
            memory["state_patterns"][state] = memory["state_patterns"].get(state, 0) + 1

        if auth and auth != "NA" and auth not in memory["common_authorities"]:
            memory["common_authorities"].append(auth)
            memory["common_authorities"] = memory["common_authorities"][-50:]  # Keep last 50

        # Save history (last 20 extractions)
        history_entry = {
            "title": new_metadata.get("title", ""),
            "department": dept,
            "state": state,
            "type": new_metadata.get("document_type", "")
        }
        memory.setdefault("extraction_history", []).append(history_entry)
        memory["extraction_history"] = memory["extraction_history"][-20:]

        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)

        return {"success": True, "total_processed": memory["total_processed"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_call_ollama(text: str, context: str = "", memory_hints: str = "") -> dict:
    """
    TOOL: Call local Ollama model to extract metadata from document text.
    Includes memory hints from previous extractions to improve accuracy.
    """
    try:
        import requests

        memory_section = f"\nMEMORY HINTS FROM PREVIOUS DOCUMENTS:\n{memory_hints}\n" if memory_hints else ""
        context_section = f"\nADDITIONAL CONTEXT:\n{context}\n" if context else ""

        prompt = f"""You are a government document metadata extraction agent for India.

Extract metadata from the document text below and return ONLY a valid JSON object with these exact keys:

{json.dumps(SCHEMA, indent=2)}

STRICT RULES:
- Return ONLY the JSON object. No markdown, no backticks, no explanation.
- Every field must have a value. Use "NA" if not found.
- jurisdiction: must be one of: central, state, local, international
- document_type: must be one of: manual, policy, circular, notification, report, form, guideline, act, order  
- security_level: must be one of: public, restricted, confidential (default: public)
- For Indian government documents: infer department_code from ministry/department names
- Common codes: MoHFW (Health), MAHA-IT (Maharashtra IT), DEA (Economic Affairs), MoE (Education)
{memory_section}{context_section}

DOCUMENT TEXT:
{text}"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "num_predict": 1000}
            },
            timeout=300
        )

        if response.status_code != 200:
            return {"success": False, "error": f"Ollama HTTP {response.status_code}"}

        raw = response.json().get("response", "").strip()

        # Extract JSON from response
        if "{" in raw and "}" in raw:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            json_str = raw[start:end]
            metadata = json.loads(json_str)
            return {"success": True, "metadata": metadata, "raw": raw}

        return {"success": False, "error": "No JSON found in response", "raw": raw}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# THE AGENT — orchestrates tools with decision-making logic
# ══════════════════════════════════════════════════════════════════════════════

class MetadataAgent:
    """
    Agentic PDF metadata extractor.
    
    Unlike a simple script, this agent:
    1. PERCEIVES: Analyses the PDF to understand what it's dealing with
    2. DECIDES: Chooses the right strategy (OCR vs text, language detection, etc.)
    3. ACTS: Uses tools in the right order
    4. REFLECTS: Validates output, self-corrects if needed
    5. LEARNS: Updates memory with patterns from each extraction
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.memory = tool_load_memory()
        logger.info(f"Agent initialized — model={model}, memory={self.memory.get('total_processed', 0)} docs processed")

    def _get_memory_hints(self) -> str:
        """Generate memory hints for Ollama based on past extractions."""
        hints = []
        if self.memory.get("department_patterns"):
            top_depts = sorted(self.memory["department_patterns"].items(), key=lambda x: x[1], reverse=True)[:5]
            hints.append(f"Common departments seen: {', '.join(d for d, _ in top_depts)}")
        if self.memory.get("common_authorities"):
            hints.append(f"Known authorities: {', '.join(self.memory['common_authorities'][:5])}")
        if self.memory.get("state_patterns"):
            top_states = sorted(self.memory["state_patterns"].items(), key=lambda x: x[1], reverse=True)[:3]
            hints.append(f"Common states: {', '.join(s for s, _ in top_states)}")
        return "\n".join(hints)

    def run(self, pdf_path: str, output_path: Optional[str] = None) -> dict:
        """
        Main agent loop — processes a single PDF agenically.
        
        Agent reasoning steps:
        1. Extract text → detect if scanned
        2. If scanned → use OCR tool
        3. Detect language → set OCR language accordingly  
        4. Extract metadata with Ollama + memory hints
        5. If missing authority → search web
        6. Validate + self-correct
        7. Save output + update memory
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return {"success": False, "error": f"PDF not found: {pdf_path}"}

        if output_path is None:
            output_path = pdf_path.with_suffix(".json")
        output_path = Path(output_path)

        logger.info(f"🤖 Agent processing: {pdf_path.name}")

        # ── STEP 1: PERCEIVE — Extract text, understand document type ──────────
        logger.info("Step 1: Extracting text...")
        text_result = tool_extract_text(str(pdf_path))

        if not text_result["success"]:
            logger.error(f"Text extraction failed: {text_result.get('error')}")
            return {"success": False, "error": text_result.get("error")}

        text = text_result["text"]
        is_scanned = text_result["is_scanned"]

        # ── STEP 2: DECIDE — Is this a scanned PDF? ────────────────────────────
        if is_scanned:
            logger.info("🔍 Agent decision: Scanned PDF detected → switching to OCR")

            # First detect language from any available text
            lang_result = tool_detect_language(text)
            ocr_lang = "eng"
            if lang_result["language"] in ["hi", "mr"]:
                ocr_lang = "eng+hin"
            elif lang_result["language"] == "bn":
                ocr_lang = "eng+ben"
            elif lang_result["language"] == "ta":
                ocr_lang = "eng+tam"
            elif lang_result["language"] == "te":
                ocr_lang = "eng+tel"
            elif lang_result["language"] == "gu":
                ocr_lang = "eng+guj"

            logger.info(f"Step 2: Running OCR with language={ocr_lang}")
            ocr_result = tool_ocr_pdf(str(pdf_path), language=ocr_lang)

            if ocr_result["success"] and ocr_result["text"].strip():
                text = ocr_result["text"]
                logger.info(f"OCR successful — {ocr_result['char_count']} characters extracted")
            else:
                logger.warning(f"OCR failed: {ocr_result.get('error')} — using original text")

        # ── STEP 3: DETECT LANGUAGE ────────────────────────────────────────────
        logger.info("Step 3: Detecting language...")
        lang_result = tool_detect_language(text)
        detected_lang = lang_result["language"]
        logger.info(f"Language detected: {detected_lang} (confidence={lang_result['confidence']})")

        # ── STEP 4: EXTRACT METADATA with memory hints ─────────────────────────
        logger.info("Step 4: Calling Ollama for metadata extraction...")
        memory_hints = self._get_memory_hints()
        context = f"Document language: {detected_lang}"
        if is_scanned:
            context += " (scanned document, OCR was used)"

        extraction_result = tool_call_ollama(text, context=context, memory_hints=memory_hints)

        if not extraction_result["success"]:
            logger.warning(f"First extraction attempt failed: {extraction_result.get('error')}")
            # SELF-CORRECT: retry with simplified prompt
            logger.info("Step 4b: Retrying with simplified extraction...")
            extraction_result = tool_call_ollama(
                text[:3000],  # Use less text
                context="Simplified retry - extract basic metadata only"
            )

        if not extraction_result["success"]:
            logger.error("Both extraction attempts failed")
            metadata = {k: "NA" for k in SCHEMA}
        else:
            metadata = extraction_result["metadata"]

        # ── STEP 5: DECIDE — Search web if authority missing ───────────────────
        if metadata.get("issuing_authority", "NA") == "NA":
            logger.info("Step 5: Authority missing → searching web for clues...")
            clues = f"{metadata.get('title', '')} {metadata.get('department_code', '')} India"
            search_result = tool_search_issuing_authority(clues)
            if search_result["success"] and search_result["results"]:
                # Feed search results back to Ollama for better extraction
                web_context = "Web search results for issuing authority:\n" + "\n".join(search_result["results"])
                retry = tool_call_ollama(text[:3000], context=web_context)
                if retry["success"]:
                    if retry["metadata"].get("issuing_authority", "NA") != "NA":
                        metadata["issuing_authority"] = retry["metadata"]["issuing_authority"]
                        logger.info(f"Authority found via web search: {metadata['issuing_authority']}")

        # ── STEP 6: VALIDATE + SELF-CORRECT ────────────────────────────────────
        logger.info("Step 6: Validating metadata...")
        validation = tool_validate_metadata(metadata)
        metadata = validation["corrected_metadata"]

        if validation["issues"]:
            logger.info(f"Validation fixed {len(validation['issues'])} issues: {validation['issues']}")

        # Override language with detected value if model got it wrong
        if detected_lang and lang_result["confidence"] > 0.3:
            metadata["primary_language"] = detected_lang

        # ── STEP 7: SAVE OUTPUT + UPDATE MEMORY ───────────────────────────────
        logger.info("Step 7: Saving metadata and updating memory...")

        with open(str(output_path), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        tool_save_memory(self.memory, metadata)

        logger.info(f"✅ Done — {output_path.name}")

        return {
            "success": True,
            "metadata": metadata,
            "output_path": str(output_path),
            "was_scanned": is_scanned,
            "language_detected": detected_lang,
            "validation_issues": validation["issues"]
        }

    def run_batch(self, directory: str) -> dict:
        """
        Batch process all PDFs in a directory.
        Agent processes each file and updates memory continuously —
        getting smarter as it processes more documents.
        """
        directory = Path(directory)
        if not directory.is_dir():
            return {"success": False, "error": f"Not a directory: {directory}"}

        pdf_files = sorted(directory.glob("*.pdf"))
        if not pdf_files:
            return {"success": False, "error": "No PDFs found"}

        logger.info(f"🤖 Agent batch processing {len(pdf_files)} PDFs...")
        results = {}

        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{len(pdf_files)}] {pdf_path.name}")
            try:
                result = self.run(str(pdf_path))
                results[pdf_path.name] = result
            except Exception as e:
                logger.error(f"Failed: {pdf_path.name} — {e}")
                results[pdf_path.name] = {"success": False, "error": str(e)}

        success_count = sum(1 for r in results.values() if r.get("success"))
        logger.info(f"Batch complete — {success_count}/{len(pdf_files)} succeeded")
        logger.info(f"Agent memory updated — total processed: {self.memory.get('total_processed', 0)}")

        return {
            "success": True,
            "total": len(pdf_files),
            "succeeded": success_count,
            "results": results
        }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — for importing into NemhemAI backend
# ══════════════════════════════════════════════════════════════════════════════

def run_metadata_agent(pdf_path: str, output_path: Optional[str] = None) -> dict:
    """
    Main entry point — run the metadata agent on a single PDF.
    
    Args:
        pdf_path:    Path to PDF file
        output_path: Where to save JSON (default: same dir as PDF)
    
    Returns:
        {
            "success": True/False,
            "metadata": {...},       # The extracted metadata
            "output_path": "...",    # Where JSON was saved
            "was_scanned": True/False,
            "language_detected": "en/hi/mr/...",
            "validation_issues": [...]
        }
    
    Example:
        from metadata_agent import run_metadata_agent
        result = run_metadata_agent("path/to/document.pdf")
        if result["success"]:
            print(result["metadata"]["title"])
    """
    agent = MetadataAgent()
    return agent.run(pdf_path, output_path)


def run_metadata_agent_batch(directory: str) -> dict:
    """Batch process all PDFs in a directory."""
    agent = MetadataAgent()
    return agent.run_batch(directory)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python metadata_agent.py <path/to/file.pdf>")
        print("  python metadata_agent.py <path/to/pdf_folder/>")
        print("  python metadata_agent.py <path/to/file.pdf> --model llama3.1:latest")
        sys.exit(1)

    target = Path(sys.argv[1])

    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        OLLAMA_MODEL = sys.argv[idx + 1]

    agent = MetadataAgent(model=OLLAMA_MODEL)

    if target.is_dir():
        result = agent.run_batch(str(target))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif target.is_file():
        result = agent.run(str(target))
        if result["success"]:
            print(json.dumps(result["metadata"], indent=2, ensure_ascii=False))
            print(f"\n✅ Saved to: {result['output_path']}")
            print(f"🌐 Language: {result['language_detected']}")
            print(f"🔍 Scanned PDF: {result['was_scanned']}")
            if result["validation_issues"]:
                print(f"⚠️  Issues fixed: {result['validation_issues']}")
        else:
            print(f"❌ Failed: {result.get('error')}")
            sys.exit(1)
    else:
        print(f"Error: path not found — {target}")
        sys.exit(1)