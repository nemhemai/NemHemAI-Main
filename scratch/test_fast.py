import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ingestion.pdf_extractor import PDFExtractor
import fitz

def test():
    pdf_path = r"d:\NH_RAG\data\chattisgarh docs\startup promotion policy.pdf"
    extractor = PDFExtractor()
    page_files = extractor.split_pdf_pages(pdf_path)
    
    page_meta = extractor.classify_pages_fast(page_files)
    print("Page Meta:")
    for m in page_meta:
        print(m)
        
    for page_file in page_files[:3]:
        page_index = extractor.get_page_index(page_file)
        page_type = next((p["type"] for p in page_meta if p["file"] == page_file), "heavy")
        print(f"--- PAGE {page_index} ({page_type}) ---")
        
        if page_type in ["light", "medium"]:
            res = extractor._extract_page_with_fitz(page_file, page_index + 1)
        else:
            res = extractor._process_single_page_with_stats(page_file)
            
        if res:
            elements = res[0]
            print(f"Extracted {len(elements)} elements")
            if elements:
                print(elements[0])
        else:
            print("No result")

if __name__ == "__main__":
    test()
