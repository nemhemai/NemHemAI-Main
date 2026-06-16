import logging
from typing import List, Dict, Any
from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

def retrieve_graph_context(keywords: List[str]) -> str:
    """
    Retrieves surrounding graph context (1-2 degrees of separation) for specific keywords.
    For example, if keywords=["NMMC", "Solid Waste"], this will pull relationships
    about NMMC and Solid Waste to feed to the LLM.
    """
    driver = neo4j_client.get_driver()
    if not driver:
        logger.warning("Neo4j driver not available. Returning empty graph context.")
        return ""
        
    if not keywords:
        return ""
        
    # We want to match any node whose name contains our keyword (case insensitive)
    # and return its immediate relationships.
    query = """
    UNWIND $keywords AS keyword
    MATCH (n)-[r]-(m)
    WHERE n.name IS NOT NULL AND m.name IS NOT NULL AND toLower(n.name) CONTAINS toLower(keyword)
    RETURN n.name AS Source, type(r) AS Relationship, m.name AS Target, labels(n)[0] AS SourceType, labels(m)[0] AS TargetType
    LIMIT 20
    """
    
    context_statements = []
    
    try:
        with driver.session() as session:
            result = session.run(query, keywords=keywords)
            records = list(result)
            
            for record in records:
                source = record["Source"]
                rel = record["Relationship"]
                target = record["Target"]
                stmt = f"- {source} {rel} {target}."
                if stmt not in context_statements:
                    context_statements.append(stmt)
                    
        if context_statements:
            final_context = "Knowledge Graph Context:\n" + "\n".join(context_statements)
            return final_context
        return ""
        
    except Exception as e:
        logger.error(f"Failed to retrieve graph context: {e}")
        return ""
