import os

file_path = 'app/utils/ocr_utils.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

old_worker = '''def _ocr_page_worker(page_number, page):'''
new_worker = '''def _ocr_page_worker(input_pdf_path, page_number):
    import fitz
    from PIL import Image

    doc = fitz.open(input_pdf_path)
    page = doc[page_number - 1]
    pix = page.get_pixmap(dpi=300)
    page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    
    page = page_img'''

old_loader = '''    doc = fitz.open(input_pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    writer = PdfWriter()

    page_stats = []
    results = []

    # Parallel OCR workers
    max_workers = min(4, os.cpu_count() or 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(_ocr_page_worker, i + 1, page)
            for i, page in enumerate(pages)
        ]'''

new_loader = '''    doc = fitz.open(input_pdf_path)
    total_pages = len(doc)
    doc.close()

    writer = PdfWriter()

    page_stats = []
    results = []

    # Parallel OCR workers
    max_workers = min(4, os.cpu_count() or 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(_ocr_page_worker, str(input_pdf_path), i + 1)
            for i in range(total_pages)
        ]'''

if old_worker in code and old_loader in code:
    code = code.replace(old_worker, new_worker).replace(old_loader, new_loader)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print('SUCCESS')
else:
    print('COULD NOT FIND CONTENT TO REPLACE')
