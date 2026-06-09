from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.auth_routes import router as auth_router
from app.api.ingestion_routes import router as ingestion_router
from app.api.query_routes import router as query_router
from app.api.extraction_routes import router as extraction_router
from app.agents.grievance.routes import router as grievance_router
from app.agents.voice.routes import router as voice_router

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
app.include_router(ingestion_router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(extraction_router, prefix="/api", tags=["Extraction"])
app.include_router(grievance_router, prefix="/api/v1/grievances", tags=["Grievances"])
app.include_router(voice_router, prefix="/api/v1", tags=["Voice Agent"])


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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
