"""Task SQLAlchemy ORM model with Priority and Status enums.

This module defines the Task model with all required fields, validation constraints,
automatic timestamps, indexing, and serialization methods.
"""

import uuid
from datetime import datetime, timezone, date
from enum import Enum
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, String, Text, Float, Date, DateTime, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, String as SQLString

from .base import Base


class Priority(Enum):
    """Task priority levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Status(Enum):
    """Task status values."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class PriorityEnumType(TypeDecorator):
    """Custom SQLAlchemy TypeDecorator for Priority enum."""
    
    impl = SQLString
    cache_ok = True
    
    def process_bind_param(self, value: Optional[Priority], dialect) -> Optional[str]:
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
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[Priority]:
        """Convert string from database to Priority enum."""
        if value is None:
            return None
        try:
            return Priority(value)
        except ValueError:
            raise ValueError(f"Invalid Priority value from database: {value}")


class StatusEnumType(TypeDecorator):
    """Custom SQLAlchemy TypeDecorator for Status enum."""
    
    impl = SQLString
    cache_ok = True
    
    def process_bind_param(self, value: Optional[Status], dialect) -> Optional[str]:
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
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[Status]:
        """Convert string from database to Status enum."""
        if value is None:
            return None
        try:
            return Status(value)
        except ValueError:
            raise ValueError(f"Invalid Status value from database: {value}")


class Task(Base):
    """Task ORM model with all required fields and functionality."""
    
    __tablename__ = 'tasks'
    
    # Primary key with UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    
    # Core task fields
    title = Column(String, nullable=False)
    assignee = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    # Enum fields with custom TypeDecorators
    priority = Column(PriorityEnumType, nullable=True)
    status = Column(StatusEnumType, nullable=False)
    
    # JSON field for labels (list of strings)
    labels = Column(JSON, nullable=True)
    
    # Numeric field for estimated time
    estimated_time = Column(Float, nullable=True)
    
    # Automatic timestamp fields with timezone
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_modified = Column(DateTime(timezone=True), 
                          default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), 
                          nullable=False)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_priority', 'priority'),
        Index('idx_task_due_date', 'due_date'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Task model instance to dictionary for serialization.
        
        Returns:
            Dictionary representation of the Task with proper type conversion.
        """
        result = {
            'id': str(self.id),  # Convert UUID to string
            'title': self.title,
            'assignee': self.assignee,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'description': self.description,
            'priority': self.priority.value if self.priority else None,  # Convert enum to string
            'status': self.status.value,  # Convert enum to string
            'labels': self.labels if self.labels else [],  # Ensure labels is a list
            'estimated_time': self.estimated_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
        }
        return result
    
    def __repr__(self) -> str:
        """String representation of Task model."""
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status.value if self.status else None}')>"
