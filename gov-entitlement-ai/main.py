from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.auth_routes import router as auth_router
from app.api.ingestion_routes import router as ingestion_router
from app.api.query_routes import router as query_router
from app.api.extraction_routes import router as extraction_router
from app.api.entitlement_routes import router as entitlement_router
from app.api.citizen_routes import router as citizen_router
from app.api.verification_routes import router as verification_router
from app.api.guidance_routes import router as guidance_router
from app.api.audit_routes import router as audit_router

from app.services.query_service import USE_OLLAMA, get_llm
from app.services.ollama_service import get_ollama_llm


# -----------------------------------------------------------------------------
# FastAPI App Initialization
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Government AI Assistant API",
    description="Backend API for document ingestion, querying, and authentication.",
    version="1.0.0",
)


# -----------------------------------------------------------------------------
# CORS Configuration
# -----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Route Registration
# -----------------------------------------------------------------------------

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ingestion_router, prefix="/api", tags=["Ingestion"])
app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(extraction_router, prefix="/api", tags=["Extraction"])
app.include_router(entitlement_router, prefix="/api", tags=["Entitlement"])
app.include_router(citizen_router, prefix="/api/v1/citizen", tags=["Citizen"])
app.include_router(verification_router, prefix="/api/v1/verification", tags=["Verification"])
app.include_router(guidance_router, prefix="/api/v1/application", tags=["Application"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])


# -----------------------------------------------------------------------------
# Health Check Route
# -----------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Government AI Assistant Backend is active",
    }


# -----------------------------------------------------------------------------
# Startup Event
# -----------------------------------------------------------------------------

@app.on_event("startup")
def load_model():
    """
    Clean up active jobs from previous runs and warm up the LLM.
    """
    print("Cleaning up active jobs on startup...")
    try:
        from app.core.database import get_db_conn, release_db_conn
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'FAILED',
                    error = 'Server restarted while job was active',
                    updated_at = NOW()
                WHERE status IN ('UPLOADED', 'REGISTERED', 'EXTRACTING', 'VALIDATING', 'STORING_ELEMENTS', 'CHUNKING', 'EMBEDDING')
            """)
            conn.commit()
        release_db_conn(conn)
        print("OK - Active jobs cleaned up")
    except Exception as e:
        print(f"Error cleaning up active jobs on startup: {e}")

    print("Loading LLM at startup...")

    try:
        if USE_OLLAMA:
            llm = get_ollama_llm()

            # Warm-up request
            llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": "Hello",
                    }
                ],
                max_tokens=1,
            )

            print("OK - Ollama Llama3 Ready")

        else:
            get_llm()
            print("OK - Sarvam Model Loaded")

    except Exception as e:
        print(f"Error loading model: {e}")


# -----------------------------------------------------------------------------
# Shutdown Event
# -----------------------------------------------------------------------------

@app.on_event("shutdown")
def shutdown_event():
    print("Shutting down Government AI Assistant Backend...")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["storage/*", "logs/*", "chunk_outputs/*", "*.pdf", "*.json"]
    )

