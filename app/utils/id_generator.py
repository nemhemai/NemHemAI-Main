import uuid
import re


def generate_act_id(act_title: str) -> str:
    """
    Generates clean Act ID like:
    INSURANCE_ACT_1938
    """
    year_match = re.search(r"\b(18|19|20)\d{2}\b", act_title)
    year = year_match.group() if year_match else ""


    words = re.sub(r"[^A-Za-z ]", "", act_title).split()
    short = "_".join(words[:3]).upper()


    return f"{short}_{year}"


def generate_section_id(act_id: str, section_label: str, version: int = 1) -> str:
    """
    Generates:
    INSURANCE_ACT_1938_SEC_1_v1
    """
    clean_section = re.sub(r"[^0-9A-Za-z]", "", section_label)
    return f"{act_id}_SEC_{clean_section}_v{version}"


def generate_chunk_id(section_id: str) -> str:
    """
    Unique ID for embedding chunks
    """
    return f"{section_id}_{uuid.uuid4().hex[:8]}"

