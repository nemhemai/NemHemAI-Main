# app/generation/citation_builder.py
import re 
BASE_URL = "http://localhost:8000/docs"

def extract_first_page(page_range):
    if isinstance(page_range, list) and page_range:
        return page_range[0]

    if isinstance(page_range, str):
        nums = re.findall(r"\d+", page_range)
        if nums:
            return int(nums[0])

    return 1

def format_page_range(page_range):
    """
    Convert [15,16] → "15, 16"
    or "1516" → "15, 16"
    """
    if isinstance(page_range, list):
        return ", ".join(map(str, page_range))

    if isinstance(page_range, str):
        # handle "1516" → split every 2 digits
        if page_range.isdigit() and len(page_range) > 2:
            return ", ".join([page_range[i:i+2] for i in range(0, len(page_range), 2)])

    return str(page_range or "N/A")


def build_citations(chunks: list[dict], source_ids: list[int]) -> list[dict]:
    citations = []

    for idx in source_ids:
        if idx - 1 < len(chunks):
            c = chunks[idx - 1]

            doc_name = c.get("document_name") or f"Doc {c.get('document_id')}"
            page_range = c.get("page_range")

            # 🔥 extract first page
            page = extract_first_page(page_range)

            # 🔥 get file_name from hydration (IMPORTANT)
            file_name = c.get("file_name")

            # 🔥 build clickable URL
            url = None
            if file_name:
                url = f"{BASE_URL}/{file_name}#page={page}"

            citations.append({
                "document_name": doc_name,
                "section_path": c.get("section_path"),

                # ✅ NEW FIELDS
                "page": page,
                "url": url,

                # keep for backward compatibility
                "page_range": format_page_range(page_range),

                "snippet": (c.get("text") or "")[:300]
            })

    return citations
