Abstract

This project implements an on-premise, retrieval-augmented decision support system designed for Maharashtra Government / BMC-style administrative use cases. The system ingests statutory Acts (JSON) and reference documents (PDFs), converts them into structured semantic embeddings, and enables controlled, auditable, and conservative policy reasoning.

The system does not approve, reject, or recommend actions. Instead, it assists officers by retrieving relevant legal provisions, clearly separating what can be concluded, what cannot be concluded, and what requires further confirmation, ensuring defensible decision-making under policy ambiguity.

Key outcomes achieved:
Large-scale ingestion of statutory and contextual documents
Authority-aware metadata tagging (statutory vs contextual)
Persistent vector database for fast semantic retrieval
Conservative RAG responses with explicit limitations
Modular, production-ready code structure suitable for team testing

Project Structure:-
policy-rag/
├─ app/
│  ├─ ingest/
│  ├─ retrieval/
│  ├─ rag/
│  ├─ llm/
│  └─ config/
│
├─ data/                 # RAW DATA ONLY (gitignored)
│  ├─ json_files/
│  └─ pdf_files/
│
├─ vector_store/         # SINGLE VECTOR DB LOCATION (gitignored)
│
├─ notebooks/            # Optional experiments only
│
├─ main.py
├─ README.md
├─ requirements.txt
└─ .gitignore


🔧 Prerequisites
Python 3.9+
Virtual environment support
GROQ API key (for LLM inference)

🚀 Setup Instructions
1️⃣ Clone the Repository
git clone https://github.com/ayushvakani/policy-rag
cd policy-rag
2️⃣ Create and Activate Virtual Environment
python -m venv .venv
.venv\Scripts\activate
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Configure Environment Variables
Create a .env file at the project root:
GROQ_API_KEY=your_groq_api_key_here
5️⃣ Add Data
data/
├── pdf_files/     # PDFs (manuals, reports, reference docs)
└── json_files/    # Acts, rules, circulars (structured JSON)

📥 One-Time Ingestion Step
⚠️ This step can take significant time depending on data size.
python -m app.ingest.ingest_documents

▶️ Running the System
After ingestion is complete, you need to start both the backend and frontend servers.

**1. Start the Backend Server:**
Open a terminal in the root directory and run:
```bash
python main.py
```
This will start the FastAPI backend server on `http://localhost:8000`.

**2. Start the Frontend Dashboard:**
Open a new terminal, navigate to the dashboard directory, and start the React app:
```bash
cd rag-dashboard
npm start
```
This will start the frontend on `http://localhost:3000`.

🌍 Project Routes
- **Frontend Dashboard:** `http://localhost:3000`
- **Backend API Docs (Swagger):** `http://localhost:8000/docs`
- **Backend API Redoc:** `http://localhost:8000/redoc`

🔍 Example Queries

What penalties are prescribed under the Act 1967?
Are contractual sanitation workers eligible for welfare benefits?
Does non-segregation of waste attract penalties under municipal rules?
Which provisions govern solid waste management responsibilities?



