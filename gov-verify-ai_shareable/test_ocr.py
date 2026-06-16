import os
os.environ["FLAGS_use_pir_api"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from paddleocr import PaddleOCR
import json

ocr_engine = PaddleOCR(
    use_angle_cls=False,
    lang="en",
    enable_mkldnn=False,
)

image_path = "government_test_assets/aadhaar/images/aadhaar_0000.png"
print(f"Running OCR on: {image_path}")
results = ocr_engine.ocr(image_path)

print("\nRAW OCR RESULTS:")
print(type(results))
try:
    print(results)
except Exception as e:
    print("Could not print raw results:", e)
