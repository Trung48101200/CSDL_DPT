"""
FastAPI application entry point.
Main application setup with middleware, exception handling, and route configuration.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import setup_logging, logger
from app.services.kdtree_service import KDTreeService
from app.routers.audio_router import audio_router, search_router, import_router

# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage FastAPI lifespan events (startup and shutdown).
    """
    # STARTUP
    try:
        logger.info("=" * 80)
        logger.info("Bird Sound CBIR API - STARTUP")
        logger.info("=" * 80)

        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        logger.info("✓ Database initialized")

        # Load ML models (KDTree and Scaler)
        logger.info("Loading ML models...")
        models_loaded = KDTreeService.load_models(
            settings.KDTREE_MODEL_PATH,
            settings.SCALER_MODEL_PATH
        )

        if models_loaded:
            logger.info("✓ ML models loaded successfully")
        else:
            logger.warning(
                "⚠ ML models not fully loaded. Search may not work. "
                "Ensure audio_kdtree.pkl and audio_scaler.pkl exist."
            )

        logger.info("=" * 80)
        logger.info("✓ API READY")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    # SHUTDOWN
    try:
        logger.info("=" * 80)
        logger.info("Bird Sound CBIR API - SHUTDOWN")
        logger.info("=" * 80)

        await close_db()
        logger.info("✓ Database closed")

        KDTreeService.reset()
        logger.info("✓ Models unloaded")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="."), name="root")
app.mount("/bird_images", StaticFiles(directory="bird_images"), name="bird_images")
app.mount("/audio", StaticFiles(directory="bird_sounds_only"), name="audio")

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and response time."""
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )

    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else None,
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

app.include_router(audio_router)
app.include_router(search_router)
app.include_router(import_router)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get(
    "/",
    summary="Root endpoint",
    description="Welcome message and API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/search/health"
    }


@app.get(
    "/health",
    summary="Health check",
    description="Check API health status"
)
async def health():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.API_VERSION
    }


# ============================================================================
# APP INFO AT MODULE LEVEL
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
