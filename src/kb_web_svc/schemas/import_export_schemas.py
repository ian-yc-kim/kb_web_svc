"""Pydantic schemas for task import/export operations.

This module defines schemas for validating JSON task data during import and export
operations, ensuring data integrity and type safety for task payloads.
"""

from datetime import date, datetime, timezone
from typing import Optional, List, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..models.task import Priority, Status


class TaskImportData(BaseModel):
    """Schema for validating JSON task data during import operations.
    
    Provides comprehensive field validation including UUID parsing, timezone-aware
    datetime handling, enum validation, and proper string normalization.
    """
    id: Optional[UUID] = Field(None, description="Task UUID (generated if None for new tasks)")
    title: str = Field(..., description="Task title (required)")
    assignee: Optional[str] = Field(None, description="Person assigned to the task")
    due_date: Optional[date] = Field(None, description="Task due date")
    description: Optional[str] = Field(None, description="Detailed task description")
    priority: Optional[str] = Field(None, description="Task priority level")
    labels: Optional[List[str]] = Field(None, description="List of task labels")
    estimated_time: Optional[float] = Field(None, ge=0.5, le=8.0, description="Estimated time in hours (0.5–8.0)")
    status: str = Field(..., description="Task status (required)")
    created_at: Optional[datetime] = Field(None, description="Task creation timestamp (ISO format string)")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp (ISO format string)")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp (ISO format string)")
    
    @field_validator('title', mode='before')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate that title is non-empty after stripping whitespace."""
        if not isinstance(v, str):
            raise ValueError("Title must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is non-empty after stripping and is valid enum value."""
        if not isinstance(v, str):
            raise ValueError("Status must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Status cannot be empty")
        
        # Validate against Status enum
        valid_statuses = [status.value for status in Status]
        if stripped not in valid_statuses:
            raise ValueError(f"Invalid status '{stripped}'. Must be one of: {valid_statuses}")
        return stripped
    
    @field_validator('assignee', mode='before')
    @classmethod
    def validate_assignee(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize assignee field - strip whitespace, convert empty to None."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Assignee must be a string")
        stripped = v.strip()
        return stripped if stripped else None
    
    @field_validator('description', mode='before')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description field - strip whitespace, convert empty to None."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Description must be a string")
        stripped = v.strip()
        return stripped if stripped else None
    
    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        """Validate priority is a valid enum value if provided, strip whitespace, convert empty to None."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Priority must be a string")
        stripped = v.strip()
        if not stripped:
            return None
        
        # Validate against Priority enum
        valid_priorities = [priority.value for priority in Priority]
        if stripped not in valid_priorities:
            raise ValueError(f"Invalid priority '{stripped}'. Must be one of: {valid_priorities}")
        return stripped
    
    @field_validator('labels', mode='before')
    @classmethod
    def validate_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Clean labels list - strip whitespace from entries, remove empty strings, return None if empty."""
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("Labels must be a list of strings")
        
        # Strip whitespace from each label and filter out empty ones
        cleaned_labels = []
        for label in v:
            if not isinstance(label, str):
                raise ValueError("All labels must be strings")
            stripped = label.strip()
            if stripped:
                cleaned_labels.append(stripped)
        
        return cleaned_labels if cleaned_labels else None
    
    @field_validator('created_at', 'last_modified', 'deleted_at', mode='before')
    @classmethod
    def validate_datetime_fields(cls, v: Union[str, datetime, None]) -> Optional[datetime]:
        """Ensure datetime fields are timezone-aware, parsing ISO strings and converting naive datetimes to UTC."""
        if v is None:
            return None
        
        # If string, parse as ISO datetime
        if isinstance(v, str):
            try:
                parsed_dt = datetime.fromisoformat(v.replace('Z', '+00:00'))  # Handle Z suffix
                # If naive after parsing, assume UTC
                if parsed_dt.tzinfo is None:
                    return parsed_dt.replace(tzinfo=timezone.utc)
                return parsed_dt
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {e}")
        
        # If datetime object
        if isinstance(v, datetime):
            # If naive datetime (no timezone info), convert to UTC
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            # If already timezone-aware, keep as is
            return v
        
        raise ValueError("Datetime fields must be datetime objects or ISO format strings")


class TaskImportResult(BaseModel):
    """Schema for tracking individual task import operation results.
    
    Provides status information for each task processed during import operations.
    """
    task_id: UUID = Field(..., description="UUID of the task that was processed")
    status: str = Field(..., description="Import status (e.g., 'imported', 'updated', 'skipped', 'failed')")
    message: str = Field(..., description="Descriptive message about the import result")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "imported",
                "message": "Task successfully imported"
            }
        }
    }
