import os
import json
import yaml
import sys
from typing import Any, Dict
import jsonschema
from jsonschema import validate, ValidationError

# Get paths to the schemas
SCHEMA_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEME_SCHEMA_PATH = os.path.join(SCHEMA_DIR, "scheme_schema.json")
CITIZEN_SCHEMA_PATH = os.path.join(SCHEMA_DIR, "citizen_schema.json")

# Load schemas
try:
    with open(SCHEME_SCHEMA_PATH, "r", encoding="utf-8") as f:
        SCHEME_SCHEMA = json.load(f)
except Exception as e:
    SCHEME_SCHEMA = {}

try:
    with open(CITIZEN_SCHEMA_PATH, "r", encoding="utf-8") as f:
        CITIZEN_SCHEMA = json.load(f)
except Exception as e:
    CITIZEN_SCHEMA = {}


def validate_scheme(data: Dict[str, Any]) -> None:
    """Validates a scheme metadata record (dictionary) against the scheme JSON schema.
    Raises ValidationError if invalid.
    """
    if not SCHEME_SCHEMA:
        raise RuntimeError("Scheme schema could not be loaded.")
    validate(instance=data, schema=SCHEME_SCHEMA)


def validate_citizen(data: Dict[str, Any]) -> None:
    """Validates a citizen profile (dictionary) against the citizen JSON schema.
    Raises ValidationError if invalid.
    """
    if not CITIZEN_SCHEMA:
        raise RuntimeError("Citizen profile schema could not be loaded.")
    validate(instance=data, schema=CITIZEN_SCHEMA)


def validate_file(file_path: str) -> bool:
    """Loads a YAML or JSON file and validates it based on file naming or content."""
    if not os.path.exists(file_path):
        print(f"Error: File does not exist at {file_path}")
        return False

    # Try loading as YAML/JSON
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Handle empty files
            if not content.strip():
                print(f"Error: File {file_path} is empty.")
                return False
            data = yaml.safe_load(content)
    except Exception as e:
        print(f"Error: Failed to parse file {file_path} as YAML/JSON. Reason: {e}")
        return False

    if not isinstance(data, dict):
        print(f"Error: File content is not a dictionary/object structure.")
        return False

    # Determine schema based on content
    is_citizen = "citizen_id" in data or "personal_info" in data or "socio_economic_info" in data
    schema_name = "Citizen Profile" if is_citizen else "Scheme Metadata"
    validate_func = validate_citizen if is_citizen else validate_scheme

    try:
        validate_func(data)
        print(f"✓ Success: {file_path} is a valid {schema_name}.")
        return True
    except ValidationError as ve:
        print(f"✗ Validation Error in {file_path} (Type: {schema_name}):")
        print(f"  Path: {list(ve.path)}")
        print(f"  Message: {ve.message}")
        return False
    except Exception as e:
        print(f"✗ Error: Unexpected failure during validation: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validator.py <path_to_yaml_or_json>")
        sys.exit(1)

    success = validate_file(sys.argv[1])
    sys.exit(0 if success else 1)
