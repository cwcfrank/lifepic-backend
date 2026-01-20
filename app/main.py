"""
FastAPI application main module.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import parking, sync, charging, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown (cleanup if needed)


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="停車場與充電站資料中台服務 - 整合 TDX 運輸資料流通服務",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(parking.router)
app.include_router(charging.router)
app.include_router(sync.router)
app.include_router(feedback.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": settings.app_name,
        "status": "healthy",
        "version": "1.1.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
