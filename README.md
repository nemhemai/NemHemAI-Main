# NemhemAI — FastAPI + Ollama Backend

A modern AI assistant with a React/Vite frontend and a FastAPI backend powered by local Ollama models. The backend includes authentication, file uploads (PDF/DOCX/Image OCR), CSV data analysis with AI-generated code, and multiple search integrations.

## Features

- **Local LLMs (Ollama)**: Uses local models via Ollama for `/ask` and data analysis.
- **Auth + RBAC**: Username/password login with JWT and `admin` role support.
- **Files + OCR**: Upload PDFs, DOCX, and images; extracts text with `pytesseract`.
- **CSV Analysis**: Upload CSVs, run AI-generated or fallback analysis code, and plot charts.
- **SQL Explorer**: Save CSVs to SQLite and run safe `SELECT` queries.
- **Search Integrations**: DuckDuckGo (free), optional Exa/Tavily endpoints.
- **Desktop/Electron**: Scripts provided to package as desktop apps.

## Quick Start

### Prerequisites

- Windows (tested), Python 3.10+ and `pip`
- Node.js 18+ and npm
- Ollama installed and in PATH (https://ollama.com)
- Optional: Tesseract OCR for image text extraction (https://tesseract-ocr.github.io/)
- Optional: `EXA_API_KEY` and `TAVILY_API_KEY` for extra search endpoints

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` in `backend/` (loaded via `dotenv`):

   ```env
   # Comma-separated keys (optional, diagnostic only)
   OPENROUTER_API_KEYS=key1,key2

   # Frontend origins
   ALLOWED_ORIGINS=http://localhost:8001,http://127.0.0.1:8001

   # Optional search API keys
   EXA_API_KEY=your_exa_key
   TAVILY_API_KEY=your_tavily_key

   # Optional server port
   PORT=8000

   # Desktop mode storage behavior (set to 1 when packaging)
   DESKTOP_MODE=0
   ```

4. Ensure required Ollama models are available (first run pulls automatically and may take time):

   ```bash
   ollama pull llama3.1:latest
   ollama pull mistral:latest
   ollama pull qwen2.5vl:latest
   ollama pull deepseek-coder-v2:latest
   ```

5. Start the backend:

   ```bash
   python main.py
   ```

   Server runs at `http://localhost:8000`. On first launch, models may download.

### Frontend Setup

1. From the project root:

   ```bash
   npm install
   npm run dev
   ```

   Vite dev server runs at `http://localhost:8001`. Update API base in the frontend if needed.

## Authentication

- Flow: Register → Login → Use `Authorization: Bearer <token>` for protected endpoints.
- Endpoints:
  - `POST /register` — body: `{ "username": "u", "password": "p", "role": "user" }`
  - `POST /login` — OAuth2 form (`username`, `password`) returns `{ access_token, token_type }`
  - `GET /me` — current user info
  - `GET /admin-only` — requires `role = admin`

Example (PowerShell):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/register -ContentType 'application/json' -Body '{"username":"test","password":"pass"}'
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/login -Body @{ username='test'; password='pass' }
$token = $login.access_token
Invoke-RestMethod -Method Get -Uri http://localhost:8000/me -Headers @{ Authorization="Bearer $token" }
```

## API Overview

- **Health**: `GET /health` — backend status.
- **Ask (LLM)**: `POST /ask` — body `{ prompt, model, session_id }` (streams JSONL). Requires auth.
- **Files**: `POST /upload?session_id=...` — multipart files (PDF/DOCX/Image) with OCR; stores text per session.
- **CSV Upload**: `POST /upload-csv?session_id=...` — returns shape, columns, dtypes, sample; saves data to SQLite.
- **Data Analysis**: `POST /data-analysis` — body `{ prompt, session_id, model? }`; streams code, output, and base64 chart.
- **CSV Info**: `GET /csv-info?session_id=...` — last uploaded CSV metadata.
- **SQL Explorer**:
  - `GET /list-tables` — tables in `databases/analysis.db`.
  - `GET /describe-table?table_name=...` — columns and types.
  - `POST /execute-sql?query=SELECT ...` — only `SELECT` allowed.
- **Search**:
  - `GET /search/duckduckgo?query=...` — free multi-strategy search.
  - `GET /search/web?query=...` — Exa API (requires `EXA_API_KEY`).
  - `GET /search/youtube|reddit|academic|crypto?query=...` — Tavily (requires `TAVILY_API_KEY`).
- **Chat History**:
  - `POST /history` — save `{ session_id, prompt, response }`.
  - `GET /history?session_id=...` — list messages for session.
- **Trial**: `GET /trial-remaining` — per-user remaining seconds.
- **Diagnostics**: `GET /debug/keys` — show parsed `OPENROUTER_API_KEYS` (optional).

## Models (Ollama)

- Allowed models include: `llama3.1:latest`, `mistral:latest`, `deepseek-coder-v2:latest`, `anindya/prem1b-sql-ollama-fp116:latest`, `llama3.1:8b`, `qwen2.5vl:latest`, `codellama:latest`, and others defined in [ALLOWED_OLLAMA_MODELS](backend/main.py#L277).
- On startup, required models are ensured via pulls defined near the end of [backend/main.py](backend/main.py#L1801-L1813).

## Data & Storage

- **Uploads**: Files stored in `[backend/uploads]` and `[backend/csv_uploads]` based on mode.
- **CSV → SQL**: Saved to `databases/analysis.db`; browse with the SQL Explorer endpoints.
- **Desktop Mode**: When `DESKTOP_MODE=1`, uses current working directory for data.

## Frontend Notes

- Dev server port: `8001` (see [vite.config.ts](vite.config.ts#L28-L35)).
- Update API base in your frontend client if your backend port differs.

## Troubleshooting

- **Ollama not found**: Ensure `ollama` is installed and available in PATH; first run may download large models.
- **CORS errors**: Update `ALLOWED_ORIGINS` in `.env` to include your frontend origin.
- **SQLite locks**: Avoid multiple writes concurrently; CSV writes use `replace`.
- **OCR missing**: Install Tesseract OCR if image text extraction fails.
- **Long analysis**: Data analysis requests may stream for a while; check status messages in the stream.

## Desktop & Electron

- See Windows/macOS packaging guides: [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md), [BUILD_MAC.md](BUILD_MAC.md), and Electron docs in [electron/](electron).

## License & Contributing

- License: MIT
- Contributions welcome: fork, branch, PR. See project docs for full distribution and setup guides.
