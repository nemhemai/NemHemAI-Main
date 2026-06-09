import json
import logging
import requests
from typing import Dict, Any

from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
from app.graph.retriever import retrieve_graph_context
from app.memory.redis_memory import memory_store

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"

DRAFT_PROMPT = """
You are a highly professional, empathetic Government AI assistant.
Your job is to analyze a citizen's grievance and draft an official response.

--- CITIZEN GRIEVANCE ---
Category: {category}
Description: {description}

--- CITIZEN RECENT HISTORY (MEMORY) ---
{memory_context}

--- POLICY CONTEXT (VECTOR RAG) ---
{vector_context}

--- GRAPH CONTEXT (RELATIONSHIPS) ---
{graph_context}

--- INSTRUCTIONS ---
You must analyze the grievance and provide an official response.
1. Determine the "urgency": (LOW, MEDIUM, HIGH, CRITICAL)
2. Determine the "tone": (NEUTRAL, ANGRY, DISTRESSED, CONFUSED, POLITE)
3. Determine the "intent": (COMPLAINT, INQUIRY, SUGGESTION)
4. Determine the "severity_score": (Integer between 1 and 10, where 10 is the most severe)
5. Draft a professional response addressing the citizen based on the Policy Context and Graph Context.
   - If Tone is Angry/Distressed, be highly empathetic.
   - If Urgency is High/Critical, mention immediate escalation.
   - Acknowledge their issue specifically.
   - Keep the draft under 250 words.

You MUST return ONLY a valid JSON object in this exact format with no other text:
{{
  "urgency": "HIGH",
  "tone": "ANGRY",
  "intent": "COMPLAINT",
  "severity_score": 8,
  "draft_response": "We have received your grievance..."
}}
"""

def generate_draft_response(citizen_id: str, category: str, description: str) -> Dict[str, Any]:
    """
    Fast Single-Pass Pipeline combining Vector RAG, Graph RAG, OpenHuman analysis, and Drafting.
    """
    logger.info(f"Generating fast draft response for {citizen_id} - {category}")
    
    # 1. Fetch Redis Memory (Do not add current yet since we don't know urgency)
    recent_grievances = memory_store.get_recent_grievances(citizen_id)
    
    memory_context = "No recent history."
    if recent_grievances:
        memory_context = "\n".join([
            f"- {g['category']} (Urgency: {g.get('urgency', 'UNKNOWN')}): {g['description']}" 
            for g in recent_grievances
        ])
    
    # 2. Vector RAG (Hybrid)
    conn = get_db_conn()
    vector_context = "No direct policy found."
    results = []
    try:
        retriever = HybridRetriever()
        search_query = f"{category} {description}"
        results = retriever.retrieve(conn, search_query, top_k=3)
        if results:
            vector_context = "\n\n".join([r.get("text", "") for r in results])
    except Exception as e:
        logger.error(f"Vector retrieval failed: {e}")
    finally:
        release_db_conn(conn)
        
    # 3. Graph RAG
    graph_results = retrieve_graph_context([category])
    graph_context = graph_results if graph_results else "No graph relationships found."
        
    # 4. LLM Prompt Construction
    prompt = DRAFT_PROMPT.format(
        category=category,
        description=description,
        memory_context=memory_context,
        vector_context=vector_context,
        graph_context=graph_context
    )
    
    # 5. LLM Call
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "temperature": 0.2
    }
    
    draft_response = "We have received your grievance and are looking into it."
    openhuman = {"urgency": "MEDIUM", "tone": "NEUTRAL", "intent": "COMPLAINT", "severity_score": 5}
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        
        analysis = json.loads(result_text)
        draft_response = analysis.get("draft_response", draft_response)
        
        openhuman = {
            "urgency": analysis.get("urgency", "MEDIUM").upper(),
            "tone": analysis.get("tone", "NEUTRAL").upper(),
            "intent": analysis.get("intent", "COMPLAINT").upper(),
            "severity_score": int(analysis.get("severity_score", 5))
        }
        
    except Exception as e:
        logger.error(f"Single-pass LLM call failed: {e}")
        
    # 6. Save current grievance to memory now that we have urgency
    memory_store.add_grievance(citizen_id, category, description, openhuman["urgency"])
        
    return {
        "draft_response": draft_response,
        "openhuman": openhuman,
        "retrieved_context": results
    }
