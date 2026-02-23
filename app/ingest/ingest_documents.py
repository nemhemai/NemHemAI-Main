import os
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_core.documents import Document

from app.config.settings import BASE_DIR
from app.retrieval.vectorstore import get_vectorstore
from app.utils.id_generator import generate_section_id
from app.contracts.metadata_contract import validate_metadata


# =========================================================
# 🔹 Recursive paragraph extractor
# =========================================================

def extract_paragraph_text(para):

    if isinstance(para, str):
        return para

    if isinstance(para, dict):
        text = ""

        if "text" in para:
            text += para["text"] + "\n"

        if "contains" in para:
            for sub in para["contains"].values():
                text += extract_paragraph_text(sub) + "\n"

        return text.strip()

    return ""


# =========================================================
# 🔹 Parse Legal JSON
# =========================================================

def parse_legal_json(file_path):

    documents = []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    act_title = data.get("Act Title", "Unknown Act")
    act_id = data.get("Act ID", "Unknown_ID")

    section_ids_seen = set()

    # =====================================================
    # CASE 1 → JSON HAS PARTS
    # =====================================================

    if "Parts" in data:

        for part in data.get("Parts", {}).values():

            part_name = part.get("Name", "Unknown Part")

            for section_number, section in part.get("Sections", {}).items():

                section_heading = section.get("heading", "")
                paragraphs = section.get("paragraphs", {})

                full_text = f"{section_number} {section_heading}\n\n"

                for para in paragraphs.values():
                    full_text += extract_paragraph_text(para) + "\n"

                if not full_text.strip():
                    continue

                section_id = generate_section_id(
                    act_id=act_id,
                    section_number=section_number
                )

                if section_id in section_ids_seen:
                    raise ValueError(f"Duplicate section_id detected: {section_id}")

                section_ids_seen.add(section_id)

                documents.append(
                    Document(
                        page_content=full_text.strip(),
                        metadata={
                            "act_title": act_title,
                            "act_id": act_id,
                            "section_id": section_id,
                            "hierarchy_type": "part",
                            "hierarchy_name": part_name,
                            "section_number": section_number,
                            "section_heading": section_heading,
                            "authority_level": "statutory",
                            "source_type": "json",
                            "source": file_path,
                        },
                    )
                )

    # =====================================================
    # CASE 2 → JSON HAS CHAPTERS
    # =====================================================

    elif "Chapters" in data:

        for chapter in data.get("Chapters", {}).values():

            chapter_name = chapter.get("Name", "Unknown Chapter")

            for section_number, section in chapter.get("Sections", {}).items():

                section_heading = section.get("heading", "")
                paragraphs = section.get("paragraphs", {})

                full_text = f"{section_number} {section_heading}\n\n"

                for para in paragraphs.values():
                    full_text += extract_paragraph_text(para) + "\n"

                if not full_text.strip():
                    continue

                section_id = generate_section_id(
                    act_id=act_id,
                    section_number=section_number
                )

                if section_id in section_ids_seen:
                    raise ValueError(f"Duplicate section_id detected: {section_id}")

                section_ids_seen.add(section_id)

                documents.append(
                    Document(
                        page_content=full_text.strip(),
                        metadata={
                            "act_title": act_title,
                            "act_id": act_id,
                            "section_id": section_id,
                            "hierarchy_type": "chapter",
                            "hierarchy_name": chapter_name,
                            "section_number": section_number,
                            "section_heading": section_heading,
                            "authority_level": "statutory",
                            "source_type": "json",
                            "source": file_path,
                        },
                    )
                )

    return documents


# =========================================================
# 🔹 MAIN INGESTION FUNCTION (API READY)
# =========================================================

def run_ingestion():

    print("📂 BASE_DIR:", BASE_DIR)

    vectorstore = get_vectorstore()

    if vectorstore.count() > 0:
        raise Exception("❌ Vector store not empty. Preventing duplicate ingestion.")

    print("✅ Vector store empty. Safe to ingest.")

    # =====================================================
    # 1️⃣ LOAD PDFs
    # =====================================================

    pdf_loader = DirectoryLoader(
        path=os.path.join(BASE_DIR, "data", "pdf_files"),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
    )

    pdf_docs = pdf_loader.load()

    for doc in pdf_docs:
        doc.metadata.update(
            {
                "source_type": "pdf",
                "authority_level": "contextual",
                "document_class": "reference",
                "page_number": doc.metadata.get("page", None),
            }
        )

    print(f"📄 PDF docs loaded: {len(pdf_docs)}")

    # =====================================================
    # 2️⃣ LOAD JSON FILES
    # =====================================================

    json_dir = os.path.join(BASE_DIR, "data", "json_files")
    json_docs = []

    for file in os.listdir(json_dir):
        if file.endswith(".json"):
            file_path = os.path.join(json_dir, file)
            print(f"📄 Parsing JSON file: {file}")
            json_docs.extend(parse_legal_json(file_path))

    print(f"🧾 JSON sections extracted: {len(json_docs)}")

    documents = pdf_docs + json_docs
    print(f"📚 Total raw documents: {len(documents)}")

    # =====================================================
    # 3️⃣ CHUNKING
    # =====================================================

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
    )

    chunks = text_splitter.split_documents(documents)

    print(f"✂️ Total chunks created: {len(chunks)}")

    # 🔒 STRICT METADATA VALIDATION
    for chunk in chunks:
        validate_metadata(chunk.metadata)

    # =====================================================
    # 4️⃣ INSERT INTO VECTOR STORE
    # =====================================================

    BATCH_SIZE = 500

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        print(f"➡️ Inserting batch {i // BATCH_SIZE + 1}")
        vectorstore.add_documents(batch)

    final_count = vectorstore.count()

    print("✅ INGESTION COMPLETE")
    print("📦 Final document count:", final_count)

    return {
        "pdf_documents": len(pdf_docs),
        "json_sections": len(json_docs),
        "total_chunks": len(chunks),
        "vectorstore_count": final_count,
    }


# =========================================================
# 🔹 CLI ENTRY
# =========================================================

if __name__ == "__main__":
    result = run_ingestion()
    print("📊 Ingestion Summary:", result)