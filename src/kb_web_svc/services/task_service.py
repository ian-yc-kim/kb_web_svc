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
from ..schemas.task import TaskCreate, TaskFilterParams, TaskUpdate

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


class TaskNotFoundError(ValueError):
    """Exception raised when a task with the specified ID is not found."""
    pass


class OptimisticConcurrencyError(ValueError):
    """Exception raised when optimistic concurrency control detects a conflict."""
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


def update_task(task_id: UUID, payload: TaskUpdate, db: Session) -> Dict[str, Any]:
    """Update an existing task with partial field changes, ensuring atomic operations and optimistic concurrency control.
    
    This function performs field-specific updates on a task, validating all input data
    and ensuring data consistency through database transactions. The expected_last_modified
    timestamp in the payload supports optimistic concurrency control by comparing against
    the task's current last_modified value (both converted to UTC for accurate comparison).
    The last_modified field is automatically updated via SQLAlchemy event listeners.
    
    @param task_id (UUID): The unique identifier of the task to be updated
    @param payload (TaskUpdate): Pydantic model containing optional fields for partial 
                                 updates and the expected_last_modified timestamp for 
                                 optimistic concurrency control
    @param db (Session): SQLAlchemy database session for executing database operations
    @returns (Dict[str, Any]): Dictionary representation of the updated task with all 
                               field values properly serialized (enums as strings, 
                               UUIDs as strings, timestamps as ISO format strings)
    @raises TaskNotFoundError: When no task with the specified task_id is not found
    @raises OptimisticConcurrencyError: When the expected_last_modified timestamp does 
                                        not match the current task's last_modified, 
                                        indicating concurrency conflict by another user
    @raises InvalidStatusError: When the provided status value is invalid and not a valid Status 
                                enum value (must be 'To Do', 'In Progress', or 'Done')
    @raises InvalidPriorityError: When the provided priority value is invalid and not a valid 
                                  Priority enum value (must be 'Critical', 'High', 
                                  'Medium', or 'Low')
    @raises PastDueDateError: When the provided due_date is in the past relative to 
                              the current UTC date
    @raises ValueError: When estimated_time is negative, title is empty after 
                        trimming whitespace, or other validation constraints are violated
    """
    logger.info(f"Updating task with ID: {task_id}")
    
    try:
        # Fetch the existing task
        task = db.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
        
        # Implement optimistic concurrency control
        if payload.expected_last_modified is not None:
            # Convert payload timestamp to UTC for comparison
            expected_last_modified = payload.expected_last_modified.astimezone(timezone.utc)
            
            # Convert task timestamp to UTC for comparison (handle SQLite naive datetime)
            task_last_modified = task.last_modified
            if task_last_modified.tzinfo is None:
                # SQLite returns naive datetimes - assume they are UTC
                task_last_modified = task_last_modified.replace(tzinfo=timezone.utc)
            else:
                task_last_modified = task_last_modified.astimezone(timezone.utc)
            
            if expected_last_modified != task_last_modified:
                raise OptimisticConcurrencyError(
                    f"Task with ID {task_id} has been modified by another user. Please refresh and try again."
                )
        
        # Get fields that were explicitly provided (including those that became None after validation)
        all_update_data = payload.model_dump(exclude_unset=True)
        all_update_data.pop('expected_last_modified', None)
        
        # Process each field for update
        for field_name in all_update_data.keys():
            field_value = getattr(payload, field_name)
            
            if field_name == 'title':
                if field_value is not None:
                    title = field_value.strip()
                    if not title:
                        raise ValueError("Title cannot be empty")
                    task.title = title
            
            elif field_name == 'status':
                if field_value is not None:
                    try:
                        status = Status(field_value)
                        task.status = status
                    except ValueError:
                        valid_statuses = [s.value for s in Status]
                        raise InvalidStatusError(f"Invalid status '{field_value}'. Must be one of: {valid_statuses}")
            
            elif field_name == 'priority':
                if field_value is not None:
                    try:
                        priority = Priority(field_value)
                        task.priority = priority
                    except ValueError:
                        valid_priorities = [p.value for p in Priority]
                        raise InvalidPriorityError(f"Invalid priority '{field_value}'. Must be one of: {valid_priorities}")
            
            elif field_name == 'due_date':
                if field_value is not None:
                    current_date = datetime.now(timezone.utc).date()
                    if field_value < current_date:
                        raise PastDueDateError(f"Due date {field_value} cannot be in the past. Current date: {current_date}")
                    task.due_date = field_value
            
            elif field_name == 'estimated_time':
                if field_value is not None:
                    if field_value < 0.0:
                        raise ValueError(f"Estimated time must be non-negative, got: {field_value}")
                    task.estimated_time = field_value
            
            elif field_name == 'labels':
                # For labels, we update even if field_value is None (from Pydantic validation)
                # because None means "empty after cleanup" which is a valid update
                task.labels = field_value
            
            elif field_name == 'assignee':
                # For assignee, we update even if field_value is None (from Pydantic validation)
                # because None means "empty after cleanup" which is a valid update
                task.assignee = field_value
            
            elif field_name == 'description':
                # For description, we update even if field_value is None (from Pydantic validation)
                # because None means "empty after cleanup" which is a valid update
                task.description = field_value
        
        # Persist changes to database
        db.add(task)
        db.commit()  # The before_update event will automatically update last_modified
        db.refresh(task)
        
        logger.info(f"Successfully updated task with ID: {task.id}")
        return task.to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(e, exc_info=True)
        raise


def delete_task(task_id: UUID, db: Session, soft: bool = True) -> Dict[str, Any]:
    """Delete a task with support for both soft and hard deletion.
    
    Args:
        task_id: UUID of the task to delete
        db: SQLAlchemy database session
        soft: Boolean flag for soft delete (default True). If True, sets deleted_at timestamp.
              If False, permanently removes the task from database.
        
    Returns:
        Dictionary containing deletion success message and task ID
        
    Raises:
        TaskNotFoundError: When no task with the specified task_id is found
        Exception: Re-raises any database errors after logging and rollback
    """
    logger.info(f"Deleting task with ID: {task_id}, soft delete: {soft}")
    
    try:
        # Fetch the existing task
        task = db.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
        
        if soft:
            # Soft delete: Set deleted_at timestamp
            task.deleted_at = datetime.now(timezone.utc)
            db.add(task)
            # Note: last_modified will be automatically updated by the before_update event listener
            message = "Task soft-deleted successfully"
        else:
            # Hard delete: Permanently remove from database
            db.delete(task)
            message = "Task hard-deleted successfully"
        
        # Commit the changes
        db.commit()
        
        logger.info(f"Successfully deleted task with ID: {task_id} (soft: {soft})")
        
        return {
            "message": message,
            "task_id": str(task_id)
        }
        
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