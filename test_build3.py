import json
from app.core.database import get_db_conn
from app.agents.entitlement.services.entitlement_service import build_determination

conn = get_db_conn()
try:
    profile = {
        "income_annual": 250000,
        "occupation": "street_vendor",
        "category": "OBC",
        "land_ownership_acres": 0,
        "has_pucca_house": False,
        "disability_status": False,
        "education_level": "post_matric"
    }
    scheme_matches, determination = build_determination(
        conn=conn, 
        raw_query="Auto generated query", 
        profile=profile, 
        trigger_llm=False
    )
    schemes = determination.get("schemes", [])
    print("Number of schemes from build_determination:", len(schemes))
finally:
    conn.close()
