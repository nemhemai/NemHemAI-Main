import json
from app.core.database import get_db_conn
from app.agents.entitlement.services.entitlement_service import build_determination

conn = get_db_conn()
try:
    scheme_matches, determination = build_determination(
        conn=conn, 
        raw_query="I am a farmer", 
        profile={"occupation": "farmer", "land_ownership_acres": 2}, 
        trigger_llm=False
    )
    schemes = determination.get("schemes", [])
    print("Number of schemes from build_determination:", len(schemes))
    if schemes:
        print("First scheme:", schemes[0]["scheme_name"])
finally:
    conn.close()
