"""
pdf_extractor.py - Government Knowledge Infrastructure | Enhanced Ingestion
─────────────────────────────────────────────────────────────────────────────
Merges advanced extraction intelligence while preserving clean architecture.
Keeps Tesseract OCR pipeline unchanged, Docling only for layout extraction.

MODULARIZED COMPONENTS:
- OCR handling → app.utils.ocr_utils
- Noise filtering → app.utils.noise_utils
- Table serialization → app.utils.table_utils
- Text utilities → app.utils.text_utils
"""

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import TableFormerMode
from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.utils.ocr_utils import create_searchable_pdf
from app.utils.pdf_utils import is_scanned_pdf
from app.utils.table_utils import serialize_table, merge_cross_page_tables
from app.utils.document_structure_utils import is_toc_page

# page health utilities
from app.utils.page_health_utils import (
    evaluate_page_health,
    classify_page_health
)

# Noise utilities
from app.utils.noise_utils import (
    compile_noise_patterns,
    is_noise,
    is_cover_page,
    is_small_artifact
)

# Text utilities
from app.utils.text_utils import (
    detect_language,
    normalize_text,
    count_tokens,
    detect_section_label,
    is_valid_section_label,
    normalize_clause_text,
    correct_ocr_errors,
    is_text_corrupted
)

import re
import logging
import gc
import os
import tempfile
import fitz

from pypdf import PdfReader, PdfWriter


# ──────────────────────────────────────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
)


