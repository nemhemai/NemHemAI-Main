import os
import sys
import yaml
import uuid
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.embedding.embedding_engine import EmbeddingEngine


def build_scheme_embedding_text(scheme: dict) -> str:
    """Builds a rich textual description of the scheme metadata and rules for vector search index."""
    rules_text = []
    for r in scheme.get("eligibility_rules", []):
        exclusion_suffix = " (Exclusion/Disqualifier)" if r.get("is_exclusion") else ""
        rules_text.append(f"- {r['field']} must be {r['operator']} {r['value']}{exclusion_suffix}")
        
    benefit = scheme.get("benefit", {})
    benefit_text = f"{benefit.get('type', 'welfare')} of {benefit.get('amount', 0)} {benefit.get('currency', 'INR')}"
    
    return f"""Scheme: {scheme.get('scheme_name')} (ID: {scheme.get('scheme_id')})
Issuing Authority: {scheme.get('issuing_authority')} ({scheme.get('department_code')})
Jurisdiction: {scheme.get('jurisdiction')} {scheme.get('state_origin') or ''}
Category: {scheme.get('category')}
Benefit description: {benefit_text}
Eligibility Rules:
{chr(10).join(rules_text) if rules_text else '- No specific rules'}
Required Documents: {', '.join(scheme.get('required_documents', []))}
Tags: {', '.join(scheme.get('tags', []))}"""


def main():
    records_dir = Path(__file__).resolve().parent / "records"
    if not records_dir.exists():
        print(f"Records directory not found: {records_dir}")
        sys.exit(1)
        
    yaml_files = list(records_dir.glob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML records to index.")
    
    if not yaml_files:
        print("No YAML files found. Run extract_rules.py first.")
        sys.exit(1)

    print("Initializing Qdrant Client...")
    client = QdrantClient(url="http://localhost:6333")
    
    collection_name = "schemes"
    
    # Recreate collection
    print(f"Creating Qdrant collection: {collection_name}")
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )
    
    print("Loading embedding model...")
    engine = EmbeddingEngine()
    
    points = []
    for yaml_file in yaml_files:
        print(f"\nProcessing record: {yaml_file.name}")
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                scheme = yaml.safe_load(f)
        except Exception as e:
            print(f"Failed to parse YAML: {e}")
            continue
            
        scheme_id = scheme.get("scheme_id", yaml_file.stem)
        
        # Build vector search text representation
        search_text = build_scheme_embedding_text(scheme)
        print(f"Encoding search text (Length: {len(search_text)} characters)...")
        
        # Generate BGE-M3 embedding vector
        dense_vec, _ = engine.embed_query(search_text)
        
        # Create unique UUID based on scheme_id
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, scheme_id))
        
        # Create Point
        point = PointStruct(
            id=point_id,
            vector=dense_vec.tolist(),
            payload=scheme
        )
        points.append(point)
        print(f"Added point for scheme: {scheme.get('scheme_name')} (ID: {point_id})")

    if points:
        print(f"\nUpserting {len(points)} points into Qdrant collection '{collection_name}'...")
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        print("Upsert completed successfully!")
    else:
        print("No points to upsert.")


if __name__ == "__main__":
    main()
