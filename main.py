from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.api.auth_routes import router as auth_router
from app.api.ingestion_routes import router as ingestion_router
from app.api.query_routes import router as query_router
from app.api.extraction_routes import router as extraction_router
from app.agents.grievance.routes import router as grievance_router
from app.agents.voice.routes import router as voice_router
from app.agents.briefing.routes import router as briefing_router
from app.agents.entitlement.api.routes import router as entitlement_router
from app.agents.verification.api.routes import router as verification_router
from app.agents.gaca.main import router as gaca_router

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

# Mount static files for PDFs
app.mount("/docs", StaticFiles(directory="storage"), name="docs")

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ingestion_router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(query_router, prefix="/api/v1/query", tags=["Querying"])
app.include_router(extraction_router, prefix="/api/v1/extraction", tags=["Extraction"])
app.include_router(grievance_router, prefix="/api/v1/grievances", tags=["Grievance Agent"])
app.include_router(voice_router, prefix="/api/v1/haptik-webhook", tags=["Voice Agent"])
app.include_router(briefing_router, prefix="/api/v1/briefings", tags=["Briefing Agent"])
app.include_router(entitlement_router, prefix="/api", tags=["Entitlement Agent"])
app.include_router(verification_router, prefix="/api/v1/verification", tags=["Verification Agent"])
app.include_router(gaca_router, prefix="/api/v1/gaca", tags=["Governance & Audit"])

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
    Load and warm up the LLM during server startup.
    """

    print("Loading LLM at startup...")

    # Initialize GACA database tables
    try:
        from app.agents.gaca.database import Base, engine
        Base.metadata.create_all(bind=engine)
        print("OK - GACA Database Tables created/verified")
    except Exception as e:
        print(f"Error initializing GACA database: {e}")

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
