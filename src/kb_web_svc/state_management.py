"""State management module for Streamlit session state initialization and task loading.

This module provides functions to initialize and manage the Streamlit session state
with core data structures for the kanban task management application.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

import streamlit as st
from sqlalchemy.orm import Session

from .database import get_db
from .models.task import Status
from .schemas.task import TaskFilterParams
from .services.task_service import list_tasks

logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """Initialize Streamlit session state with core data structures.
    
    This function checks if the session state has already been initialized and
    sets up the basic structure with tasks_by_status, form_states, and ui_states.
    If not already populated, it loads existing tasks from the database.
    
    The function is idempotent - subsequent calls will not re-initialize if
    already done.
    """
    logger.info("Initializing Streamlit session state")
    
    # Check if already initialized
    if st.session_state.get("initialized", False):
        logger.info("Session state already initialized, skipping")
        return
    
    try:
        # Set initialization flag
        st.session_state.initialized = True
        
        # Initialize form_states and ui_states (always empty on init)
        st.session_state.form_states = {}
        st.session_state.ui_states = {}
        
        # Check if tasks_by_status already exists and has content
        existing_tasks = getattr(st.session_state, 'tasks_by_status', None)
        has_existing_tasks = (existing_tasks is not None and 
                            isinstance(existing_tasks, dict) and
                            (bool(existing_tasks.get(Status.TODO.value)) or 
                             bool(existing_tasks.get(Status.IN_PROGRESS.value)) or 
                             bool(existing_tasks.get(Status.DONE.value))))
        
        if not has_existing_tasks:
            # Initialize tasks_by_status structure
            st.session_state.tasks_by_status = {
                Status.TODO.value: [],
                Status.IN_PROGRESS.value: [],
                Status.DONE.value: []
            }
            
            # Load tasks from database since we have empty task structure
            db_gen = None
            try:
                db_gen = get_db()
                db = next(db_gen)
                load_tasks_from_db_to_session(db)
                logger.info("Tasks loaded from database to session state")
            except Exception as e:
                logger.error(f"Failed to load tasks from database: {e}", exc_info=True)
                # Don't raise - initialization should continue even if task loading fails
            finally:
                # Ensure generator cleanup
                if db_gen is not None:
                    try:
                        next(db_gen)
                    except StopIteration:
                        pass  # Generator properly closed
                    except Exception as cleanup_error:
                        logger.error(f"Error during database cleanup: {cleanup_error}", exc_info=True)
        else:
            logger.info("Tasks already exist in session state, skipping database load")
        
        logger.info("Session state core structures initialized")
        logger.info("Session state initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error during session state initialization: {e}", exc_info=True)
        raise


def load_tasks_from_db_to_session(db: Session) -> None:
    """Load existing tasks from the database into session state.
    
    This function fetches all non-deleted tasks from the database and populates
    the session state tasks_by_status dictionary, categorizing tasks by their status.
    
    Args:
        db: SQLAlchemy database session for database operations
        
    Raises:
        Exception: Re-raises any database errors after logging
    """
    logger.info("Loading tasks from database to session state")
    
    try:
        # Clear existing tasks in session state
        st.session_state.tasks_by_status = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        
        # Fetch tasks from database with a large limit to get all tasks
        # Since current list_tasks doesn't support deleted_at filtering,
        # we fetch a large set and filter locally
        filters = TaskFilterParams(limit=10000, offset=0)
        task_dicts, total_count = list_tasks(db, filters)
        
        logger.info(f"Retrieved {len(task_dicts)} tasks from database")
        
        # Filter out deleted tasks and categorize by status
        active_tasks_count = 0
        for task_dict in task_dicts:
            # Skip deleted tasks (deleted_at is not None)
            if task_dict.get("deleted_at") is not None:
                continue
            
            # Get task status
            task_status = task_dict.get("status")
            
            # Add to appropriate status list
            if task_status == Status.TODO.value:
                st.session_state.tasks_by_status[Status.TODO.value].append(task_dict)
                active_tasks_count += 1
            elif task_status == Status.IN_PROGRESS.value:
                st.session_state.tasks_by_status[Status.IN_PROGRESS.value].append(task_dict)
                active_tasks_count += 1
            elif task_status == Status.DONE.value:
                st.session_state.tasks_by_status[Status.DONE.value].append(task_dict)
                active_tasks_count += 1
            else:
                logger.warning(f"Task {task_dict.get('id')} has unknown status: {task_status}")
        
        logger.info(f"Loaded {active_tasks_count} active tasks into session state by status")
        logger.info(f"Tasks by status: "
                   f"To Do: {len(st.session_state.tasks_by_status[Status.TODO.value])}, "
                   f"In Progress: {len(st.session_state.tasks_by_status[Status.IN_PROGRESS.value])}, "
                   f"Done: {len(st.session_state.tasks_by_status[Status.DONE.value])}")
        
    except Exception as e:
        logger.error(f"Error loading tasks from database: {e}", exc_info=True)
        # Clear session state on error to maintain consistency
        st.session_state.tasks_by_status = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        raise


def add_task_to_session(task_dict: Dict[str, Any]) -> None:
    """Add a task dictionary to the session state organized by status.
    
    Takes a task dictionary and adds it to the appropriate status list within
    st.session_state.tasks_by_status. If the status list does not exist, it will
    be initialized as an empty list.
    
    Args:
        task_dict: Dictionary containing task data with a 'status' field
        
    Note:
        If the task_dict does not contain a 'status' field, a warning will be
        logged and the task will not be added.
    """
    logger.info(f"Adding task to session state: {task_dict.get('id', 'unknown')}")
    
    try:
        # Ensure tasks_by_status structure exists
        if not hasattr(st.session_state, 'tasks_by_status') or not isinstance(st.session_state.tasks_by_status, dict):
            st.session_state.tasks_by_status = {}
        
        # Get task status
        status = task_dict.get('status')
        if status is None:
            logger.warning(f"Task dictionary missing 'status' field, cannot add to session state")
            return
        
        # Initialize status list if it doesn't exist
        if status not in st.session_state.tasks_by_status:
            st.session_state.tasks_by_status[status] = []
        
        # Add task to appropriate status list
        st.session_state.tasks_by_status[status].append(task_dict)
        
        logger.info(f"Successfully added task {task_dict.get('id', 'unknown')} to status '{status}'")
        
    except Exception as e:
        logger.error(f"Error adding task to session state: {e}", exc_info=True)
        raise


def update_task_in_session(task_dict: Dict[str, Any]) -> None:
    """Update an existing task in the session state.
    
    Takes an updated task dictionary (including its id) and finds the existing task
    in st.session_state.tasks_by_status. If found, removes the old task from its
    current status list and adds the updated task to the correct status list based
    on its (potentially new) status field.
    
    Args:
        task_dict: Dictionary containing updated task data with 'id' and 'status' fields
        
    Note:
        If the task_dict does not contain an 'id' field, a warning will be logged
        and no update will be performed. If no existing task with matching id is
        found, no action is taken (as per requirement).
    """
    logger.info(f"Updating task in session state: {task_dict.get('id', 'unknown')}")
    
    try:
        # Ensure tasks_by_status structure exists
        if not hasattr(st.session_state, 'tasks_by_status') or not isinstance(st.session_state.tasks_by_status, dict):
            st.session_state.tasks_by_status = {}
        
        # Get task id
        task_id = task_dict.get('id')
        if task_id is None:
            logger.warning(f"Task dictionary missing 'id' field, cannot update in session state")
            return
        
        # Convert task_id to string for comparison (handles UUID objects)
        task_id_str = str(task_id)
        
        # Find and remove existing task with matching id
        existing_task_found = False
        for status_key, task_list in st.session_state.tasks_by_status.items():
            for i, existing_task in enumerate(task_list):
                if str(existing_task.get('id', '')) == task_id_str:
                    # Remove the existing task
                    task_list.pop(i)
                    existing_task_found = True
                    logger.info(f"Removed existing task {task_id_str} from status '{status_key}'")
                    break
            if existing_task_found:
                break
        
        if existing_task_found:
            # Get new status
            new_status = task_dict.get('status')
            if new_status is None:
                logger.warning(f"Updated task dictionary missing 'status' field, cannot place in session state")
                return
            
            # Initialize new status list if it doesn't exist
            if new_status not in st.session_state.tasks_by_status:
                st.session_state.tasks_by_status[new_status] = []
            
            # Add updated task to new status list
            st.session_state.tasks_by_status[new_status].append(task_dict)
            
            logger.info(f"Successfully updated task {task_id_str} and moved to status '{new_status}'")
        else:
            logger.info(f"No existing task found with id {task_id_str}, no update performed")
        
    except Exception as e:
        logger.error(f"Error updating task in session state: {e}", exc_info=True)
        raise


def delete_task_from_session(task_id: UUID) -> None:
    """Delete a task from the session state by task ID.
    
    Takes a UUID for task_id and finds and removes the task with matching id
    from st.session_state.tasks_by_status across all status lists.
    
    Args:
        task_id: UUID of the task to delete
        
    Note:
        If no task with the specified id is found, no action is taken
        (no-op as per requirement).
    """
    logger.info(f"Deleting task from session state: {task_id}")
    
    try:
        # Ensure tasks_by_status structure exists
        if not hasattr(st.session_state, 'tasks_by_status') or not isinstance(st.session_state.tasks_by_status, dict):
            st.session_state.tasks_by_status = {}
            logger.info(f"No tasks in session state, nothing to delete for task {task_id}")
            return
        
        # Convert task_id to string for comparison
        task_id_str = str(task_id)
        
        # Find and remove task with matching id across all status lists
        task_found = False
        for status_key, task_list in st.session_state.tasks_by_status.items():
            for i, task in enumerate(task_list):
                if str(task.get('id', '')) == task_id_str:
                    # Remove the task
                    task_list.pop(i)
                    task_found = True
                    logger.info(f"Successfully deleted task {task_id_str} from status '{status_key}'")
                    return  # Exit after finding and removing the task
        
        if not task_found:
            logger.info(f"No task found with id {task_id_str}, nothing to delete")
        
    except Exception as e:
        logger.error(f"Error deleting task from session state: {e}", exc_info=True)
        raise


def get_tasks_by_status(status_value: str) -> List[Dict[str, Any]]:
    """Get tasks by status from the session state.
    
    Returns the list of task dictionaries for a given status_value from
    st.session_state.tasks_by_status.
    
    Args:
        status_value: Status string to retrieve tasks for
        
    Returns:
        List of task dictionaries for the specified status, or empty list if
        the status does not exist in session state
    """
    logger.info(f"Getting tasks by status: {status_value}")
    
    try:
        # Ensure tasks_by_status structure exists
        if not hasattr(st.session_state, 'tasks_by_status') or not isinstance(st.session_state.tasks_by_status, dict):
            logger.info(f"No tasks_by_status in session state, returning empty list for status '{status_value}'")
            return []
        
        # Get tasks for the specified status
        tasks = st.session_state.tasks_by_status.get(status_value, [])
        
        logger.info(f"Retrieved {len(tasks)} tasks for status '{status_value}'")
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks by status: {e}", exc_info=True)
        raise


def get_all_tasks_from_session() -> List[Dict[str, Any]]:
    """Get all tasks from the session state as a flattened list.
    
    Returns a flattened list of all task dictionaries present in
    st.session_state.tasks_by_status across all status categories.
    
    Returns:
        List of all task dictionaries from all status lists combined
    """
    logger.info("Getting all tasks from session state")
    
    try:
        # Ensure tasks_by_status structure exists
        if not hasattr(st.session_state, 'tasks_by_status') or not isinstance(st.session_state.tasks_by_status, dict):
            logger.info("No tasks_by_status in session state, returning empty list")
            return []
        
        # Flatten all task lists
        all_tasks = []
        for status_key, task_list in st.session_state.tasks_by_status.items():
            if isinstance(task_list, list):
                all_tasks.extend(task_list)
        
        logger.info(f"Retrieved {len(all_tasks)} total tasks from session state")
        return all_tasks
        
    except Exception as e:
        logger.error(f"Error getting all tasks from session state: {e}", exc_info=True)
        raise
