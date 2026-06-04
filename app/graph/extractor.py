import json
import logging
from typing import List, Dict, Any
import requests
from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"  # Best for structured JSON extraction

EXTRACTION_PROMPT = """
You are a highly capable AI assistant that extracts knowledge graphs from government policy documents.
Your task is to extract Entities (Nodes) and Relationships (Edges) from the provided text.

Expected Entity Types:
- Policy (e.g., "Solid Waste Management Rule 2016")
- Department (e.g., "NMMC", "Health Department")
- Penalty (e.g., "Rs. 500 fine")
- GrievanceCategory (e.g., "Uncollected Garbage")

Expected Relationship Types:
- IMPLEMENTED_BY (Policy -> Department)
- IMPOSES (Policy -> Penalty)
- HANDLES (Department -> GrievanceCategory)
- HAS_PENALTY (GrievanceCategory -> Penalty)

Return a strictly valid JSON object in the following format:
{{
  "nodes": [
    {{"id": "node_id_string", "label": "EntityType", "properties": {{"name": "human readable name"}}}}
  ],
  "edges": [
    {{"source": "source_node_id", "target": "target_node_id", "type": "RELATIONSHIP_TYPE", "properties": {{}}}}
  ]
}}

Text to extract from:
---
{text}
---

Return ONLY the JSON. Do not include markdown formatting like ```json.
"""

def extract_graph_from_text(text: str) -> Dict[str, Any]:
    """Uses Ollama to extract nodes and edges from a text chunk."""
    prompt = EXTRACTION_PROMPT.format(text=text)
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "temperature": 0.1
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        
        graph_data = json.loads(result_text)
        return graph_data
    except Exception as e:
        logger.error(f"Failed to extract graph from text using {MODEL_NAME}: {e}")
        return {"nodes": [], "edges": []}

def ingest_graph_data(graph_data: Dict[str, Any]):
    """Ingests extracted graph data into Neo4j."""
    driver = neo4j_client.get_driver()
    if not driver:
        logger.warning("Neo4j driver not available. Skipping graph ingestion.")
        return
        
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    with driver.session() as session:
        # Create Nodes
        for node in nodes:
            label = node.get("label", "Entity").replace(" ", "")
            node_id = node.get("id")
            name = node.get("properties", {}).get("name", node_id)
            
            if not node_id: continue
            
            # Using MERGE to avoid duplicates
            query = f"MERGE (n:{label} {{id: $id}}) SET n.name = $name"
            session.run(query, id=node_id, name=name)
            
        # Create Edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type", "RELATED_TO").upper().replace(" ", "_")
            
            if not source or not target: continue
            
            query = f"""
            MATCH (s {{id: $source}})
            MATCH (t {{id: $target}})
            MERGE (s)-[r:{rel_type}]->(t)
            """
            session.run(query, source=source, target=target)
            
    logger.info(f"Ingested {len(nodes)} nodes and {len(edges)} edges into Neo4j.")
