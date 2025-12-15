"""
Vercel serverless entry point for FastAPI application.
"""
from app.main import app

# Vercel requires the app to be named 'app' or 'handler'
# This file serves as the entry point for Vercel's Python runtime
