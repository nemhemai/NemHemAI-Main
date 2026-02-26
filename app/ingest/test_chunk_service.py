from app.ingest.chunk_service import prepare_chunks

sample_data = {
    "act_id": "TEST_ACT_2024",
    "sections": [
        {
            "section_id": "TEST_ACT_2024_SEC_1_v1",
            "content": "This Act may be called the Test Act, 2024. " * 20
        }
    ]
}

chunks = prepare_chunks(sample_data)

print("Total Chunks:", len(chunks))
print(chunks[0])