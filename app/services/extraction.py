# app/services/extraction.py

import json
import re
from typing import Dict

from app.llm.ollama_client import call_llm


EXTRACTION_PROMPT = """
You are a legal document parser.

Convert the following legal Act text into structured JSON.

STRICT RULES:
- Output ONLY valid JSON.
- No explanations.
- No markdown.
- No text before or after JSON.

Required JSON format:

{
  "act_id": "",
  "act_title": "",
  "sections": [
    {
      "section_number": "",
      "heading": "",
      "content": "",
      "clauses": []
    }
  ]
}

Now convert the following text:
"""


def clean_llm_json(response: str) -> str:
    """
    Extract JSON block if model adds extra text.
    """
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        return match.group(0)
    return response


def extract_structure(pdf_text: str) -> Dict:

    prompt = EXTRACTION_PROMPT + "\n\n" + pdf_text

    raw_response = call_llm(prompt)

    cleaned_response = clean_llm_json(raw_response)

    try:
        structured_data = json.loads(cleaned_response)
    except json.JSONDecodeError:
        raise ValueError("❌ LLM did not return valid JSON")

    # Basic schema validation
    if "sections" not in structured_data:
        raise ValueError("❌ Invalid structure: 'sections' missing")

    return structured_data