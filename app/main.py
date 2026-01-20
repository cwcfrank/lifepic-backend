"""
FastAPI application main module - Feedback API only.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feedback


app = FastAPI(
    title="Feedback API",
    description="問題回報服務 - 支援圖片上傳與郵件通知",
    version="1.0.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include feedback router only
app.include_router(feedback.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": "Feedback API",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
