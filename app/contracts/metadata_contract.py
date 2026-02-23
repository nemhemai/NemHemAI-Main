REQUIRED_FIELDS = [
    "act_title",
    "act_id",
    "section_id",
    "section_number",
    "authority_level",
    "source_type",
]

OPTIONAL_FIELDS = [
    "hierarchy_type",     # part OR chapter
    "hierarchy_name",
    "section_heading",
    "document_class",
    "source",
]


def validate_metadata(metadata: dict):
    for field in REQUIRED_FIELDS:
        if field not in metadata:
            raise ValueError(f"Missing required metadata field: {field}")