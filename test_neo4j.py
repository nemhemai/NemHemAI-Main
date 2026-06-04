import sys
import json
import logging
from app.graph.neo4j_client import neo4j_client
from app.graph.extractor import extract_graph_from_text, ingest_graph_data
from app.graph.retriever import retrieve_graph_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    print("1. Connecting to Neo4j and setting up schema...")
    neo4j_client.setup_schema()
    
    text = "The Solid Waste Management Rule 2016 is implemented by the NMMC. Under this rule, failing to segregate waste imposes a Rs. 500 fine."
    print("\n2. Extracting graph from sample text:")
    print(f"Text: '{text}'")
    
    graph_data = extract_graph_from_text(text)
    print("\nExtracted Graph JSON:")
    print(json.dumps(graph_data, indent=2))
    
    print("\n3. Ingesting graph into Neo4j...")
    ingest_graph_data(graph_data)
    
    print("\n4. Retrieving context for 'NMMC' and 'fine'...")
    context = retrieve_graph_context(["NMMC", "fine"])
    print(context)
    
    print("\nTest complete!")
    neo4j_client.close()

if __name__ == "__main__":
    run_test()
