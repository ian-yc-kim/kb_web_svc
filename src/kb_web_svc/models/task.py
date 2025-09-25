"""Task SQLAlchemy ORM model for the kb_web_svc application.

This module defines the Task model with Priority and Status enums,
custom TypeDecorators for enum validation, and all required fields.
"""

import uuid
from datetime import datetime, timezone, date
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Text, Float, Date, DateTime, Index, JSON, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, String as SQLString

from .base import Base


class Priority(Enum):
    """Enum for task priority levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Status(Enum):
    """Enum for task status values."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class PriorityEnumType(TypeDecorator):
    """Custom SQLAlchemy TypeDecorator for Priority enum validation."""
    impl = SQLString
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Priority enum to string for database storage."""
        if value is None:
            return None
        if isinstance(value, Priority):
            return value.value
        if isinstance(value, str):
            # Validate that the string is a valid Priority value
            try:
                Priority(value)
                return value
            except ValueError:
                raise ValueError(f"Invalid Priority value: {value}. Must be one of {[p.value for p in Priority]}")
        raise ValueError(f"Invalid Priority type: {type(value)}. Must be Priority enum or string.")

    def process_result_value(self, value, dialect):
        """Convert string from database to Priority enum."""
        if value is None:
            return None
        try:
            return Priority(value)
        except ValueError:
            raise ValueError(f"Invalid priority value in database: {value}")


class StatusEnumType(TypeDecorator):
    """Custom SQLAlchemy TypeDecorator for Status enum validation."""
    impl = SQLString
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Status enum to string for database storage."""
        if value is None:
            return None
        if isinstance(value, Status):
            return value.value
        if isinstance(value, str):
            # Validate that the string is a valid Status value
            try:
                Status(value)
                return value
            except ValueError:
                raise ValueError(f"Invalid Status value: {value}. Must be one of {[s.value for s in Status]}")
        raise ValueError(f"Invalid Status type: {type(value)}. Must be Status enum or string.")

    def process_result_value(self, value, dialect):
        """Convert string from database to Status enum."""
        if value is None:
            return None
        try:
            return Status(value)
        except ValueError:
            raise ValueError(f"Invalid status value in database: {value}")


class Task(Base):
    """Task ORM model for kanban task management.
    
    Represents a task with comprehensive metadata including priority,
    status, assignee, due date, and automatic timestamp management.
    """
    __tablename__ = 'tasks'
    
    # Define indexes
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_priority', 'priority'),
        Index('idx_task_due_date', 'due_date'),
    )
    
    # Fields definition
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    title = Column(String, nullable=False)
    assignee = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    priority = Column(PriorityEnumType, nullable=True)
    labels = Column(JSON, nullable=True)
    estimated_time = Column(Float, nullable=True)
    status = Column(StatusEnumType, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_modified = Column(DateTime(timezone=True), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    
    def __init__(self, **kwargs):
        """Initialize Task with synchronized timestamps."""
        # Get current timestamp once for both created_at and last_modified
        now = datetime.now(timezone.utc)
        
        # Set timestamps if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'last_modified' not in kwargs:
            kwargs['last_modified'] = now
        # Note: deleted_at is left to default behavior (None)
            
        super().__init__(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Task model instance to a dictionary for serialization.
        
        Returns:
            Dict containing all task fields with proper type conversion:
            - Enum values converted to string values
            - UUID converted to string
            - DateTime objects converted to ISO format strings
            - Date objects converted to ISO format strings
            - Labels JSON field returned as Python list
        """
        return {
            'id': str(self.id),
            'title': self.title,
            'assignee': self.assignee,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'description': self.description,
            'priority': self.priority.value if self.priority else None,
            'labels': self.labels if self.labels else [],
            'estimated_time': self.estimated_time,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    def __repr__(self):
        """String representation of the Task object."""
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status.value if self.status else None}')>"


# Set up event listener to update last_modified on updates
@event.listens_for(Task, 'before_update')
def update_last_modified(mapper, connection, target):
    """Update last_modified timestamp before updating a Task record."""
    target.last_modified = datetime.now(timezone.utc)