"""FastAPI application for the kb_web_svc API.

This module creates and configures the FastAPI application instance
with all necessary routes and middleware.
"""

from fastapi import FastAPI

from ..routes.task_routes import task_router

# Create FastAPI application instance
app = FastAPI(
    title="KB Web Service API",
    description="REST API for kanban task management operations",
    version="1.0.0"
)

# Include routers with API prefix
app.include_router(task_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
