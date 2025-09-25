"""Task service layer for business logic and data persistence.

This module implements the task creation service with comprehensive
input validation, data sanitization, and database persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session

from ..models.task import Task, Priority, Status
from ..schemas.task import TaskCreate

logger = logging.getLogger(__name__)


class InvalidStatusError(ValueError):
    """Exception raised when an invalid task status is provided."""
    pass


class InvalidPriorityError(ValueError):
    """Exception raised when an invalid task priority is provided."""
    pass


class PastDueDateError(ValueError):
    """Exception raised when due date is in the past."""
    pass


def create_task(payload: TaskCreate, db: Session) -> Dict[str, Any]:
    """Create a new task with validation and database persistence.
    
    Args:
        payload: TaskCreate Pydantic model with validated input data
        db: SQLAlchemy database session
        
    Returns:
        Dictionary representation of the created task
        
    Raises:
        InvalidStatusError: When status is not a valid Status enum value
        InvalidPriorityError: When priority is not a valid Priority enum value
        PastDueDateError: When due_date is in the past
        ValueError: When estimated_time is negative or other validation errors
    """
    logger.info(f"Creating task with title: {payload.title}")
    
    # Validate title (already validated by Pydantic, but double-check)
    title = payload.title.strip()
    if not title:
        raise ValueError("Title cannot be empty")
    
    # Validate and convert status to enum
    try:
        status = Status(payload.status)
    except ValueError:
        valid_statuses = [s.value for s in Status]
        raise InvalidStatusError(f"Invalid status '{payload.status}'. Must be one of: {valid_statuses}")
    
    # Validate and convert priority to enum if provided
    priority = None
    if payload.priority is not None and payload.priority.strip():
        try:
            priority = Priority(payload.priority)
        except ValueError:
            valid_priorities = [p.value for p in Priority]
            raise InvalidPriorityError(f"Invalid priority '{payload.priority}'. Must be one of: {valid_priorities}")
    
    # Validate due_date is not in the past if provided
    due_date = payload.due_date
    if due_date is not None:
        current_date = datetime.now(timezone.utc).date()
        if due_date < current_date:
            raise PastDueDateError(f"Due date {due_date} cannot be in the past. Current date: {current_date}")
    
    # Validate estimated_time is non-negative if provided
    estimated_time = payload.estimated_time
    if estimated_time is not None and estimated_time < 0.0:
        raise ValueError(f"Estimated time must be non-negative, got: {estimated_time}")
    
    # Process labels - convert None to None (to_dict will handle as [])
    labels = payload.labels
    if labels is not None and len(labels) == 0:
        labels = None
    
    # Create Task ORM instance
    task = Task(
        title=title,
        assignee=payload.assignee,
        due_date=due_date,
        description=payload.description,
        priority=priority,
        labels=labels,
        estimated_time=estimated_time,
        status=status
    )
    
    # Persist to database with proper transaction handling
    try:
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Successfully created task with ID: {task.id}")
        
        # Return serialized dictionary
        return task.to_dict()
        
    except Exception as e:
        logger.error(e, exc_info=True)
        db.rollback()
        raise
