# app/ocr_v2/extraction/extract_text_from_scanned_pdf.py

import pytesseract
from app.utils.ocr_utils import deskew_image, should_preprocess, preprocess_image_for_ocr
from pathlib import Path
from app.core.ocr_config import OCRConfig
import fitz
from PIL import Image

#### ocr - V2: Faster raw text extraction without PDF output, for quick content analysis and debugging.



def extract_text_from_scanned_pdf(input_pdf_path, debug=True):
    """
    Extract raw OCR text from scanned PDF using Tesseract.
    
    Returns:
        {
            "pages": [...],
            "summary": {...}
        }
    """

    input_pdf_path = Path(input_pdf_path)

    doc = fitz.open(input_pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    extracted_pages = []

    for i, page in enumerate(pages):

        # Deskew
        page = deskew_image(page)

        # Preprocessing decision
        applied_preprocessing = should_preprocess(page)

        if applied_preprocessing:
            processed_page = preprocess_image_for_ocr(page)
        else:
            processed_page = page

        # OCR text extraction
        raw_text = pytesseract.image_to_string(
            processed_page,
            lang=OCRConfig.OCR_LANGUAGES,
            config="--psm 6"
        )

        extracted_pages.append({
            "page": i + 1,
            "raw_text": raw_text,
            "preprocessed": applied_preprocessing
        })

        if debug:
            print(f"[OCR] Page {i+1} extracted")

    return {
        "pages": extracted_pages,
        "summary": {
            "total_pages": len(extracted_pages)
        }
    }