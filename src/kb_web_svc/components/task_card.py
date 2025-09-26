"""Task card component for displaying individual task details.

This module provides a reusable Streamlit component for displaying task information
in a visually distinct card format using st.expander.
"""

import logging
from typing import Dict, Any

import streamlit as st

logger = logging.getLogger(__name__)


def render_task_card(task: Dict[str, Any]) -> None:
    """Render a task card component using st.expander.
    
    This function takes a task dictionary and displays its details in a visually
    distinct and well-formatted card using Streamlit's expander component.
    
    Args:
        task: Dictionary containing task data with the following expected keys:
            - title: Task title (string, required)
            - assignee: Assigned person (string, optional)
            - due_date: Due date (string in ISO format or None, optional)
            - priority: Task priority (string, optional)
            - status: Task status (string, required)
            - description: Task description (string, optional)
            - id: Task ID (string, optional)
            - labels: Task labels (list, optional)
            - estimated_time: Estimated time in hours (float, optional)
            - created_at: Creation timestamp (string, optional)
            - last_modified: Last modified timestamp (string, optional)
    
    The function handles missing or None values gracefully by displaying "N/A" or "—".
    """
    logger.debug(f"Rendering task card for task: {task.get('id', 'unknown')}")
    
    try:
        # Extract task details with fallbacks
        title = task.get('title', 'Untitled Task')
        status = task.get('status', 'Unknown')
        assignee = task.get('assignee') or '—'
        due_date = task.get('due_date') or '—'
        priority = task.get('priority') or '—'
        description = task.get('description') or '—'
        task_id = task.get('id', '')
        labels = task.get('labels', [])
        estimated_time = task.get('estimated_time')
        
        # Format estimated time
        if estimated_time is not None:
            estimated_time_str = f"{estimated_time} hours"
        else:
            estimated_time_str = "—"
        
        # Format labels
        if labels and isinstance(labels, list) and len(labels) > 0:
            labels_str = ", ".join(str(label) for label in labels)
        else:
            labels_str = "—"
        
        # Create expander header with title and status badge
        expander_header = f"**{title}** • `{status}`"
        
        # Create the main expander container
        with st.expander(expander_header, expanded=False):
            # Display task title prominently inside expander
            st.markdown(f"### {title}")
            
            # Create two columns for better layout
            col1, col2 = st.columns(2)
            
            with col1:
                st.caption("**Assignee**")
                st.write(assignee)
                
                st.caption("**Priority**")
                # Add basic styling for priority with colors
                if priority == "Critical":
                    st.markdown(f'<span style="color: red;">🔴 {priority}</span>', unsafe_allow_html=True)
                elif priority == "High":
                    st.markdown(f'<span style="color: orange;">🟠 {priority}</span>', unsafe_allow_html=True)
                elif priority == "Medium":
                    st.markdown(f'<span style="color: blue;">🔵 {priority}</span>', unsafe_allow_html=True)
                elif priority == "Low":
                    st.markdown(f'<span style="color: green;">🟢 {priority}</span>', unsafe_allow_html=True)
                else:
                    st.write(priority)
                
                st.caption("**Labels**")
                st.write(labels_str)
            
            with col2:
                st.caption("**Due Date**")
                st.write(due_date)
                
                st.caption("**Status**")
                # Add basic styling for status
                if status == "To Do":
                    st.markdown(f'<span style="color: gray;">⚪ {status}</span>', unsafe_allow_html=True)
                elif status == "In Progress":
                    st.markdown(f'<span style="color: blue;">🔵 {status}</span>', unsafe_allow_html=True)
                elif status == "Done":
                    st.markdown(f'<span style="color: green;">✅ {status}</span>', unsafe_allow_html=True)
                else:
                    st.write(status)
                
                st.caption("**Estimated Time**")
                st.write(estimated_time_str)
            
            # Description takes full width
            if description and description != "—":
                st.caption("**Description**")
                st.markdown(description)
            else:
                st.caption("**Description**")
                st.write("—")
            
            # Task ID for reference (if available)
            if task_id:
                st.caption("**Task ID**")
                st.code(task_id, language=None)
        
        logger.debug(f"Successfully rendered task card for task: {task.get('id', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Error rendering task card: {e}", exc_info=True)
        # Fallback display in case of error
        with st.expander(f"Task: {task.get('title', 'Error loading task')}", expanded=False):
            st.error("An error occurred while displaying this task card.")
            st.caption("Raw task data:")
            st.json(task)
