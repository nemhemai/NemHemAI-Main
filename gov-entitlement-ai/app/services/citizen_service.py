# app/services/citizen_service.py

from typing import Any
import uuid
import json
from app.core.database import get_db_conn, release_db_conn

# Verhoeff algorithm tables
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 1, 4, 6, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff(num_str: str) -> bool:
    try:
        c = 0
        length = len(num_str)
        for i in range(length):
            p_idx = i % 8
            digit = int(num_str[length - 1 - i])
            c = VERHOEFF_D[c][VERHOEFF_P[p_idx][digit]]
        return c == 0
    except (ValueError, IndexError):
        return False

def register_citizen(mobile_number: str, aadhaar_id: str, email: str = None) -> dict[str, Any]:
    """
    Step 1: Citizen Registration & Step 2: Identity Verification.
    Verifies citizen against internal registers / simulated municipal records and registers them.
    """
    mobile_number = mobile_number.strip()
    aadhaar_id = aadhaar_id.strip()
    email = email.strip() if email else None

    # Validate mobile number format
    if len(mobile_number) != 10 or not mobile_number.isdigit():
        return {
            "success": False,
            "message": "Identity Verification Failed: Invalid Mobile number format. Must be a 10-digit numeric code."
        }

    # Step 2: Mock Identity Verification sources (Municipal/State registry check)
    # Production note: In real app, this would hit UIDAI/municipal APIs
    if not aadhaar_id.isdigit():
        return {
            "success": False,
            "message": "Identity Verification Failed: Aadhaar ID must be numeric only."
        }

    if len(aadhaar_id) != 12:
        return {
            "success": False,
            "message": "Identity Verification Failed: Aadhaar ID must be exactly 12 digits."
        }

    if aadhaar_id[0] in ('0', '1'):
        return {
            "success": False,
            "message": "Identity Verification Failed: Aadhaar ID first digit cannot be 0 or 1."
        }

    if not validate_verhoeff(aadhaar_id):
        return {
            "success": False,
            "message": "Identity Verification Failed: Aadhaar ID failed Verhoeff checksum validation."
        }

    # Validate email format if provided
    import re
    if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return {
            "success": False,
            "message": "Identity Verification Failed: Invalid Email address format."
        }

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Check if citizen already registered
            cur.execute("""
                SELECT citizen_id, is_verified, verification_source 
                FROM citizens 
                WHERE mobile_number = %s OR aadhaar_id = %s
            """, (mobile_number, aadhaar_id))
            row = cur.fetchone()

            if row:
                citizen_id, is_verified, source = row
                return {
                    "success": True,
                    "citizen_id": str(citizen_id),
                    "is_verified": is_verified,
                    "verification_source": source,
                    "message": "Citizen already registered and verified."
                }

            # Simulate municipal/state database check (Step 2)
            # 99% of registrations succeed with mock validation
            is_verified = True
            verification_source = "State Municipal & UIDAI Cross-Verification Portal"

            citizen_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO citizens (citizen_id, mobile_number, aadhaar_id, email, is_verified, verification_source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (citizen_id, mobile_number, aadhaar_id, email, is_verified, verification_source))
            
            # Step 3: Create initial empty profile
            cur.execute("""
                INSERT INTO citizen_profiles (citizen_id, personal_info, household_info, socio_economic_info, existing_benefits)
                VALUES (%s, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb)
            """, (citizen_id,))
            
            conn.commit()
            return {
                "success": True,
                "citizen_id": citizen_id,
                "is_verified": is_verified,
                "verification_source": verification_source,
                "message": "Citizen identity verified and profile successfully created."
            }
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Registration failed: {str(e)}")
    finally:
        release_db_conn(conn)

