# app/utils/pdf_utils.py

import fitz


def is_scanned_pdf(pdf_path, sample_pages=3):
    """
    Detect whether a PDF is scanned or digital.

    A scanned PDF usually has no text layer.
    We check the first few pages for extractable text.
    """

    try:
        doc = fitz.open(pdf_path)

        for i in range(min(sample_pages, len(doc))):

            page = doc[i]
            text = page.get_text().strip()

            if len(text) > 50:
                print("Its a digital PDF.")
                return False   # digital PDF

        print("Its a scanned PDF.")
        return True   # scanned PDF

    except Exception:
        return True