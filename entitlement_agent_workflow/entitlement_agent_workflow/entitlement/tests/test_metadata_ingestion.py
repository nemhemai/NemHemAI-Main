import os
import sys
import yaml
from pathlib import Path
import pytest
from qdrant_client import QdrantClient

from app.embedding.embedding_engine import EmbeddingEngine

def test_yaml_records_exist_and_are_valid():
    records_dir = Path(__file__).resolve().parents[1] / "app" / "core" / "metadata" / "records"
    assert records_dir.exists(), f"Records directory {records_dir} does not exist"
    
    yaml_files = list(records_dir.glob("*.yaml"))
    assert len(yaml_files) == 20, f"Expected 20 YAML records, found {len(yaml_files)}"
    
    from app.core.metadata.schemas.validator import validate_scheme
    
    for yaml_file in yaml_files:
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        try:
            validate_scheme(data)
        except Exception as e:
            pytest.fail(f"Schema validation failed for {yaml_file.name}: {e}")

def test_qdrant_collection_exists():
    """Verify that the 'schemes' collection exists in Qdrant and contains records."""
    client = QdrantClient(url="http://localhost:6333")
    assert client.collection_exists(collection_name="schemes"), "Qdrant collection 'schemes' does not exist"
    
    info = client.get_collection(collection_name="schemes")
    assert info.points_count > 0, "Qdrant collection 'schemes' is empty"

def test_semantic_search_retrieval():
    """Verify that we can encode a query and get relevant schemes from Qdrant."""
    engine = EmbeddingEngine()
    
    query = "schemes for street vendors needing loans"
    dense_vec, _ = engine.embed_query(query)
    
    client = QdrantClient(url="http://localhost:6333")
    response = client.query_points(
        collection_name="schemes",
        query=dense_vec.tolist(),
        limit=3
    )
    
    assert len(response.points) > 0, "No results returned from Qdrant search"
    
    # Verify top match is indeed a street vendor scheme
    top_hit = response.points[0]
    payload = top_hit.payload
    
    # Check if scheme_id or name matches svanidhi or street vendor
    identifier = (payload.get("scheme_name", "") + " " + payload.get("scheme_id", "")).lower()
    assert "vendor" in identifier or "svanidhi" in identifier, f"Expected street vendor scheme, got {identifier}"
