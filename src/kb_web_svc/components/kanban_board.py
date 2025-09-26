"""Kanban board component for displaying tasks organized by status.

This module provides a three-column kanban board layout that displays tasks
organized by their status (To Do, In Progress, Done) with task counts.
"""

import logging
from typing import Any, Dict

import streamlit as st

from ..models.task import Status
from ..state_management import get_tasks_by_status
from .task_card import render_task_card

logger = logging.getLogger(__name__)


def render_kanban_board() -> None:
    """Render a three-column kanban board organized by task status.
    
    This function creates a three-column layout displaying tasks categorized
    by their status: To Do, In Progress, and Done. Each column shows a header
    with the status name and task count, followed by task cards for all tasks
    in that status.
    
    The function retrieves tasks from the session state using get_tasks_by_status
    and renders each task using the render_task_card component. Visual separation
    is provided between columns using markdown horizontal rules.
    
    Handles errors gracefully by logging them and continuing to render other
    tasks and columns even if individual task rendering fails.
    """
    logger.info("Rendering kanban board")
    
    try:
        # Create three columns for the kanban board
        cols = st.columns(3)
        
        # Define statuses in order
        statuses = [Status.TODO, Status.IN_PROGRESS, Status.DONE]
        
        # Render each column
        for idx, status in enumerate(statuses):
            with cols[idx]:
                try:
                    # Get tasks for this status
                    tasks = get_tasks_by_status(status.value) or []
                    task_count = len(tasks)
                    
                    # Display column header with status name and count
                    st.subheader(f"{status.value} ({task_count})")
                    
                    # Add visual separation
                    st.markdown("---")
                    
                    # Render each task in this status
                    for task in tasks:
                        try:
                            render_task_card(task)
                        except Exception as task_error:
                            logger.error(f"Error rendering task card for task {task.get('id', 'unknown')}: {task_error}", exc_info=True)
                            # Continue rendering other tasks even if one fails
                            continue
                            
                except Exception as column_error:
                    logger.error(f"Error rendering column for status {status.value}: {column_error}", exc_info=True)
                    # Display error message in the column but continue
                    st.error(f"Error loading {status.value} tasks")
                    continue
        
        logger.info("Kanban board rendered successfully")
        
    except Exception as e:
        logger.error(f"Error rendering kanban board: {e}", exc_info=True)
        st.error("An error occurred while loading the kanban board. Please refresh the page.")
