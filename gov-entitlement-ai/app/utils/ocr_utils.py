# app/utils/ocr_utils.py

import pytesseract
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pytesseract import Output
from app.core.ocr_config import OCRConfig
import statistics
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

OCRConfig.configure()


def should_preprocess(image):
    """
    Decide whether OCR preprocessing is needed based on page quality.

    Uses simple contrast heuristic:
    - Low contrast pages benefit from preprocessing
    - Clean high-contrast pages should skip preprocessing
    """

    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    contrast = gray.std()

    if contrast < 25:
        return True

    return False

def deskew_image(image):
    """
    Detect and correct small page rotation before OCR.
    """

    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.bitwise_not(gray)

    thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(np.where(thresh > 0))

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    rotated = cv2.warpAffine(
        img,
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated

def preprocess_image_for_ocr(image):
    """
    Preprocess page image before OCR.

    Pipeline:
    1. Convert to numpy
    2. Grayscale
    3. Noise removal
    4. Contrast enhancement (CLAHE)

    Returns processed image for OCR.
    """
    
    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )
    contrast = clahe.apply(denoised)

    return contrast


# -----------------------------
# OCR Worker (for parallel OCR)
# -----------------------------
def _ocr_page_worker(page_number, page, lang=None):
    
    # Step 1: deskew page first
    page = deskew_image(page)

    applied_preprocessing = should_preprocess(page)

    if applied_preprocessing:
        processed_page = preprocess_image_for_ocr(page)
    else:
        processed_page = page

    tess_lang = lang if lang else OCRConfig.OCR_LANGUAGES

    data = pytesseract.image_to_data(
        processed_page,
        lang=tess_lang,
        config="--psm 6",
        output_type=Output.DICT
    )

    confidences = []
    words = []

    for conf, word in zip(data["conf"], data["text"]):

        if conf != "-1" and word.strip():
            confidences.append(float(conf))
            words.append(word.strip())

    avg_conf = round(statistics.mean(confidences), 2) if confidences else 0

    pdf_bytes = pytesseract.image_to_pdf_or_hocr(
        processed_page,
        lang=tess_lang,
        extension="pdf",
        config="--psm 6"
    )

    reader = PdfReader(BytesIO(pdf_bytes))

    page_stat = {
        "page": page_number,
        "words_detected": len(words),
        "avg_confidence": avg_conf,
        "preprocessed": applied_preprocessing
    }

    return page_number, reader.pages[0], page_stat


def create_searchable_pdf(input_pdf_path, output_pdf_path=None, debug=True, lang=None):
    """
    Converts scanned PDF → searchable PDF using Tesseract OCR.

    Adds:
    - Page level OCR confidence statistics
    - Word detection metrics
    - Debug diagnostics for testing

    Returns:
        path_to_pdf, ocr_stats
    """

    input_pdf_path = Path(input_pdf_path)

    if output_pdf_path is None:
        output_pdf_path = input_pdf_path.with_name(
            input_pdf_path.stem + "_ocr.pdf"
        )

    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(input_pdf_path))
    pages = [page.render(scale=300/72.0).to_pil() for page in doc]

    writer = PdfWriter()

    page_stats = []
    results = []

    # Parallel OCR workers
    max_workers = min(4, os.cpu_count() or 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(_ocr_page_worker, i + 1, page, lang)
            for i, page in enumerate(pages)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    # Preserve correct page order
    results.sort(key=lambda x: x[0])

    for page_number, pdf_page, page_stat in results:

        writer.add_page(pdf_page)
        page_stats.append(page_stat)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)

    all_conf = [p["avg_confidence"] for p in page_stats if p["avg_confidence"] > 0]

    global_stats = {
        "pages": len(page_stats),
        "avg_confidence": round(statistics.mean(all_conf), 2) if all_conf else 0,
        "min_confidence": min(all_conf) if all_conf else 0,
        "max_confidence": max(all_conf) if all_conf else 0
    }

    if debug:

        print("\n" + "-" * 70)
        print(" OCR DIAGNOSTICS")
        print("-" * 70)

        for p in page_stats:
            print(
                f"Page {p['page']:>3} | "
                f"words={p['words_detected']:>5} | "
                f"confidence={p['avg_confidence']}% |"
                f"preprocessed={p['preprocessed']}"
            )

        print("\nOverall OCR Quality")
        print("-------------------")
        print("Pages:", global_stats["pages"])
        print("Average confidence:", global_stats["avg_confidence"], "%")
        print("Min confidence:", global_stats["min_confidence"], "%")
        print("Max confidence:", global_stats["max_confidence"], "%")

    return str(output_pdf_path), {
        "pages": page_stats,
        "summary": global_stats
    }


def map_primary_language_to_tess(lang_str: str) -> str:
    if not lang_str:
        return "eng"
    lang_str = lang_str.lower().strip()
    
    mapping = {
        "en": "eng", "english": "eng",
        "hi": "hin", "hindi": "hin",
        "mr": "mar", "marathi": "mar",
        "gu": "guj", "gujarati": "guj",
        "bn": "ben", "bengali": "ben",
        "ta": "tam", "tamil": "tam",
        "te": "tel", "telugu": "tel",
        "kn": "kan", "kannada": "kan",
        "ml": "mal", "malayalam": "mal",
        "or": "ori", "oriya": "ori", "od": "ori", "odia": "ori",
        "pa": "pan", "punjabi": "pan",
        "as": "asm", "assamese": "asm"
    }
    
    tess_lang = mapping.get(lang_str, "eng")
    if tess_lang != "eng":
        return f"eng+{tess_lang}"
    return "eng"





