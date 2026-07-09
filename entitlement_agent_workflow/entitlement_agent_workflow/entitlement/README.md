# Standalone Government Entitlement Agent

This is a self-contained, metadata-driven Government Entitlement Agent subsystem. It provides dynamic welfare scheme discovery, rule evaluation, Neo4j eligibility knowledge graphing, Keycloak-based role gating (RBAC), and OpenHuman context intent shaping.

---

## Architecture Overview

The entitlement agent is composed of:
1. **Dynamic Evaluator**: Intake Citizen 360 profiles and run complex condition checks (operators like `eq`, `lt`, `between`, `in`) specified in metadata JSON schemas.
2. **Knowledge Graph (Neo4j)**: Maps schemes, required documents, rules, and rule fields as nodes and relationships.
3. **Semantic Search (Qdrant)**: Batch-encodes policy descriptions using BGE-M3 and performs cosine similarity search.
4. **Multi-Agent Pipeline (PaisonAI)**: Intakes citizen details, executes discovery tools, and feeds contextual alerts/verifications into Ollama (`llama3.1`) for explanation generation.
5. **Keycloak RBAC**: Decodes RS256 JWT tokens to enforce user access policies for `CITIZEN`, `OFFICER`, and `ADMIN` roles.
6. **OpenHuman Memory**: Shapes queries dynamically using conversation history, detects confusion intents, and adapts output tone depending on the user's role.

---

## Setup & Prerequisites

Before running the application, make sure the following local services are active:
* **PostgreSQL Database**: Port `5433` (DB: `nemhem_db`, User: `postgres`).
* **Qdrant Vector DB**: Port `6333` (runs semantic scheme matches).
* **Neo4j Graph Database**: Port `7687` (runs schema rules graphing).
* **Ollama (Local LLM)**: Port `11434` with the `llama3.1` model downloaded (`ollama pull llama3.1`).

---

## Installation Steps

1. Navigate to the `entitlement` folder.
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install required libraries:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Data Ingestion & Indexing

To load the 20 central and state welfare scheme rules and text guidelines into the databases, execute the following indexing scripts:

### 1. Vector Search Indexing (Qdrant)
Encodes the textual descriptions of the schemes from `records/*.yaml` using the BGE-M3 model and registers them as vectors in Qdrant:
```powershell
$env:PYTHONPATH="."
python -m app.core.metadata.index_qdrant
```

### 2. Knowledge Graph Indexing (Neo4j)
Creates unique constraints and inserts all rules, documents, and schemes as nodes in Neo4j:
```powershell
$env:PYTHONPATH="."
python -m app.core.metadata.index_neo4j
```

---

## Running the Standalone API Gateway

Run the unified API Gateway server:
```powershell
$env:PYTHONPATH="."
python -m app.core.metadata.api
```
The server will boot on `http://localhost:8000` and handle all backend calls for the React Dashboard.

---

## Testing

To run the complete 28-test suite (covers evaluator rules, graph traversal, Keycloak role gating, and OpenHuman adaptive responses):
```powershell
$env:PYTHONPATH="."
python -m pytest tests/
```
