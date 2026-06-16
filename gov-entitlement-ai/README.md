# Gov Entitlement AI Backend (Standalone)

This is a standalone, self-contained export of the Entitlement Agent and its accompanying RAG (Retrieval-Augmented Generation) ingestion pipeline, extracted from the NemHemAI platform. 

It contains the backend logic, database schemas, PDF guidelines, tests, and a CLI ingestion script, allowing integration into external orchestration engines or orchestrators.

---

## Folder Structure

* `app/`: Contain core modules including the entitlement agent graph, rule matcher, embedding generator, vector store, and chunking pipeline.
* `data/entitlement/`: Standard PDF scheme guidelines (PMAY-U, PM SVANidhi, PM-Kisan, PM-KUSUM, Post-Matric Scholarship) with corresponding metadata JSON files.
* `scripts/ingest_documents.py`: CLI ingestion script to run the RAG pipeline directly without a frontend web interface.
* `tests/`: Integration and unit tests.
* `create_db.py`: Quick helper to create the Postgres database.
* `requirements.txt`: Python package requirements.
* `.env.example`: Configuration templates for databases and Ollama connection parameters.

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

1. **Python 3.10+**
2. **PostgreSQL** with the `pgvector` extension installed and enabled.
3. **Ollama** installed locally (running with the `llama3` model pulled: `ollama pull llama3`).

---

## Quick Start Setup

Follow these steps to initialize and run the Entitlement Agent backend on your machine.

### 1. Set Up Python Virtual Environment

Navigate into the standalone directory and create a virtual environment:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows (cmd/PowerShell):
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a copy of `.env.example` named `.env`:

```bash
copy .env.example .env
```

Open `.env` and fill in your PostgreSQL credentials and Ollama endpoint:

```ini
# Database configurations
DB_USER=your_db_username_here
DB_PASS=your_db_password_here
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=nemhem_db

# Database connection URL
DATABASE_URL=postgresql://your_db_username_here:your_db_password_here@127.0.0.1:5432/nemhem_db

# LLM Config (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### 3. Initialize Database and Tables

Run the database creation script, followed by the migration scripts to initialize all necessary tables and schemas:

```bash
# 1. Create the database
python create_db.py

# 2. Run all schema files and migrations
python app/database/init_db.py
```

### 4. Ingest Guidelines Documents (RAG Setup)

Run the CLI document ingestion script. It will automatically detect all PDF files under `data/entitlement/` (and their respective `.json` metadata sidecars), parse, chunk, embed, and store them in the Postgres vector database:

```bash
# Run ingestion for all documents in the default folder
python scripts/ingest_documents.py

# (Optional) Run ingestion for a specific file
python scripts/ingest_documents.py --file data/entitlement/PM_SVANidhi_English.pdf

# (Optional) Run ingestion for another directory
python scripts/ingest_documents.py --dir /path/to/custom/pdf/folder
```

### 5. Running the Entitlement Agent (Programmatic Usage)

You can call the entitlement agent directly from Python using the following code snippet:

```python
import os
from dotenv import load_dotenv

# Load configuration
load_dotenv()

from app.services.entitlement_service import entitlement_agent

# The user query containing user criteria
query = "I am a street vendor in an urban area with a valid vending certificate. Am I eligible for any schemes?"

# Invoke the entitlement agent
result = entitlement_agent(
    raw_query=query,
    citizen_id="citizen-123",  # Optional: unique citizen identifier
    user_id="user-456"         # Optional: uuid of the operator calling the agent
)

# Print execution results
print("Execution Status:", result["status"])
print("Overall Verdict:", result["determination"]["verdict"])
print("Reasoning Summary:", result["determination"]["explanation"]["reasoning"])
```

---

## Running Verification Tests

To verify that all components are self-contained and run correctly, execute `pytest` in the directory root:

```bash
pytest
```
