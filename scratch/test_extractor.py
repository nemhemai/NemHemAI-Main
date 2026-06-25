import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ingestion.pdf_extractor import PDFExtractor

def test():
    pdf_path = r"d:\NH_RAG\data\chattisgarh docs\startup promotion policy.pdf"
    print(f"Testing extraction on {pdf_path}")
    extractor = PDFExtractor()
    elements, stats = extractor.extract_elements(pdf_path)
    
    print(f"Extraction stats: {stats}")
    print(f"Total elements returned: {len(elements)}")
    
    if len(elements) > 0:
        print("First element preview:")
        print(elements[0])

if __name__ == "__main__":
    test()
