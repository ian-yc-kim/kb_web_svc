"""Task service layer for business logic and data persistence.

This module implements the task creation service with comprehensive
input validation, data sanitization, and database persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, case, or_
from sqlalchemy.orm import Session

from ..models.task import Task, Priority, Status
from ..schemas.task import TaskCreate, TaskFilterParams

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


def get_task_by_id(db: Session, task_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieve a task by its UUID.
    
    Args:
        db: SQLAlchemy database session
        task_id: UUID of the task to retrieve
        
    Returns:
        Dictionary representation of the task if found, None otherwise
        
    Raises:
        Exception: Re-raises any database errors after logging
    """
    logger.info(f"Retrieving task with ID: {task_id}")
    
    try:
        task = db.get(Task, task_id)
        
        if task is None:
            logger.info(f"Task with ID {task_id} not found")
            return None
        
        logger.info(f"Successfully retrieved task with ID: {task_id}")
        return task.to_dict()
        
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def list_tasks(db: Session, filters: TaskFilterParams) -> Tuple[List[Dict[str, Any]], int]:
    """List tasks with filtering, sorting, and pagination.
    
    Args:
        db: SQLAlchemy database session
        filters: TaskFilterParams containing filter, sort, and pagination options
        
    Returns:
        Tuple of (list of task dictionaries, total count before pagination)
        
    Raises:
        ValueError: When sort_by or sort_order parameters are invalid
        Exception: Re-raises any database errors after logging
    """
    logger.info(f"Listing tasks with filters: status={filters.status}, priority={filters.priority}, "
                f"assignee={filters.assignee}, search_term={filters.search_term}, "
                f"due_date_start={filters.due_date_start}, due_date_end={filters.due_date_end}, "
                f"sort_by={filters.sort_by}, sort_order={filters.sort_order}, "
                f"limit={filters.limit}, offset={filters.offset}")
    
    # Validate sort_by and sort_order parameters
    allowed_sort_by = {"created_at", "due_date", "priority"}
    allowed_sort_order = {"asc", "desc"}
    
    if filters.sort_by not in allowed_sort_by:
        raise ValueError(f"Invalid sort_by '{filters.sort_by}'. Must be one of: {list(allowed_sort_by)}")
    
    if filters.sort_order not in allowed_sort_order:
        raise ValueError(f"Invalid sort_order '{filters.sort_order}'. Must be one of: {list(allowed_sort_order)}")
    
    try:
        # Build base statement
        stmt = select(Task)
        
        # Apply filters
        conditions = []
        
        if filters.status is not None:
            conditions.append(Task.status == filters.status)
        
        if filters.priority is not None:
            conditions.append(Task.priority == filters.priority)
        
        if filters.assignee is not None:
            conditions.append(Task.assignee.ilike(f"%{filters.assignee}%"))
        
        if filters.due_date_start is not None:
            conditions.append(Task.due_date >= filters.due_date_start)
        
        if filters.due_date_end is not None:
            conditions.append(Task.due_date <= filters.due_date_end)
        
        if filters.search_term is not None:
            search_pattern = f"%{filters.search_term}%"
            conditions.append(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern)
                )
            )
        
        # Apply all conditions
        if conditions:
            stmt = stmt.where(*conditions)
        
        # Get total count before pagination
        count_stmt = select(func.count(Task.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        total_count = db.execute(count_stmt).scalar()
        
        # Apply sorting
        if filters.sort_by == "created_at":
            sort_column = Task.created_at
        elif filters.sort_by == "due_date":
            sort_column = Task.due_date
        elif filters.sort_by == "priority":
            # Use CASE statement for logical priority order (Critical > High > Medium > Low)
            sort_column = case(
                (Task.priority == "Critical", 4),
                (Task.priority == "High", 3),
                (Task.priority == "Medium", 2),
                (Task.priority == "Low", 1),
                else_=0
            )
        
        if filters.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        stmt = stmt.limit(filters.limit).offset(filters.offset)
        
        # Execute query
        result = db.execute(stmt)
        tasks = result.scalars().all()
        
        # Serialize tasks
        task_dicts = [task.to_dict() for task in tasks]
        
        logger.info(f"Successfully retrieved {len(task_dicts)} tasks out of {total_count} total")
        
        return task_dicts, total_count
        
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
