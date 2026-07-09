# Handover Documentation

This document covers system maintenance instructions and next steps for the NemHem AI Entitlement Engine.

## Running the Application
The system comprises two core components:
1. **Backend (FastAPI)**: Run from the `entitlement` directory:
   ```bash
   .\.venv\Scripts\python -m uvicorn app.core.metadata.api:app --host 0.0.0.0 --port 8000
   ```
2. **Frontend (React)**: Run from the `rag-dashboard` directory:
   ```bash
   npm start
   ```

## Key Infrastructure and Repositories
- **Neo4j Graph Database**: Runs locally on `bolt://localhost:7687`. Handles document relationships and logical eligibility rules.
- **Qdrant Vector Database**: Runs locally on `http://localhost:6333`. Handles semantic matching of free-text queries to scheme metadata.
- **PostgreSQL**: Runs locally. Handles the mock Citizen 360 Profile and Document Registry.

## Testing Profiles (Personas)
We have implemented 5 test personas in `tests/test_day7_personas.py`:
1. `test_perfect_vendor` - Eligible for PM SVANidhi.
2. `test_missing_doc_vendor` - Missing Vending Certificate for PM SVANidhi.
3. `test_perfect_farmer` - Eligible for PM-KISAN.
4. `test_wealthy_farmer` - Excluded from PM-KISAN due to `pays_income_tax = true`.
5. `test_generic_student` - No specific matches.

You can simulate these personas in the UI by using their `citizen_id` if they are registered in your PostgreSQL database, or run the test suite:
```bash
.\.venv\Scripts\python -m pytest tests/test_day7_personas.py
```

## Adding New Schemes
To add a new scheme to the system:
1. **Create Metadata YAML**: In `app/core/metadata/records/`, create a new `.yaml` file containing the `scheme_id`, `eligibility_rules`, `required_documents`, and `benefit` payload.
2. **Re-Index Graph & Vector**: Run the Neo4j/Qdrant ingestion scripts (`ingest.py` or similar) to parse the YAML into graph nodes and vector points.
3. **Add PDF Source Document**: Place the actual PDF Guidelines inside the system. Ensure the name matches the `.yaml` name exactly but with `.pdf`.

## Future Improvements
- Implement a real authentication provider (e.g., actual Keycloak or Auth0).
- Integrate a live document verification registry instead of the mock `verify_documents_stub`.
- Implement dynamic PDF chunking and retrieval using Langchain for actual RAG-based context extraction for citations.