class PDFExtractor:
    """
    Government-grade PDF extractor for structured knowledge extraction.

    Pipeline:
    1. Detect scanned PDFs
    2. Run OCR if needed
    3. Use Docling for layout extraction
    4. Apply advanced filtering + structure detection
    """

    def __init__(self):

        # Docling converter instance
        self.converter = None

        # Deduplication tracking
        self._seen_keys = set()

        # Section hierarchy breadcrumb
        self._breadcrumb_stack = []

        # Precompiled noise patterns
        self.noise_patterns = compile_noise_patterns()
        
    
    def get_page_index(self, page_file):
        try:
            name = os.path.basename(page_file)
            return int(name.split("_page_")[-1].replace(".pdf", ""))
        except:
            return None
      
    # ─────────────────────────────────────────────────────────
    # Fast Pre-Scan Classification
    # ─────────────────────────────────────────────────────────    
       
    def classify_pages_fast(self, page_files):
        """
        Fast pre-scan classification WITHOUT Docling or OCR.
        Uses PyMuPDF (fitz) to estimate page complexity.
        """

        page_meta = []

        for page_file in page_files:
            try:
                doc = fitz.open(page_file)
                page = doc[0]

                text = page.get_text("text")
                blocks = page.get_text("blocks")

                text_length = len(text)
                block_count = len(blocks)

                # Heuristics
                is_low_text = text_length < 80
                is_dense_layout = block_count > 25

                # Detect numeric-heavy pages (tables)
                digit_ratio = (
                    sum(c.isdigit() for c in text) / max(len(text), 1)
                )

                is_statistical = digit_ratio > 0.3

                # FINAL CLASSIFICATION
                if is_statistical or is_dense_layout:
                    page_type = "heavy"
                elif is_low_text:
                    page_type = "medium"
                else:
                    page_type = "light"

                page_meta.append({
                    "file": page_file,
                    "type": page_type
                })

            except Exception:
                page_meta.append({
                    "file": page_file,
                    "type": "heavy"  # safe fallback
                })

        return page_meta 

    # ─────────────────────────────────────────────────────────
    # PDF PAGE SPLITTING (NEW - for Docling stability)
    # ─────────────────────────────────────────────────────────

    def split_pdf_pages(self, pdf_path):
        """
        Split PDF into single-page PDFs for safer Docling processing using fitz.
        """
        import fitz
        import tempfile
        doc = fitz.open(pdf_path)
        page_files = []

        for i in range(len(doc)):
            tmp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f"_page_{i}.pdf"
            )
            tmp_file.close() # 🔥 CRITICAL FOR WINDOWS: CLOSE THE FILE HANDLE SO FITZ CAN WRITE TO IT!
            
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
            new_doc.save(tmp_file.name)
            new_doc.close()
            page_files.append(tmp_file.name)

        doc.close()
        return page_files

    def _process_single_page(self, page_file):
        try:
            result = self.converter.convert(page_file)

            # Extract page number
            try:
                page_index = self.get_page_index(page_file)
                actual_page_number = page_index + 1
            except Exception:
                actual_page_number = None

            page_elements = self.process_doc(result.document, actual_page_number)

            return page_elements

        except Exception as e:
            logger.warning(f"Parallel processing failed: {page_file}")
            return []
        
    def _process_single_page_with_stats(self, page_file):

        try:
            # Extract page number
            try:
                page_index = self.get_page_index(page_file)
                actual_page_number = page_index + 1
            except Exception:
                actual_page_number = None

            attempts = 0

            while attempts < 2:

                try:
                    logger.info(f"Processing page: {page_file}")

                    result = self.converter.convert(page_file)

                    page_elements = self.process_doc(result.document, actual_page_number)

                    health = evaluate_page_health(page_elements)
                    status = classify_page_health(health)
                    is_corrupt = is_text_corrupted(page_elements)

                    return (page_elements, health, status, is_corrupt, page_file)

                except Exception:
                    attempts += 1

                    logger.warning(
                        f"Page error: {page_file} | attempt {attempts}"
                    )

                    if attempts == 2:
                        logger.warning(f"Skipping page: {page_file}")
                        return None

        except Exception:
            return None
    

    # ─────────────────────────────────────────────────────────
    # DUPLICATE DETECTION
    # ─────────────────────────────────────────────────────────

    def is_duplicate(self, text, element_type):

        normalized = re.sub(r"\s+", " ", text).lower()[:120]

        key = f"{element_type[:2]}|{normalized}"

        if key in self._seen_keys:
            return True

        self._seen_keys.add(key)

        return False


    # ─────────────────────────────────────────────────────────
    # BREADCRUMB HIERARCHY
    # ─────────────────────────────────────────────────────────

    def update_breadcrumb(self, level, label):

        self._breadcrumb_stack = [
            (lvl, txt)
            for lvl, txt in self._breadcrumb_stack
            if lvl < level
        ]

        self._breadcrumb_stack.append((level, label))

        return [txt for _, txt in self._breadcrumb_stack]


    # ─────────────────────────────────────────────────────────
    # NORMALIZE DOCLING LABELS
    # ─────────────────────────────────────────────────────────

    def normalize_label(self, label):

        mapping = {
            "title": "heading",
            "section_header": "heading",
            "list_item": "clause",
            "paragraph": "paragraph",
            "table": "table",
            "caption": "caption",
            "page_header": "page_header",
            "page_footer": "page_footer",
            "footnote": "footnote"
        }

        return mapping.get(label, "paragraph")


    # ─────────────────────────────────────────────────────────
    # LOCATION EXTRACTION
    # ─────────────────────────────────────────────────────────

    def extract_location(self, item):

        page = None
        bbox = None

        if hasattr(item, "prov") and item.prov:

            prov = item.prov[0]

            page = getattr(prov, "page_no", None)

            if hasattr(prov, "bbox") and prov.bbox:

                bbox = {
                    "left": prov.bbox.l,
                    "top": prov.bbox.t,
                    "right": prov.bbox.r,
                    "bottom": prov.bbox.b
                }

        return {"page": page, "bbox": bbox}


    # ─────────────────────────────────────────────────────────
    # PROCESS DOCUMENT
    # ─────────────────────────────────────────────────────────

    def process_doc(self, doc, actual_page_number=None):

        elements = []
        sequence = 0

        current_section = None
        current_breadcrumb = []

        page_texts_map = {}

        # Collect page text for TOC detection
        for item, _ in doc.iterate_items():

            if hasattr(item, "text") and item.text:

                loc = self.extract_location(item)

                page = loc.get("page") or 0

                page_texts_map.setdefault(page, []).append(item.text.strip())

        # Identify TOC / cover pages
        toc_pages = set()

        for page, texts in page_texts_map.items():

            if is_cover_page(texts):
                toc_pages.add(page)
                logger.info(f"Page {page} identified as cover page - skipping")
                continue

            if is_toc_page(texts):
                toc_pages.add(page)
                logger.info(f"Page {page} identified as TOC - skipping")

        # Main extraction
        for item, level in doc.iterate_items():

            label = None

            if hasattr(item, "label"):
                label = item.label.value

            element_type = self.normalize_label(label)

            location = self.extract_location(item)

            # Override Docling page number with real PDF page
            page = actual_page_number if actual_page_number else location.get("page")

            if page in toc_pages:
                continue

            # ─────────────────────────
            # TABLE HANDLING
            # ─────────────────────────

            if element_type == "table":

                table_json = None

                if hasattr(item, "data"):
                    table_json = serialize_table(item.data,
                                                 source_page=page,
                                                 section_path=current_section)

                if not table_json:
                    continue

                nl_text = table_json.get("nl_representation", "")
                

                if not nl_text:
                    continue
                
                nl_text = normalize_text(nl_text)
                nl_text = correct_ocr_errors(nl_text)

                lang = detect_language(nl_text)
                
                ocr_conf = None

                if hasattr(self, "ocr_page_map"):
                    ocr_conf = self.ocr_page_map.get(page)

                    if ocr_conf is None:
                        ocr_conf = self.ocr_page_map.get(page - 1)

                element = {
                    "sequence_order": sequence,
                    "element_type": "table",
                    "element_depth": level,
                    "section_path": current_section,
                    "heading_breadcrumb": list(current_breadcrumb),
                    "content_original": nl_text,
                    "structured_content": table_json,
                    "source_location": location,
                    "token_count": count_tokens(nl_text, lang),
                    "detected_language": lang,
                    "metadata": {"is_table": True,
                                 "docling_label": label,
                                 "page_number": page,
                                 "bbox": location.get("bbox"),
                                 "ocr_confidence": ocr_conf,
                                 "extraction_mode": "ocr" if ocr_conf is not None else "digital"}
                }

                elements.append(element)
                sequence += 1
                continue


            # ─────────────────────────
            # TEXT ELEMENTS
            # ─────────────────────────

            if not hasattr(item, "text"):
                continue

            text = item.text.strip()

            if not text:
                continue

            text = normalize_text(text)
            text = correct_ocr_errors(text)

            if element_type == "clause":
                text = normalize_clause_text(text)

            if is_small_artifact(text):
                continue

            if is_noise(text, element_type, self.noise_patterns):
                continue

            if self.is_duplicate(text, element_type):
                continue

            lang = detect_language(text)

            section_label = detect_section_label(text, element_type)

            if section_label and is_valid_section_label(section_label, text):

                element_type = "section"
                current_section = section_label
                current_breadcrumb = self.update_breadcrumb(level, section_label)

            elif element_type == "heading":

                current_breadcrumb = self.update_breadcrumb(level, text[:80])

            token_count = count_tokens(text, lang)
            
            ocr_conf = None

            if hasattr(self, "ocr_page_map"):
                ocr_conf = self.ocr_page_map.get(page)

                if ocr_conf is None:
                    ocr_conf = self.ocr_page_map.get(page - 1)
                    
            element = {
                "sequence_order": sequence,
                "element_type": element_type,
                "element_depth": level,
                "section_path": current_section,
                "heading_breadcrumb": list(current_breadcrumb),
                "content_original": text,
                "structured_content": None,
                "source_location": location,
                "token_count": token_count,
                "detected_language": lang,
                "metadata": {"docling_label": label,
                "page_number": page,
                "bbox": location.get("bbox"),
                "ocr_confidence": ocr_conf,
                "extraction_mode": "ocr" if ocr_conf is not None else "digital"}
            }

            elements.append(element)

            sequence += 1

        return elements


    # ─────────────────────────────────────────────────────────
    # MAIN EXTRACTION
    # ─────────────────────────────────────────────────────────

    def extract_elements(self, pdf_path):

        elements = []
        
        extraction_stats = {
        "ocr_used": False,
        "weak_pages": 0,
        "failed_pages": 0,
        "docling_errors": 0,
        "pages_processed": 0
    }

        self._seen_keys.clear()
        self._breadcrumb_stack = []

        scanned = is_scanned_pdf(pdf_path)

        if scanned:
            
            extraction_stats["ocr_used"] = True

            logger.info("Scanned PDF detected. Running Tesseract OCR...")

            pdf_path, ocr_stats = create_searchable_pdf(pdf_path)
            
            self.ocr_page_map = {
                p["page"]: p["avg_confidence"]
                for p in ocr_stats["pages"]
            }

            logger.info(
                f"OCR average confidence: {ocr_stats['summary']['avg_confidence']}%"
            )

            logger.info(f"Searchable PDF created: {pdf_path}")

        pipeline_options = PdfPipelineOptions()

        # 🔥 SPEED BOOST FOR TABLES
        pipeline_options.table_structure_options.mode = TableFormerMode.FAST
        
        # 🔥 HARDWARE ACCELERATION (FORCE CPU TO AVOID VRAM CONTENTION WITH OLLAMA)
        pipeline_options.accelerator_options = AcceleratorOptions(
            device=AcceleratorDevice.CPU
        )
        
        logger.info(f"Using accelerator: CPU (forced to avoid VRAM OOM)")
        
        pipeline_options.do_ocr = False

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        try:

            logger.info(f"Splitting PDF into pages: {pdf_path}")

            page_files = self.split_pdf_pages(pdf_path)

            all_elements = []

            # 🔥 STEP 1: CLASSIFY PAGES
            page_meta = self.classify_pages_fast(page_files)

            light_pages = [p["file"] for p in page_meta if p["type"] == "light"]
            medium_pages = [p["file"] for p in page_meta if p["type"] == "medium"]
            heavy_pages = [p["file"] for p in page_meta if p["type"] == "heavy"]

            logger.info(f"Total pages detected: {len(page_files)}")
            logger.info(f"Light pages: {len(light_pages)} | Medium: {len(medium_pages)} | Heavy: {len(heavy_pages)}")

            results_with_index = []

            # 🔥 PROCESS ALL PAGES SEQUENTIALLY TO AVOID MEMORY SPIKES
            for page_file in page_files:
                page_index = self.get_page_index(page_file)
                if page_index is None:
                    continue

                try:
                    result = self._process_single_page_with_stats(page_file)
                    results_with_index.append((page_index, result))
                except Exception as e:
                    logger.warning(f"Page failed: {e}")
                    results_with_index.append((page_index, None))
                    
                       
            results_with_index.sort(key=lambda x: x[0])
            
            results = [res for _, res in results_with_index]
                
            for res in results:

                extraction_stats["pages_processed"] += 1

                if not res:
                    extraction_stats["failed_pages"] += 1
                    continue

                page_elements, health, status, is_corrupt, page_file = res
                
                # new: ocr fallback only for corrupted pages
                if is_corrupt:
                    logger.warning(f"Page {page_file} text appears corrupted - reprocessing with OCR")

                    try:
                        ocr_pdf, ocr_stats = create_searchable_pdf(page_file)

                        # update OCR map for this page
                        self.ocr_page_map = {
                            p["page"]: p["avg_confidence"]
                            for p in ocr_stats["pages"]
                        }

                        # extract correct page number
                        try:
                            page_index = self.get_page_index(page_file)
                            actual_page_number = page_index + 1
                        except:
                            actual_page_number = None

                        result = self.converter.convert(ocr_pdf)

                        page_elements = self.process_doc(
                            result.document,
                            actual_page_number
                        )
                        extraction_stats["ocr_used"] = True
                        
                    except Exception as e:
                        logger.warning(f"OCR reprocessing failed for page {page_file}: {str(e)}. Falling back to original digital extraction.")
                        extraction_stats["failed_pages"] += 1
                        # Do not continue; just fall through to use the original page_elements

                        
                logger.info(
                    f"Page health -> elements={health['element_count']} "
                    f"text_len={health['text_length']} "
                    f"tokens={health['token_count']} "
                    f"tables={health['tables']}"
                )

                if status == "weak":
                    extraction_stats["weak_pages"] += 1

                    logger.warning(
                        f"Weak extraction (elements={health['element_count']} text_len={health['text_length']})"
                    )

                if status == "failed":
                    extraction_stats["failed_pages"] += 1

                    logger.warning("Extraction failed on page")

                if len(page_elements) < 2:
                    logger.warning("Very low elements extracted on page")

                all_elements.extend(page_elements)

                if extraction_stats["pages_processed"] % 5 == 0:
                    gc.collect()

            elements = all_elements
            
            # Merge tables split across pages
            elements = merge_cross_page_tables(elements)

            for f in page_files:
                try:
                    os.remove(f)
                except:
                    pass

            logger.info(f"Extracted {len(elements)} elements")

        except Exception as e:

            logger.warning(f"Document conversion failed: {e}")

        return elements, extraction_stats