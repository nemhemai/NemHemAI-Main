import json
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"

OPENHUMAN_PROMPT = """
You are OpenHuman, an empathetic AI that analyzes citizen grievances.
Your task is to analyze the following grievance and detect four things:
1. "urgency": (LOW, MEDIUM, HIGH, CRITICAL)
2. "tone": (NEUTRAL, ANGRY, DISTRESSED, CONFUSED, POLITE)
3. "intent": (COMPLAINT, INQUIRY, SUGGESTION)
4. "severity_score": (Integer between 1 and 10, where 10 is the most severe)

Return ONLY a valid JSON object in this exact format, with no other text or markdown:
{{
  "urgency": "HIGH",
  "tone": "ANGRY",
  "intent": "COMPLAINT",
  "severity_score": 8
}}

Grievance:
---
{text}
---
"""

def detect_grievance_tone(text: str) -> Dict[str, str]:
    """Analyzes a grievance to detect urgency, tone, and intent."""
    prompt = OPENHUMAN_PROMPT.format(text=text)
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "temperature": 0.1
    }
    
    default_result = {"urgency": "MEDIUM", "tone": "NEUTRAL", "intent": "COMPLAINT", "severity_score": 5}
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        
        analysis = json.loads(result_text)
        # Fallback to default keys if missing
        return {
            "urgency": analysis.get("urgency", "MEDIUM").upper(),
            "tone": analysis.get("tone", "NEUTRAL").upper(),
            "intent": analysis.get("intent", "COMPLAINT").upper(),
            "severity_score": int(analysis.get("severity_score", 5))
        }
    except Exception as e:
        logger.error(f"OpenHuman analysis failed: {e}")
        return default_result
