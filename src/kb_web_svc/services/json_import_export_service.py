"""JSON Import/Export service for task management.

This module provides core logic for importing and exporting tasks to/from JSON format,
including conflict resolution, duplicate detection, and atomic transaction handling.
"""

import json
import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..models.task import Task, Priority, Status
from ..schemas.import_export_schemas import TaskImportData

logger = logging.getLogger(__name__)


def export_all_tasks_to_json(db: Session) -> str:
    """Export all active tasks to a JSON string.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        JSON string containing all active tasks serialized as TaskImportData objects
        
    Raises:
        Exception: Re-raises any database or serialization errors after logging
    """
    logger.info("Starting export of all active tasks to JSON")
    
    try:
        # Query all active tasks (where deleted_at is None)
        stmt = select(Task).where(Task.deleted_at.is_(None))
        result = db.execute(stmt)
        tasks = result.scalars().all()
        
        logger.info(f"Found {len(tasks)} active tasks to export")
        
        # Convert each Task ORM object to TaskImportData
        task_import_data_list = []
        for task in tasks:
            task_dict = task.to_dict()
            task_import_data = TaskImportData.model_validate(task_dict)
            task_import_data_list.append(task_import_data)
        
        # Serialize to JSON string using Pydantic's model_dump with json mode
        serializable_data = [task_data.model_dump(mode="json") for task_data in task_import_data_list]
        json_string = json.dumps(serializable_data, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully exported {len(task_import_data_list)} tasks to JSON")
        return json_string
        
    except Exception as e:
        logger.error(f"Error exporting tasks to JSON: {e}", exc_info=True)
        raise


def restore_database_from_json_backup(db: Session, json_backup_data: str) -> None:
    """Restore database from JSON backup data, performing full overwrite.
    
    Args:
        db: SQLAlchemy database session
        json_backup_data: JSON string containing task backup data
        
    Raises:
        ValueError: When JSON data is invalid or doesn't match TaskImportData schema
        Exception: Re-raises any database errors after logging and rollback
    """
    logger.info("Starting database restoration from JSON backup")
    
    try:
        # Start explicit transaction
        with db.begin():
            # Hard-delete all active tasks to ensure clean slate
            delete_stmt = delete(Task).where(Task.deleted_at.is_(None))
            result = db.execute(delete_stmt)
            deleted_count = result.rowcount
            logger.info(f"Hard-deleted {deleted_count} existing active tasks")
            
            # Parse JSON data
            try:
                json_data = json.loads(json_backup_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")
            
            if not isinstance(json_data, list):
                raise ValueError("JSON data must be a list of task objects")
            
            # Validate and create TaskImportData objects
            task_import_data_list = []
            for i, task_data in enumerate(json_data):
                try:
                    task_import_data = TaskImportData.model_validate(task_data)
                    task_import_data_list.append(task_import_data)
                except ValidationError as e:
                    raise ValueError(f"Validation error in task at index {i}: {e}")
            
            logger.info(f"Successfully parsed and validated {len(task_import_data_list)} tasks from JSON")
            
            # Create new Task ORM instances preserving IDs and timestamps
            created_tasks = []
            for task_data in task_import_data_list:
                task_orm = _create_task_orm_from_import_data(task_data)
                db.add(task_orm)
                created_tasks.append(task_orm)
            
            # Commit happens automatically when with block exits successfully
            logger.info(f"Successfully restored {len(created_tasks)} tasks from JSON backup")
            
    except Exception as e:
        logger.error(f"Error restoring database from JSON backup: {e}", exc_info=True)
        # Transaction will be rolled back automatically by context manager
        raise


def import_tasks_logic(db: Session, tasks_data: List[TaskImportData], conflict_strategy: str) -> Dict[str, Any]:
    """Import tasks with conflict resolution strategy.
    
    Args:
        db: SQLAlchemy database session
        tasks_data: List of TaskImportData objects to import
        conflict_strategy: One of 'skip', 'replace', 'merge_with_timestamp'
        
    Returns:
        Dictionary with import summary: {imported, updated, skipped, failed}
        
    Raises:
        ValueError: When conflict_strategy is invalid
        Exception: Re-raises any critical database errors after logging and rollback
    """
    logger.info(f"Starting import of {len(tasks_data)} tasks with conflict_strategy='{conflict_strategy}'")
    
    # Validate conflict_strategy
    valid_strategies = {"skip", "replace", "merge_with_timestamp"}
    if conflict_strategy not in valid_strategies:
        raise ValueError(f"Invalid conflict_strategy '{conflict_strategy}'. Must be one of: {list(valid_strategies)}")
    
    # Initialize counters
    imported = 0
    updated = 0
    skipped = 0
    failed = 0
    had_error = False
    
    try:
        # Pre-fetch all existing active tasks for efficient duplicate detection
        stmt = select(Task).where(Task.deleted_at.is_(None))
        result = db.execute(stmt)
        existing_tasks = result.scalars().all()
        
        # Build lookup dictionary for O(1) duplicate detection
        # Key: (normalized_title_lower, created_at_date_UTC)
        existing_lookup = {}
        for task in existing_tasks:
            if task.created_at is not None:
                # Convert created_at to UTC and extract date
                created_at_utc = _ensure_utc_datetime(task.created_at)
                date_key = created_at_utc.date()
                lookup_key = (task.title.lower().strip(), date_key)
                existing_lookup[lookup_key] = task
        
        logger.info(f"Built lookup table with {len(existing_lookup)} existing tasks")
        
        # Check if session already has an active transaction
        if db.in_transaction():
            # Session already in transaction, work within existing transaction
            transaction_context = None
        else:
            # Start new transaction
            transaction_context = db.begin()
        
        try:
            if transaction_context is not None:
                transaction_context.__enter__()
            
            # Process each incoming task
            for i, incoming_task_data in enumerate(tasks_data):
                try:
                    # Compute duplicate detection key
                    duplicate_key = None
                    existing_task = None
                    
                    if incoming_task_data.created_at is not None:
                        incoming_created_at_utc = _ensure_utc_datetime(incoming_task_data.created_at)
                        date_key = incoming_created_at_utc.date()
                        duplicate_key = (incoming_task_data.title.lower().strip(), date_key)
                        existing_task = existing_lookup.get(duplicate_key)
                    
                    # Apply conflict resolution strategy
                    if existing_task is not None:
                        # Duplicate found
                        if conflict_strategy == "skip":
                            skipped += 1
                            logger.debug(f"Skipped duplicate task: {incoming_task_data.title}")
                        
                        elif conflict_strategy == "replace":
                            # Hard-delete existing task
                            db.delete(existing_task)
                            # Create new task with incoming data
                            new_task = _create_task_orm_from_import_data(incoming_task_data)
                            db.add(new_task)
                            updated += 1
                            # Update lookup for this key
                            if duplicate_key is not None:
                                existing_lookup[duplicate_key] = new_task
                            logger.debug(f"Replaced task: {incoming_task_data.title}")
                        
                        elif conflict_strategy == "merge_with_timestamp":
                            # Compare timestamps
                            existing_last_modified_utc = _ensure_utc_datetime(existing_task.last_modified)
                            incoming_last_modified_utc = _ensure_utc_datetime(incoming_task_data.last_modified or datetime.min.replace(tzinfo=timezone.utc))
                            
                            if incoming_last_modified_utc > existing_last_modified_utc:
                                # Incoming is newer, update existing task
                                _update_task_orm_from_import_data(existing_task, incoming_task_data)
                                updated += 1
                                logger.debug(f"Updated task with newer data: {incoming_task_data.title}")
                            else:
                                # Existing is newer or same, skip
                                skipped += 1
                                logger.debug(f"Skipped task with older/same timestamp: {incoming_task_data.title}")
                    
                    else:
                        # No duplicate, create new task
                        new_task = _create_task_orm_from_import_data(incoming_task_data)
                        db.add(new_task)
                        imported += 1
                        # Update lookup if key is present
                        if duplicate_key is not None:
                            existing_lookup[duplicate_key] = new_task
                        logger.debug(f"Imported new task: {incoming_task_data.title}")
                
                except Exception as task_error:
                    # Log individual task processing error and continue
                    logger.error(f"Error processing task at index {i}: {task_error}", exc_info=True)
                    failed += 1
                    had_error = True
                    continue
            
            # If any individual task errors occurred, rollback entire transaction
            if had_error:
                logger.warning(f"Rolling back transaction due to {failed} task processing errors")
                if transaction_context is not None:
                    transaction_context.__exit__(Exception, None, None)
                else:
                    db.rollback()
                raise Exception(f"Import failed with {failed} task processing errors")
            
            # Commit transaction
            if transaction_context is not None:
                transaction_context.__exit__(None, None, None)
            else:
                db.commit()
            
            logger.info(f"Import completed successfully: imported={imported}, updated={updated}, skipped={skipped}, failed={failed}")
            
        except Exception as e:
            # Handle transaction rollback
            if transaction_context is not None:
                try:
                    transaction_context.__exit__(type(e), e, e.__traceback__)
                except:
                    pass
            else:
                db.rollback()
            raise
    
    except Exception as e:
        logger.error(f"Critical error during import: {e}", exc_info=True)
        raise
    
    # Return summary
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "failed": failed
    }


def _create_task_orm_from_import_data(task_data: TaskImportData) -> Task:
    """Create a new Task ORM instance from TaskImportData, preserving imported timestamps and ID.
    
    Args:
        task_data: TaskImportData containing all task fields
        
    Returns:
        Task ORM instance ready for database persistence
        
    Raises:
        ValueError: When required enum values are invalid
    """
    # Convert enums
    status = Status(task_data.status)
    priority = Priority(task_data.priority) if task_data.priority else None
    
    # Handle labels - normalize empty list to None
    labels = task_data.labels if task_data.labels else None
    
    # Build kwargs dict
    task_kwargs = {
        "title": task_data.title,
        "assignee": task_data.assignee,
        "due_date": task_data.due_date,
        "description": task_data.description,
        "priority": priority,
        "labels": labels,
        "estimated_time": task_data.estimated_time,
        "status": status,
        "deleted_at": task_data.deleted_at
    }
    
    # Include ID and timestamps if provided
    if task_data.id is not None:
        task_kwargs["id"] = task_data.id
    if task_data.created_at is not None:
        task_kwargs["created_at"] = task_data.created_at
    if task_data.last_modified is not None:
        task_kwargs["last_modified"] = task_data.last_modified
    
    return Task(**task_kwargs)


def _update_task_orm_from_import_data(existing_task: Task, task_data: TaskImportData) -> None:
    """Update an existing Task ORM instance with data from TaskImportData.
    
    Args:
        existing_task: Existing Task ORM instance to update
        task_data: TaskImportData containing updated field values
        
    Raises:
        ValueError: When required enum values are invalid
    """
    # Update all fields except id (preserve existing id)
    existing_task.title = task_data.title
    existing_task.assignee = task_data.assignee
    existing_task.due_date = task_data.due_date
    existing_task.description = task_data.description
    
    # Convert and set enums
    existing_task.status = Status(task_data.status)
    existing_task.priority = Priority(task_data.priority) if task_data.priority else None
    
    # Handle labels - normalize empty list to None
    existing_task.labels = task_data.labels if task_data.labels else None
    existing_task.estimated_time = task_data.estimated_time
    existing_task.deleted_at = task_data.deleted_at
    
    # Note: Don't manually set last_modified - let SQLAlchemy event listener handle it
    # unless we want to preserve the imported last_modified timestamp
    if task_data.last_modified is not None:
        existing_task.last_modified = task_data.last_modified


def _ensure_utc_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC.
    
    Args:
        dt: DateTime object that may be naive or timezone-aware
        
    Returns:
        UTC timezone-aware datetime
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC (common with SQLite)
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)