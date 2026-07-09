import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def get_nested_value(d: Dict[str, Any], path: str) -> Any:
    """Helper to get a value from a nested dictionary using a dot-separated path (e.g. 'personal_info.age').
    If not found, falls back to checking the key flat in the dict.
    """
    if path in d:
        return d[path]

    parts = path.split(".")
    current = d
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def evaluate_operator(profile_value: Any, operator: str, rule_value: Any) -> bool:
    """Evaluates a comparison operator between a profile value and a rule value.
    Handles type conversion errors gracefully.
    """
    if profile_value is None:
        return False

    try:
        if operator == "eq":
            # Direct comparison, check if strings match case-insensitively
            if isinstance(profile_value, str) and isinstance(rule_value, str):
                return profile_value.lower().strip() == rule_value.lower().strip()
            return profile_value == rule_value

        elif operator == "neq":
            if isinstance(profile_value, str) and isinstance(rule_value, str):
                return profile_value.lower().strip() != rule_value.lower().strip()
            return profile_value != rule_value

        elif operator == "lt":
            return float(profile_value) < float(rule_value)

        elif operator == "lte":
            return float(profile_value) <= float(rule_value)

        elif operator == "gt":
            return float(profile_value) > float(rule_value)

        elif operator == "gte":
            return float(profile_value) >= float(rule_value)

        elif operator == "in":
            if isinstance(rule_value, list):
                # normalize strings for case-insensitive check
                normalized_rule_val = [v.lower().strip() if isinstance(v, str) else v for v in rule_value]
                val = profile_value.lower().strip() if isinstance(profile_value, str) else profile_value
                return val in normalized_rule_val
            return profile_value == rule_value

        elif operator == "between":
            if isinstance(rule_value, list) and len(rule_value) == 2:
                val = float(profile_value)
                return float(rule_value[0]) <= val <= float(rule_value[1])
            return False

        else:
            logger.warning(f"Unsupported operator: {operator}")
            return False

    except (ValueError, TypeError) as e:
        logger.warning(f"Type comparison error between profile value {profile_value!r} and rule value {rule_value!r} using {operator}: {e}")
        return False


def evaluate_scheme_eligibility(profile: Dict[str, Any], scheme: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates a dynamic Citizen 360 Profile against a Schema Metadata record.

    Decision Matrix:
    1. INELIGIBLE: Any eligibility rule evaluates to False, or any exclusion rule evaluates to True.
    2. INCOMPLETE_PROFILE: No disqualifiers matched, but one or more required rules could not be evaluated
       because their fields are absent/None in the citizen profile.
    3. PENDING_DOCS: All eligibility rules pass, but one or more required documents are missing or unverified.
    4. ELIGIBLE: All rules pass and all required documents are verified.
    """
    scheme_id = scheme.get("scheme_id", "unknown")
    scheme_name = scheme.get("scheme_name", "Unknown Scheme")
    
    rules = scheme.get("eligibility_rules", [])
    required_docs = scheme.get("required_documents", [])
    verified_docs = [doc.lower().strip() for doc in profile.get("verified_documents", []) if isinstance(doc, str)]

    matched_rules = []
    failed_rules = []
    missing_fields = []
    disqualified = False
    reasons = []

    for rule in rules:
        field = rule.get("field")
        operator = rule.get("operator")
        rule_val = rule.get("value")
        is_exclusion = rule.get("is_exclusion", False)

        if not field or not operator:
            continue

        profile_val = get_nested_value(profile, field)

        # Check if field is missing from profile
        if profile_val is None:
            missing_fields.append(field)
            continue

        result = evaluate_operator(profile_val, operator, rule_val)

        if is_exclusion:
            # Exclusion matched -> Citizen is disqualified
            if result:
                disqualified = True
                failed_rules.append(rule)
                reasons.append(f"Exclusion rule matched: {field} satisfies exclusion rule ({operator} {rule_val}).")
            else:
                matched_rules.append(rule)
        else:
            # Normal eligibility rule must match
            if result:
                matched_rules.append(rule)
            else:
                disqualified = True
                failed_rules.append(rule)
                reasons.append(f"Eligibility rule failed: {field} ({profile_val}) did not satisfy {operator} {rule_val}.")

    # Evaluate States:
    if disqualified:
        status = "INELIGIBLE"
    elif missing_fields:
        status = "INCOMPLETE_PROFILE"
        reasons.append(f"Profile is missing required information for: {', '.join(sorted(set(missing_fields)))}.")
    else:
        # Check required documents
        missing_docs = []
        for doc in required_docs:
            if not isinstance(doc, str):
                continue
            normalized_doc = doc.lower().strip()
            if normalized_doc not in verified_docs:
                missing_docs.append(doc)

        if missing_docs:
            status = "PENDING_DOCS"
            reasons.append(f"Eligible but waiting for verification of: {', '.join(missing_docs)}.")
        else:
            status = "ELIGIBLE"
            reasons.append("Citizen qualifies for the scheme and all required documents are verified.")

    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "status": status,
        "matched_rules": matched_rules,
        "failed_rules": failed_rules,
        "missing_fields": sorted(list(set(missing_fields))),
        "missing_documents": missing_docs if status == "PENDING_DOCS" else ([] if status == "ELIGIBLE" else required_docs),
        "reasons": reasons
    }
