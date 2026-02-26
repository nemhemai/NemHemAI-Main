# app/services/extraction.py

import json
import re
from typing import Dict
from app.llm.ollama_client import call_llm
from app.utils.id_generator import generate_act_id, generate_section_id


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


def extract_json_from_response(response: str) -> str:
    """
    Robust JSON extraction from LLM output.
    """

    # Remove markdown code fences
    response = re.sub(r"```json|```", "", response)

    # Find first '{'
    start = response.find("{")
    if start == -1:
        raise ValueError("❌ No JSON object found in LLM output.")

    # Find last '}'
    end = response.rfind("}")
    if end == -1:
        raise ValueError("❌ JSON appears incomplete.")

    json_string = response[start:end + 1]

    return json_string.strip()


def extract_structure(pdf_text: str) -> Dict:

    prompt = EXTRACTION_PROMPT + "\n\n" + pdf_text

    raw_response = call_llm(prompt)

    # DEBUG (temporarily enable if needed)
    # print("RAW LLM OUTPUT:\n", raw_response)

    cleaned_json = extract_json_from_response(raw_response)

    try:
        structured_data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        print("❌ JSON PARSE ERROR:", str(e))
        print("CLEANED JSON:\n", cleaned_json)
        raise ValueError("❌ LLM did not return valid JSON")

    # Validate root fields
    if "act_title" not in structured_data:
        raise ValueError("❌ Invalid structure: 'act_title' missing")

    if "sections" not in structured_data:
        raise ValueError("❌ Invalid structure: 'sections' missing")

    # ---- ACT ID GENERATION ----
    # If LLM did not provide act_id OR provided bad one, regenerate
    act_title = structured_data["act_title"]

    if not structured_data.get("act_id"):
        structured_data["act_id"] = generate_act_id(act_title)

    act_id = structured_data["act_id"]

    # ---- SECTION ID GENERATION ----
    for section in structured_data["sections"]:

        if "section_number" not in section:
            raise ValueError("❌ section_number missing in section")

        section_label = section["section_number"]

        section_id = generate_section_id(
            act_id=act_id,
            section_label=section_label,
            version=1
        )

        section["section_id"] = section_id
    return structured_data