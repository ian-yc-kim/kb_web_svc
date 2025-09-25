"""State management module for Streamlit session state initialization and task loading.

This module provides functions to initialize and manage the Streamlit session state
with core data structures for the kanban task management application.
"""

import logging
from typing import Dict, Any, List

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
