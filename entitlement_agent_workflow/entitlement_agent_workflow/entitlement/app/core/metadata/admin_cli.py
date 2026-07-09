import os
import sys
import yaml
import json
import uuid
import argparse
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.embedding.embedding_engine import EmbeddingEngine
from app.core.metadata.schemas.validator import validate_scheme

RECORDS_DIR = Path(__file__).resolve().parent / "records"


def build_scheme_embedding_text(scheme: dict) -> str:
    rules_text = []
    for r in scheme.get("eligibility_rules", []):
        exclusion_suffix = " (Exclusion)" if r.get("is_exclusion") else ""
        rules_text.append(f"- {r['field']} must be {r['operator']} {r['value']}{exclusion_suffix}")
    benefit = scheme.get("benefit", {})
    benefit_text = f"{benefit.get('type')} of {benefit.get('amount')} {benefit.get('currency', 'INR')}"
    
    return f"""Scheme: {scheme.get('scheme_name')} (ID: {scheme.get('scheme_id')})
Category: {scheme.get('category')}
Benefit description: {benefit_text}
Eligibility Rules:
{chr(10).join(rules_text) if rules_text else '- No specific rules'}
Required Documents: {', '.join(scheme.get('required_documents', []))}"""


def list_records():
    print(f"Listing scheme records from: {RECORDS_DIR}\n")
    if not RECORDS_DIR.exists():
        print("Records directory does not exist.")
        return
        
    yaml_files = list(RECORDS_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No scheme records found.")
        return
        
    print(f"{'Scheme ID':<25} | {'Scheme Name':<50} | {'Category':<20}")
    print("-" * 100)
    for yf in yaml_files:
        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                print(f"{data.get('scheme_id', 'unknown'):<25} | {data.get('scheme_name', 'unknown'):<50} | {data.get('category', 'unknown'):<20}")
        except Exception as e:
            print(f"Error reading {yf.name}: {e}")


def validate_file(file_path: Path):
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return None
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error parsing YAML: {e}")
        return None
        
    try:
        # Enforce active by default if not set
        if "active" not in data:
            data["active"] = True
        validate_scheme(data)
        print("✓ Success: Scheme metadata is valid!")
        return data
    except Exception as e:
        print(f"✗ Validation Error: {e}")
        return None


def reindex_in_qdrant(scheme: dict):
    print("Connecting to Qdrant...")
    client = QdrantClient(url="http://localhost:6333")
    engine = EmbeddingEngine()
    
    scheme_id = scheme["scheme_id"]
    search_text = build_scheme_embedding_text(scheme)
    
    print("Generating embedding...")
    dense_vec, _ = engine.embed_query(search_text)
    
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, scheme_id))
    point = PointStruct(
        id=point_id,
        vector=dense_vec.tolist(),
        payload=scheme
    )
    
    print(f"Upserting scheme '{scheme['scheme_name']}' into Qdrant collection 'schemes'...")
    client.upsert(
        collection_name="schemes",
        points=[point]
    )
    print("✓ Success: Reindexed in Qdrant!")


def add_record(file_path_str: str):
    file_path = Path(file_path_str)
    print(f"Adding new scheme from: {file_path}")
    scheme = validate_file(file_path)
    if not scheme:
        print("Aborting: Invalid scheme record.")
        return
        
    dest_path = RECORDS_DIR / f"{file_path.stem}.yaml"
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            yaml.dump(scheme, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"Saved copy to {dest_path.name}")
        
        # Index in Qdrant
        reindex_in_qdrant(scheme)
    except Exception as e:
        print(f"Failed to add scheme: {e}")


def update_record(scheme_id: str, field: str, value: str):
    print(f"Updating scheme '{scheme_id}' field '{field}' to '{value}'...")
    
    # Find YAML file for this scheme
    target_file = None
    if RECORDS_DIR.exists():
        for yf in RECORDS_DIR.glob("*.yaml"):
            try:
                with open(yf, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data.get("scheme_id") == scheme_id:
                        target_file = yf
                        break
            except:
                pass
                
    if not target_file:
        print(f"Error: Scheme '{scheme_id}' not found in records.")
        return
        
    with open(target_file, "r", encoding="utf-8") as f:
        scheme = yaml.safe_load(f)
        
    # Cast value depending on field type or try parsing JSON/scalar
    try:
        parsed_val = json.loads(value)
    except:
        parsed_val = value # fallback to string
        
    scheme[field] = parsed_val
    
    # Validate updated
    try:
        validate_scheme(scheme)
    except Exception as ve:
        print(f"✗ Update failed validation check: {ve}")
        return
        
    # Save YAML
    with open(target_file, "w", encoding="utf-8") as f:
        yaml.dump(scheme, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
    print(f"Saved updated file {target_file.name}")
    
    # Reindex in Qdrant
    reindex_in_qdrant(scheme)


def main():
    parser = argparse.ArgumentParser(description="Metadata Administration CLI Utility")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # list
    subparsers.add_parser("list", help="List all scheme metadata records")
    
    # validate
    val_parser = subparsers.add_parser("validate", help="Validate a YAML file against schema")
    val_parser.add_argument("file", type=str, help="Path to YAML file")
    
    # add
    add_parser = subparsers.add_parser("add", help="Add a validated YAML scheme to records and Qdrant")
    add_parser.add_argument("file", type=str, help="Path to YAML file")
    
    # update
    up_parser = subparsers.add_parser("update", help="Update a specific field in a scheme and reindex")
    up_parser.add_argument("scheme_id", type=str, help="Scheme unique ID")
    up_parser.add_argument("field", type=str, help="Field name to update")
    up_parser.add_argument("value", type=str, help="New field value (JSON format or raw string)")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_records()
    elif args.command == "validate":
        validate_file(Path(args.file))
    elif args.command == "add":
        add_record(args.file)
    elif args.command == "update":
        update_record(args.scheme_id, args.field, args.value)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
