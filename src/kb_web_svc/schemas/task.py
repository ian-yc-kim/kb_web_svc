"""Pydantic schemas for task-related operations.

This module defines the input and output schemas for task operations,
including validation and serialization models.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    """Input schema for creating a new task.
    
    This model validates and sanitizes input data for task creation,
    ensuring all required fields are present and optional fields
    meet the specified constraints.
    """
    title: str = Field(..., description="Task title (required)")
    assignee: Optional[str] = Field(None, description="Person assigned to the task")
    due_date: Optional[date] = Field(None, description="Task due date")
    description: Optional[str] = Field(None, description="Detailed task description")
    priority: Optional[str] = Field(None, description="Task priority level")
    labels: Optional[List[str]] = Field(None, description="List of task labels")
    estimated_time: Optional[float] = Field(None, ge=0.0, description="Estimated time in hours")
    status: str = Field(..., description="Task status (required)")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate that title is non-empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        """Validate priority is a valid enum value if provided."""
        if v is None:
            return v
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            return None
        return stripped
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is non-empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Status cannot be empty")
        return v.strip()
    
    @field_validator('assignee')
    @classmethod
    def validate_assignee(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize assignee field."""
        if v is None:
            return v
        stripped = v.strip() if isinstance(v, str) else v
        return stripped if stripped else None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description field."""
        if v is None:
            return v
        stripped = v.strip() if isinstance(v, str) else v
        return stripped if stripped else None
    
    @field_validator('labels')
    @classmethod
    def validate_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate labels is a list of strings if provided."""
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("Labels must be a list of strings")
        # Strip whitespace from each label and filter out empty ones
        cleaned_labels = [label.strip() for label in v if isinstance(label, str) and label.strip()]
        return cleaned_labels if cleaned_labels else None


class TaskFilterParams(BaseModel):
    """Filter parameters for task queries with pagination and sorting.
    
    This model provides comprehensive filtering, pagination, and sorting
    capabilities for task retrieval operations.
    """
    status: Optional[str] = Field(None, description="Filter by task status")
    priority: Optional[str] = Field(None, description="Filter by task priority")
    assignee: Optional[str] = Field(None, description="Filter by assignee (case-insensitive partial match)")
    due_date_start: Optional[date] = Field(None, description="Filter tasks due on or after this date")
    due_date_end: Optional[date] = Field(None, description="Filter tasks due on or before this date")
    search_term: Optional[str] = Field(None, description="Search in task title and description (case-insensitive)")
    limit: int = Field(10, ge=1, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip for pagination")
    sort_by: str = Field("created_at", description="Field to sort by (created_at, due_date, priority)")
    sort_order: str = Field("desc", description="Sort order (asc, desc)")
    
    @field_validator('status', 'priority', 'assignee', 'search_term')
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from optional string fields, convert empty strings to None."""
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        return stripped if stripped else None


class TaskResponse(BaseModel):
    """Output schema for task responses.
    
    This model represents the serialized task data returned by the API,
    with proper type conversion for UUIDs, enums, and timestamps.
    """
    id: str = Field(..., description="Unique task identifier (UUID as string)")
    title: str = Field(..., description="Task title")
    assignee: Optional[str] = Field(None, description="Person assigned to the task")
    due_date: Optional[str] = Field(None, description="Task due date (ISO format string)")
    description: Optional[str] = Field(None, description="Detailed task description")
    priority: Optional[str] = Field(None, description="Task priority level")
    labels: List[str] = Field(default_factory=list, description="List of task labels")
    estimated_time: Optional[float] = Field(None, description="Estimated time in hours")
    status: str = Field(..., description="Task status")
    created_at: str = Field(..., description="Task creation timestamp (ISO format string)")
    last_modified: str = Field(..., description="Last modification timestamp (ISO format string)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Complete project documentation",
                "assignee": "John Doe",
                "due_date": "2024-12-31",
                "description": "Write comprehensive documentation for the project",
                "priority": "High",
                "labels": ["documentation", "high-priority"],
                "estimated_time": 8.5,
                "status": "In Progress",
                "created_at": "2024-01-15T10:30:00Z",
                "last_modified": "2024-01-15T10:30:00Z"
            }
        }
    }
