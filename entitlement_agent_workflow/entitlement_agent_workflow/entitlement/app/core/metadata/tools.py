import os
import sys
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient

from app.embedding.embedding_engine import EmbeddingEngine

# Imports from entitlement app (resolves correctly to entitlement\app)
from app.core.metadata.schemas.validator import validate_citizen
from app.core.metadata.evaluator.evaluator import evaluate_scheme_eligibility
from app.core.metadata.graph_queries import get_driver, get_scheme_rules, find_schemes_by_documents


def normalize_document_name(doc_name: str) -> str:
    """Normalize document name to title case and strip extra spaces."""
    return doc_name.strip().title()


def get_db_connection():
    """Returns a connection to the PostgreSQL database using settings or environment variables."""
    import psycopg2
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5433")
    db_name = os.getenv("DB_NAME", "nemhem_db")
    
    return psycopg2.connect(
        user=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        database=db_name
    )


def load_citizen_profile_from_db(citizen_id_or_aadhaar: str) -> dict:
    """
    Queries PostgreSQL database for the citizen identity, profile, and documents,
    merges them into a flat Citizen 360 Profile structure.
    Supports either citizen_id (UUID string) or aadhaar_id string.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Determine if input is UUID or Aadhaar ID
        is_uuid = False
        try:
            uuid.UUID(citizen_id_or_aadhaar)
            is_uuid = True
        except ValueError:
            pass
            
        if is_uuid:
            query_citizen = """
            SELECT citizen_id, aadhaar_id, is_verified 
            FROM citizens 
            WHERE citizen_id = %s
            """
        else:
            query_citizen = """
            SELECT citizen_id, aadhaar_id, is_verified 
            FROM citizens 
            WHERE aadhaar_id = %s
            """
            
        cur.execute(query_citizen, (citizen_id_or_aadhaar,))
        citizen_row = cur.fetchone()
        
        if not citizen_row:
            raise ValueError(f"Citizen with ID/Aadhaar '{citizen_id_or_aadhaar}' not found in database registry.")
            
        citizen_id, aadhaar_id, is_verified = citizen_row
        
        # Query profile
        query_profile = """
        SELECT personal_info, household_info, socio_economic_info, existing_benefits
        FROM citizen_profiles
        WHERE citizen_id = %s
        """
        cur.execute(query_profile, (citizen_id,))
        profile_row = cur.fetchone()
        
        personal_info = {}
        household_info = {}
        socio_economic_info = {}
        existing_benefits = []
        
        if profile_row:
            personal_info = profile_row[0] or {}
            household_info = profile_row[1] or {}
            socio_economic_info = profile_row[2] or {}
            existing_benefits = profile_row[3] or []
            
        # Query verified documents from database
        query_docs = """
        SELECT document_type 
        FROM citizen_documents 
        WHERE citizen_id = %s AND verification_status = 'VERIFIED'
        """
        cur.execute(query_docs, (citizen_id,))
        doc_rows = cur.fetchall()
        verified_docs = [normalize_document_name(row[0]) for row in doc_rows]
        
        # Always include Aadhaar if citizen is_verified is True
        if is_verified and "Aadhaar" not in verified_docs:
            verified_docs.append("Aadhaar")
            
        # Compile a flat profile structure matching citizen_schema.json
        profile_data = {
            "citizen_id": str(citizen_id),
            "age": personal_info.get("age"),
            "gender": personal_info.get("gender"),
            "state": personal_info.get("state"),
            "district": personal_info.get("district"),
            "urban_rural": personal_info.get("urban_rural"),
            "income_annual": socio_economic_info.get("income_annual"),
            "category": socio_economic_info.get("category"),
            "occupation": socio_economic_info.get("occupation"),
            "education_level": socio_economic_info.get("education_level"),
            "has_aadhaar": personal_info.get("has_aadhaar") or (True if is_verified else False),
            "has_bank_account": personal_info.get("has_bank_account") or socio_economic_info.get("has_bank_account"),
            "has_vending_certificate": socio_economic_info.get("has_vending_certificate"),
            "has_ulb_recommendation": socio_economic_info.get("has_ulb_recommendation"),
            "has_pucca_house": socio_economic_info.get("has_pucca_house"),
            "is_govt_employee": socio_economic_info.get("is_govt_employee"),
            "pays_income_tax": socio_economic_info.get("pays_income_tax"),
            "owns_motorized_vehicle": socio_economic_info.get("owns_motorized_vehicle"),
            "is_institutional_landholder": socio_economic_info.get("is_institutional_landholder"),
            "land_ownership_acres": socio_economic_info.get("land_ownership_acres"),
            "existing_benefits": existing_benefits,
            "verified_documents": verified_docs
        }
        
        # Copy custom/extra properties from personal, socio_economic, and household info
        for k, v in personal_info.items():
            if k not in profile_data:
                profile_data[k] = v
        for k, v in socio_economic_info.items():
            if k not in profile_data:
                profile_data[k] = v
        for k, v in household_info.items():
            if k not in profile_data:
                profile_data[k] = v
                
        return profile_data
        
    finally:
        cur.close()
        conn.close()


def build_profile_tool(citizen_data: Any) -> dict:
    """
    Intakes citizen data (either as a dictionary of raw attributes, or a string
    representing citizen_id/aadhaar_id to pull from DB) and constructs a
    validated Citizen 360 Profile.
    Validates it against citizen_schema.json.
    """
    if isinstance(citizen_data, str):
        # Input is an ID or Aadhaar; load from DB registry
        profile_data = load_citizen_profile_from_db(citizen_data)
    elif isinstance(citizen_data, dict):
        # Input is a dictionary; check if it is thin and we should fetch from DB
        citizen_id = citizen_data.get("citizen_id")
        aadhaar_id = citizen_data.get("aadhaar_id")
        
        if (citizen_id or aadhaar_id) and len(citizen_data) <= 2:
            identifier = citizen_id if citizen_id else aadhaar_id
            profile_data = load_citizen_profile_from_db(identifier)
        else:
            profile_data = citizen_data
    else:
        raise TypeError("citizen_data must be a dictionary of attributes or an ID/Aadhaar string.")
        
    # Standard normalization of list fields
    verified_docs = profile_data.get("verified_documents", [])
    if isinstance(verified_docs, str):
        verified_docs = [d.strip() for d in verified_docs.split(",") if d.strip()]
    verified_docs = [normalize_document_name(d) for d in verified_docs]
    
    normalized_profile = {
        "citizen_id": str(profile_data.get("citizen_id", "anonymous")),
        "age": profile_data.get("age"),
        "gender": profile_data.get("gender"),
        "state": profile_data.get("state"),
        "district": profile_data.get("district"),
        "urban_rural": profile_data.get("urban_rural"),
        "income_annual": profile_data.get("income_annual"),
        "category": profile_data.get("category"),
        "occupation": profile_data.get("occupation"),
        "education_level": profile_data.get("education_level"),
        "verified_documents": verified_docs
    }
    
    # Fill in the schema booleans if present
    boolean_fields = [
        "has_aadhaar", "has_bank_account", "has_vending_certificate", 
        "has_ulb_recommendation", "has_pucca_house", "is_govt_employee", 
        "pays_income_tax", "owns_motorized_vehicle", "is_institutional_landholder",
        "land_ownership_acres", "existing_benefits"
    ]
    for field in boolean_fields:
        if field in profile_data:
            normalized_profile[field] = profile_data[field]
            
    # Copy other custom fields
    for k, v in profile_data.items():
        if k not in normalized_profile:
            normalized_profile[k] = v
            
    # Clean up keys that are None to avoid schema validation errors if not required
    cleaned_profile = {k: v for k, v in normalized_profile.items() if v is not None}
    
    # Validate against schema
    validate_citizen(cleaned_profile)
    return cleaned_profile


def discover_schemes_tool(profile: dict, query_text: str = None) -> List[Dict[str, Any]]:
    """
    Discovers potential schemes matching a citizen profile.
    Performs dual retrieval:
      1. Qdrant vector similarity search using query_text.
      2. Neo4j graph-based document overlap search using the citizen's verified documents.
    Returns a unified list of unique schemes with metadata.
    """
    candidate_schemes = {}
    
    # Fallback to build a query string if none provided
    if not query_text:
        occupation = profile.get("occupation", "")
        category = profile.get("category", "")
        state = profile.get("state", "")
        query_text = f"schemes for {occupation} {category} in {state}".strip()

    # 1. Qdrant Similarity Search
    try:
        engine = EmbeddingEngine()
        dense_vec, _ = engine.embed_query(query_text)
            
        qdrant_client = QdrantClient(url="http://localhost:6333")
        response = qdrant_client.query_points(
            collection_name="schemes",
            query=dense_vec.tolist(),
            limit=5
        )
        for hit in response.points:
            payload = hit.payload
            scheme_id = payload.get("scheme_id")
            if scheme_id:
                candidate_schemes[scheme_id] = {
                    "scheme_id": scheme_id,
                    "scheme_name": payload.get("scheme_name"),
                    "category": payload.get("category"),
                    "required_documents": payload.get("required_documents", []),
                    "source": "qdrant_similarity"
                }
    except Exception as e:
        print(f"Warning: Qdrant discovery failed: {e}")
        
    # 2. Neo4j Document-based Search
    try:
        verified_docs = profile.get("verified_documents", [])
        graph_matches = find_schemes_by_documents(verified_docs)
        
        # Add fully eligible schemes
        for s in graph_matches.get("fully_eligible", []):
            scheme_id = s["scheme_id"]
            if scheme_id not in candidate_schemes:
                candidate_schemes[scheme_id] = {
                    "scheme_id": scheme_id,
                    "scheme_name": s["scheme_name"],
                    "required_documents": s.get("required_documents", []),
                    "source": "neo4j_document_match"
                }
                
        # Add partially eligible schemes
        for s in graph_matches.get("partially_eligible", []):
            scheme_id = s["scheme_id"]
            if scheme_id not in candidate_schemes:
                candidate_schemes[scheme_id] = {
                    "scheme_id": scheme_id,
                    "scheme_name": s["scheme_name"],
                    "required_documents": s.get("required_documents", []),
                    "source": "neo4j_document_partial"
                }
    except Exception as e:
        print(f"Warning: Neo4j discovery failed: {e}")
        
    return list(candidate_schemes.values())


def evaluate_eligibility_tool(profile: dict, scheme_id: str) -> dict:
    """
    Evaluates the eligibility of a citizen profile against a specific scheme.
    Fetches the scheme properties and required documents from Neo4j,
    recreates the scheme metadata, and calls the evaluator.
    """
    # Fetch details from Neo4j
    query = """
    MATCH (s:Scheme {scheme_id: $scheme_id})
    OPTIONAL MATCH (s)-[:REQUIRES_DOCUMENT]->(d:Document)
    RETURN s.scheme_name AS scheme_name, s.category AS category, collect(d.name) AS required_docs
    """
    scheme_name = None
    required_docs = []
    
    with get_driver() as driver:
        with driver.session() as session:
            record = session.run(query, scheme_id=scheme_id).single()
            if record:
                scheme_name = record["scheme_name"]
                required_docs = record["required_docs"]
                
    if not scheme_name:
        return {
            "scheme_id": scheme_id,
            "status": "INELIGIBLE",
            "missing_fields": [],
            "missing_documents": [],
            "reason": f"Scheme {scheme_id} not found in Neo4j database."
        }
        
    # Fetch eligibility rules from Neo4j
    rules = get_scheme_rules(scheme_id)
    
    # Reconstruct scheme metadata dictionary
    scheme_metadata = {
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "required_documents": required_docs,
        "eligibility_rules": rules
    }
    
    # Evaluate eligibility using the dynamic rules engine
    evaluation = evaluate_scheme_eligibility(profile, scheme_metadata)
    return evaluation


def verify_documents_stub(citizen_id: str, required_docs: List[str]) -> List[str]:
    """
    Mock placeholder representing the Document Verification Agent.
    Simulates checking external registries for document validity, 
    returning a list of successfully verified documents.
    """
    verified = []
    for doc in required_docs:
        norm_doc = normalize_document_name(doc)
        if norm_doc in ["Aadhaar", "Bank Passbook"]:
            verified.append(norm_doc)
        else:
            # Simple deterministic mock verification (exclude caste certificate or vending certificate for certain test users)
            if "Caste" in norm_doc and citizen_id.endswith("even"):
                # Simulates missing caste certificate for testing PENDING_DOCS
                pass
            elif "Vending" in norm_doc and ("poor" in citizen_id or "missing_doc" in citizen_id):
                # Simulates missing vending certificate
                pass
            else:
                verified.append(norm_doc)
    return verified
