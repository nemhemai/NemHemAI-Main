Ingestion Module Documentation (app/ingestion)
1. Overview

The ingestion module is the entry point of the Hybrid RAG pipeline.

It is responsible for:
    Registering documents into the system
    Extracting structured content from raw PDFs
    Cleaning, validating, and organizing extracted data
    Inserting structured elements into the database

This module transforms raw documents → structured, validated, machine-understandable data.

2. Architecture & Flow

End-to-End Flow
    PDF Input
        ↓
    document_registry.py
        ↓
    pdf_extractor.py
        ↓
    element validation & cleaning
        ↓
    element_ingestor.py
        ↓
    document_elements table

3. Submodules Breakdown

3.1 Document Registration (document_registry.py)

Purpose
    Registers document metadata into the documents table
    Prevents duplicate ingestion using SHA256 checksum

Key Design Decisions
    1. SHA256-Based Deduplication
        checksum = calculate_sha256(file_path)
    
Why:
    Guarantees uniqueness of files
    Prevents redundant processing

Why not filename-based deduplication?
    Same file can have different names
    Not reliable

    2. Pre-Insertion Duplicate Check
        SELECT document_id FROM documents WHERE file_checksum = %s
    
Why:
    Avoids unnecessary processing pipeline execution
    Saves compute (OCR + extraction is expensive)

    3. Metadata-Driven Insert
        Uses flexible metadata.get() pattern
        Supports dynamic ingestion inputs

Advantages
    Prevents duplicate uploads efficiently
    Lightweight validation before heavy processing
    Clean separation of metadata and content

Limitations
    No strict validation of metadata fields
    Uses generic Exception instead of typed errors
    No logging framework (uses print)

3.2 PDF Extraction Engine (pdf_extractor.py)

Purpose
    Converts raw PDFs into structured elements

Handles both:
    Digital PDFs
    Scanned PDFs (via OCR)

Core Pipeline
    PDF
    ↓
Scan Detection
    ↓
OCR (if needed)
    ↓
Docling Layout Extraction
    ↓
Noise Filtering
    ↓
Structure Detection
    ↓
Element Generation

Key Technologies Used

1. Docling (Layout Extraction)

Why used:
    Extracts structured document layout (headings, tables, paragraphs)

Why not alternatives?
| Alternative     | Reason Not Used            |
| --------------- | -------------------------- |
| PyMuPDF only    | No structure understanding |
| pdfplumber      | Weak table handling        |
| Tesseract alone | No layout intelligence     |

2. Tesseract OCR

Used via:
    create_searchable_pdf()

Why:
    Converts scanned PDFs into machine-readable format

3. PyMuPDF (fitz)

Role:
    Fast page-level heuristics

Used for:
    Page classification
    Complexity estimation

4. Multithreading (ThreadPoolExecutor)

Why:
    Parallel processing for performance

Strategy:
| Page Type | Processing Mode              |
| --------- | ---------------------------- |
| Light     | Parallel (3 threads)         |
| Medium    | Limited parallel (2 threads) |
| Heavy     | Sequential                   |


5. Custom Utility Layer
    Noise filtering
    OCR correction
    Language detection
    Token counting
    Table serialization

Advanced Design Features

    1. Adaptive Page Processing
        light / medium / heavy classification

Why:
    Prevents system overload
    Optimizes performance dynamically

2. OCR Fallback for Corrupted Pages
    Detects corrupted text
    Reprocesses only those pages

Impact:
    Improves extraction quality
    Avoids full reprocessing

    3. Breadcrumb-Based Context Tracking
        heading_breadcrumb
            Maintains hierarchical structure
            Critical for RAG context
        
4. Duplicate Element Detection
    Prevents repeated content
    Uses normalized text hashing

5. Table Intelligence

Converts tables into:
    Structured JSON
    Natural language representation

Advantages
    Handles both scanned and digital PDFs
    Highly optimized for performance
    Maintains document structure
    Robust against OCR noise
    Supports multilingual extraction

Limitations
    High complexity → harder to debug
    Heavy dependency on Docling
    Memory-intensive for large PDFs
    Heuristic-based classification may fail

3.3 Element Ingestion (element_ingestor.py)

Purpose
    Inserts extracted elements into document_elements table

Key Design Decisions

    1. Bulk Insert using execute_values
        execute_values(cur, query, rows)
    
Why:
    Much faster than row-by-row insert
    Critical for large documents

    2. JSON Handling with psycopg2.extras.Json
        Ensures correct JSONB insertion
        Avoids serialization issues

    3. Conflict Handling
        ON CONFLICT (element_id) DO NOTHING
    
Why:
    Prevents duplicate insertion
    Enables idempotent ingestion

    4. Data Normalization Fixes
        Ensures:
            heading_breadcrumb is always list
            structured_content is valid JSON
            Table metadata extracted properly
    
Advantages
    High-performance insertion
    Idempotent design
    Handles structured + unstructured data

Limitations
    No batching limits (could overload memory)
    No retry logic
    Silent failures possible

4. Design Strategies

4.1 Multi-Stage Ingestion Pipeline
    Registration → Extraction → Storage

Benefit:
    Modular debugging
    Clear pipeline boundaries

4.2 Quality-Aware Extraction
    Tracks:
        OCR confidence
        Page health
        Corruption detection
    
4.3 Hybrid Content Handling
    Text + Tables + Metadata

4.4 Performance Optimization Strategy
    Parallel processing
    Page classification
    Bulk DB insertion

5. Advantages
    Highly scalable ingestion pipeline
    Supports real-world noisy documents
    Maintains traceability
    Optimized for performance
    Handles multilingual government data

6. Limitations / Trade-offs (Critical)

❌ 6.1 Over-Engineering Risk
    Complex pipeline → harder maintenance

❌ 6.2 Weak Error Handling
    Uses print instead of logging
    No retry mechanisms

❌ 6.3 Dependency Risk
    Heavy reliance on Docling

❌ 6.4 No Schema Validation
    Metadata not strictly validated

❌ 6.5 Memory Usage
    Large PDFs may cause high memory consumption

7. Alternatives & Trade-offs

Extraction
| Option            | Pros                  | Cons                  |
| ----------------- | --------------------- | --------------------- |
| Docling (current) | Structured extraction | Complex               |
| pdfplumber        | Simple                | Limited structure     |
| PyMuPDF           | Fast                  | No semantic structure |

OCR
| Option        | Pros          | Cons           |
| ------------- | ------------- | -------------- |
| Tesseract     | Free          | Lower accuracy |
| Google Vision | High accuracy | Paid           |
| AWS Textract  | Structured    | Expensive      |

8. Future Improvements

High Priority
    Add structured logging
    Add retry mechanisms
    Validate metadata before insertion

Medium Priority
    Optimize memory usage
    Add batching for insertion
    Improve page classification heuristics

Advanced
    Distributed ingestion pipeline
    GPU-based OCR
    Smart chunk-aware extraction

9. Key Takeaways
This module is technically strong and feature-rich

Core strength lies in:
    Intelligent extraction
    Performance optimization
    Noise handling

However:
    Complexity is high
    Needs better production hardening

10. Non-Technical Summary (For Stakeholders)
This module reads government documents and converts them into structured data

It ensures:
    Even scanned documents can be understood
    Data is cleaned and organized properly
    Information is ready for AI-based search

It acts as the foundation for building a reliable AI knowledge system

Direct Assessment
    Design quality: Very High
    Complexity: High
    Production readiness: Medium (needs hardening)