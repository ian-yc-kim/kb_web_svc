"""API routes for the kb_web_svc application.

This package contains all FastAPI route definitions organized by domain.
"""

from .task_routes import task_router

__all__ = ["task_router"]
