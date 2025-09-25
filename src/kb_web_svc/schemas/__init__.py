"""Pydantic schemas for the kb_web_svc application.

This package contains all Pydantic models for request/response validation
and serialization.
"""

from .task import TaskCreate, TaskResponse, TaskUpdate

__all__ = ["TaskCreate", "TaskResponse", "TaskUpdate"]
