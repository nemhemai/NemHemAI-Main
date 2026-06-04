import json
import logging
import requests
from typing import Dict, Any

from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
from app.graph.retriever import retrieve_graph_context
from app.memory.redis_memory import memory_store
from app.generation.openhuman import detect_grievance_tone

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"

DRAFT_PROMPT = """
You are a highly professional, empathetic Government AI assistant.
Your job is to draft an official response to a citizen's grievance.

You must base your response on the provided Context (Policy rules and Graph relationships).
If the citizen's Tone is Angry or Distressed, be highly empathetic and reassuring.
If the Urgency is High or Critical, mention that this is being escalated immediately.

--- CITIZEN GRIEVANCE ---
Category: {category}
Description: {description}

--- OPENHUMAN ANALYSIS ---
Urgency: {urgency}
Tone: {tone}
Intent: {intent}

--- CITIZEN RECENT HISTORY (MEMORY) ---
{memory_context}

--- POLICY CONTEXT (VECTOR RAG) ---
{vector_context}

--- GRAPH CONTEXT (RELATIONSHIPS) ---
{graph_context}

--- INSTRUCTIONS ---
Write a professional, official response addressing the citizen.
1. Acknowledge their issue specifically.
2. If applicable, mention relevant policy or penalties based on the context provided.
3. State the immediate next steps being taken.
4. Keep it under 250 words.
5. Output ONLY the draft response text. Do not include markdown or internal thoughts.
"""

def generate_draft_response(citizen_id: str, category: str, description: str) -> Dict[str, Any]:
    """
    Core generation pipeline combining Vector RAG, Graph RAG, and Memory.
    """
    logger.info(f"Generating draft response for {citizen_id} - {category}")
    
    # 1. OpenHuman Tone Detection
    openhuman = detect_grievance_tone(description)
    
    # 2. Redis Memory (Track this new one, fetch past ones)
    memory_store.add_grievance(citizen_id, category, description, openhuman["urgency"])
    recent_grievances = memory_store.get_recent_grievances(citizen_id)
    
    memory_context = "No recent history."
    if len(recent_grievances) > 1:
        memory_context = "\n".join([
            f"- {g['category']} (Urgency: {g['urgency']}): {g['description']}" 
            for g in recent_grievances[1:] # Exclude the current one just added
        ])
    
    # 3. Vector RAG (Hybrid)
    conn = get_db_conn()
    vector_context = "No direct policy found."
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
        
    # 4. Graph RAG
    graph_results = retrieve_graph_context(search_query)
    graph_context = "No graph relationships found."
    if graph_results:
        graph_context = "\n".join([f"{edge['source']} -> {edge['type']} -> {edge['target']}" for edge in graph_results])
        
    # 5. LLM Prompt Construction
    prompt = DRAFT_PROMPT.format(
        category=category,
        description=description,
        urgency=openhuman["urgency"],
        tone=openhuman["tone"],
        intent=openhuman["intent"],
        memory_context=memory_context,
        vector_context=vector_context,
        graph_context=graph_context
    )
    
    # 6. LLM Call
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.3
    }
    
    draft_response = "We have received your grievance and are looking into it."
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        draft_response = response.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Draft generation LLM call failed: {e}")
        
    return {
        "draft_response": draft_response,
        "openhuman": openhuman
    }
