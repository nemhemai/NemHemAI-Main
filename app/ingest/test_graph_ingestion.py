from app.ingest.graph_ingestor import persist_structured_json

'''sample_data = {
    "act_id": "TEST_ACT_001",
    "act_title": "Test Act",
    "sections": [
        {
            "section_id": "TEST_ACT_001_SEC_1",
            "heading": "Section 1",
            "content": "This is test content.",
            "clauses": []
        },
        {
            "section_id": "TEST_ACT_001_SEC_2",
            "heading": "Section 2",
            "content": "More test content.",
            "clauses": []
        }
    ]
}'''

'''sample_data = {
    "act_id": "FAIL_TEST_001",
    "act_title": "Failure Test Act",
    "sections": [
        {
            "section_id": "FAIL_TEST_001_SEC_1",
            "heading": "Section 1",
            "content": "Content A",
            "clauses": []
        },
        {
            # DUPLICATE ID (intentional)
            "section_id": "FAIL_TEST_001_SEC_1",
            "heading": "Section 1 Duplicate",
            "content": "Content B",
            "clauses": []
        }
    ]
}'''

sample_data = {
    "act_id": "ANOTHER_ACT",
    "act_title": "Another Act",
    "sections": [
        {
            "section_id": "CONFLICT_SEC",  # same as manual
            "heading": "Conflict Section",
            "content": "Different Content",
            "clauses": []
        }
    ]
}

summary = persist_structured_json(sample_data)
print(summary)