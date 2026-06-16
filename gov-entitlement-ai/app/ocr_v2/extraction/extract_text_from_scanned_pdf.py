# app/ocr_v2/extraction/extract_text_from_scanned_pdf.py

import pytesseract
from app.utils.ocr_utils import deskew_image, should_preprocess, preprocess_image_for_ocr
from pathlib import Path
from app.core.ocr_config import OCRConfig

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

    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(input_pdf_path))
    pages = [page.render(scale=300/72.0).to_pil() for page in doc]

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