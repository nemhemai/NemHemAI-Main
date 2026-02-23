from app.services.extraction import extract_structure

sample_text = """
Section 1 Preliminary
This Act may be called the Example Act.

Section 2 Definitions
In this Act, unless the context otherwise requires...
"""

result = extract_structure(sample_text)

print("✅ STRUCTURED OUTPUT:")
print(result)