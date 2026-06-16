import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.agents.verification.api.routes import router

from app.agents.verification.core.config import settings
from app.agents.verification.core.logger import (
    logger,
    setup_logging
)

from app.agents.verification.core.exceptions import AppException


# =========================================
# LOGGING SETUP
# =========================================

setup_logging()


# =========================================
# FASTAPI APPLICATION
# =========================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Enterprise AI Verification Platform"
    ),
    version="1.0.0",
    debug=settings.DEBUG
)


# =========================================
# GLOBAL EXCEPTION HANDLER
# =========================================

@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException
):

    trace_id = str(uuid.uuid4())

    logger.error(
        "Application exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        trace_id=trace_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "trace_id": trace_id
        }
    )


# =========================================
# STARTUP EVENT
# =========================================

@app.on_event("startup")
async def startup_event():

    logger.info(
        "Application startup complete"
    )


# =========================================
# SHUTDOWN EVENT
# =========================================

@app.on_event("shutdown")
async def shutdown_event():

    logger.info(
        "Application shutdown complete"
    )


# =========================================
# ROUTES
# =========================================

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/api/v1/")

app.include_router(
    router,
    prefix="/api/v1",
    tags=["API"]
)