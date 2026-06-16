# app/utils/chunk_utils/chunk_debugger.py

import json
import os


def print_chunks(chunks, max_chars=300):

    print("\n" + "="*80)
    print(f"TOTAL CHUNKS: {len(chunks)}")
    print("="*80)

    for i, c in enumerate(chunks):
        print(f"\n--- CHUNK {i+1} ---")
        print(f"ID: {c.get('chunk_id')}")
        print(f"Tokens: {c.get('token_count')}")
        print(f"Type: {c.get('chunk_type')}")
        print(f"Pages: {c.get('page_range')}")
        print(f"Section: {c.get('section_path')}")

        text = c.get("text") or ""
        print(f"\n{text[:max_chars]}...")


def save_chunks_to_json(chunks, document_id, folder="chunk_outputs"):

    doc_folder = os.path.join(folder, f"doc_{document_id}")
    os.makedirs(doc_folder, exist_ok=True)

    file_path = os.path.join(doc_folder, "chunks.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved: {file_path}")