def get_citizen_profile(citizen_id: str) -> dict[str, Any]:
    """
    Step 3: Fetch Citizen 360 Profile.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.mobile_number, c.aadhaar_id, c.email, c.is_verified, 
                       p.personal_info, p.household_info, p.socio_economic_info, p.existing_benefits
                FROM citizens c
                JOIN citizen_profiles p ON c.citizen_id = p.citizen_id
                WHERE c.citizen_id = %s
            """, (citizen_id,))
            row = cur.fetchone()
            if not row:
                raise Exception("Citizen profile not found.")
            
            mobile, aadhaar, email, is_verified, personal, household, socio, benefits = row
            
            # Combine into a unified Citizen 360 Profile object
            return {
                "citizen_id": citizen_id,
                "mobile_number": mobile,
                "aadhaar_id": aadhaar,
                "email": email,
                "is_verified": is_verified,
                "personal_info": personal,
                "household_info": household,
                "socio_economic_info": socio,
                "existing_benefits": benefits
            }
    finally:
        release_db_conn(conn)

def update_citizen_profile(
    citizen_id: str, 
    personal_info: dict, 
    household_info: dict, 
    socio_economic_info: dict,
    existing_benefits: list = None
) -> dict[str, Any]:
    """
    Step 3: Update Citizen 360 Profile and re-evaluate Socio-Economic Assessment.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM citizens WHERE citizen_id = %s", (citizen_id,))
            if not cur.fetchone():
                raise Exception("Citizen not found.")

            # Profile fields validation checks
            income = socio_economic_info.get("income_annual", 0)
            dependents = household_info.get("dependents_count", 0)
            land_ownership = socio_economic_info.get("land_ownership_acres", 0.0)

            if income < 0:
                raise ValueError("Annual household income must be a non-negative number.")
            if dependents < 0:
                raise ValueError("Dependents count must be a non-negative number.")
            if land_ownership < 0:
                raise ValueError("Land ownership must be a non-negative number.")

            benefits = existing_benefits if existing_benefits is not None else []

            # Update DB profile columns
            cur.execute("""
                UPDATE citizen_profiles
                SET personal_info = %s,
                    household_info = %s,
                    socio_economic_info = %s,
                    existing_benefits = %s,
                    updated_at = NOW()
                WHERE citizen_id = %s
            """, (
                json.dumps(personal_info),
                json.dumps(household_info),
                json.dumps(socio_economic_info),
                json.dumps(benefits),
                citizen_id
            ))
            conn.commit()
            
            # Run socio-economic assessment (Step 4)
            assessment = assess_household_and_socio_economic(personal_info, household_info, socio_economic_info)
            
            return {
                "citizen_id": citizen_id,
                "profile_360": {
                    "personal_info": personal_info,
                    "household_info": household_info,
                    "socio_economic_info": socio_economic_info,
                    "existing_benefits": benefits
                },
                "eligibility_context_model": assessment
            }
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Profile update failed: {str(e)}")
    finally:
        release_db_conn(conn)

def assess_household_and_socio_economic(personal_info: dict, household_info: dict, socio_economic_info: dict) -> dict[str, Any]:
    """
    Step 4: Household & Socio-Economic Assessment.
    Builds the Eligibility Context Model based on personal, household, and socio-economic markers.
    """
    income = socio_economic_info.get("income_annual", 0)
    category = socio_economic_info.get("category", "General")
    
    # Household determination logic
    bpl_apl_status = "APL"
    if income <= 120000:
        bpl_apl_status = "BPL" # Below Poverty Line threshold mock
        
    dependents = household_info.get("dependents_count", 0)
    has_seniors = household_info.get("has_senior_citizens", False)
    has_students = household_info.get("has_students", False)
    has_widows = household_info.get("has_widows", False)
    has_disabled = socio_economic_info.get("disability_status", False)
    
    occupation = socio_economic_info.get("occupation", "unemployed")
    is_farmer = (occupation == "farmer")
    
    return {
        "bpl_apl_status": bpl_apl_status,
        "household_income": income,
        "applicant_category": category,
        "dependents_count": dependents,
        "has_senior_citizens": has_seniors,
        "has_students": has_students,
        "has_widows": has_widows,
        "is_farmer": is_farmer,
        "has_disabled_members": has_disabled,
        "state": personal_info.get("state", "Unknown"),
        "urban_rural": personal_info.get("urban_rural", "urban"),
        "land_ownership_acres": socio_economic_info.get("land_ownership_acres", 0.0),
        "education_level": socio_economic_info.get("education_level", "none"),
        "has_pucca_house": socio_economic_info.get("has_pucca_house", False)
    }
