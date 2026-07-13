from app.agents.verification.services.classification_service import ClassificationService
from app.agents.verification.services.field_extraction_service import FieldExtractionService
from app.agents.verification.services.verification_service import VerificationService

text = """
AFFIDAVIT / DECLARATION
I, Rajesh Kumar, son of Suresh Kumar, resident of Maharashtra, 
do hereby solemnly affirm and state as follows:
1. I do not own any pucca house anywhere in India.
2. I am applying for PMAY-U.
"""

print("1. CLASSIFICATION")
doc_type = ClassificationService.classify(text)
print(f"Document Type: {doc_type}")

print("\n2. EXTRACTION")
fields = FieldExtractionService.extract_fields(doc_type, text)
print(f"Fields: {fields['extracted_fields']}")

print("\n3. VERIFICATION")
res = VerificationService.verify(doc_type, fields['extracted_fields'])
print(f"Passed Checks: {res['passed_checks']}")
print(f"Failed Checks: {res['failed_checks']}")
print(f"Confidence: {res['confidence']}")
print(f"Verified: {res['verified']}")
