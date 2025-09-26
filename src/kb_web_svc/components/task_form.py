"""Task form component for creating new tasks.

This module provides a Streamlit form component for task creation with all
required fields and session state management.
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any

import streamlit as st

from ..models.task import Priority, Status

logger = logging.getLogger(__name__)


def render_task_form() -> None:
    """Render the task creation form with all required fields.
    
    This function creates a comprehensive task creation form using Streamlit widgets
    and manages form data through st.session_state.task_form_data. All form values
    are persisted in session state to maintain state across reruns.
    
    The form includes:
    - title: Text input for task title
    - assignee: Text input for assignee name
    - due_date: Date picker for due date
    - description: Text input for task description
    - priority: Selectbox with Priority enum options
    - labels: Multiselect for task categorization
    - estimated_time: Number input for time estimation
    - status: Selectbox with Status enum options
    - Submit button for form submission
    """
    logger.info("Rendering task creation form")
    
    try:
        # Initialize task_form_data in session state if not exists
        _initialize_form_data()
        
        # Render form fields
        st.session_state.task_form_data["title"] = st.text_input(
            "Title *",
            value=st.session_state.task_form_data.get("title", ""),
            placeholder="Enter task title",
            help="Required field. Provide a descriptive title for the task."
        )
        
        st.session_state.task_form_data["assignee"] = st.text_input(
            "Assignee",
            value=st.session_state.task_form_data.get("assignee", ""),
            placeholder="Enter assignee name",
            help="Optional field. Specify who the task is assigned to."
        )
        
        st.session_state.task_form_data["due_date"] = st.date_input(
            "Due Date",
            value=st.session_state.task_form_data.get("due_date"),
            help="Optional field. Select the due date for the task."
        )
        
        st.session_state.task_form_data["description"] = st.text_input(
            "Description",
            value=st.session_state.task_form_data.get("description", ""),
            placeholder="Enter task description",
            help="Optional field. Provide detailed information about the task."
        )
        
        # Priority selectbox with enum options
        priority_options = [p.value for p in Priority]
        priority_index = 0
        current_priority = st.session_state.task_form_data.get("priority")
        if current_priority and current_priority in priority_options:
            priority_index = priority_options.index(current_priority)
        
        selected_priority = st.selectbox(
            "Priority",
            options=priority_options,
            index=priority_index,
            help="Optional field. Select the priority level for the task."
        )
        st.session_state.task_form_data["priority"] = selected_priority
        
        # Labels multiselect with predefined options
        label_options = ["Bug", "Feature", "Refactor", "Documentation"]
        st.session_state.task_form_data["labels"] = st.multiselect(
            "Labels",
            options=label_options,
            default=st.session_state.task_form_data.get("labels", []),
            help="Optional field. Select relevant labels for task categorization."
        )
        
        st.session_state.task_form_data["estimated_time"] = st.number_input(
            "Estimated Time (hours)",
            min_value=0.0,
            step=0.5,
            value=st.session_state.task_form_data.get("estimated_time", 0.0),
            help="Optional field. Estimate the time required to complete the task."
        )
        
        # Status selectbox with enum options
        status_options = [s.value for s in Status]
        status_index = 0
        current_status = st.session_state.task_form_data.get("status")
        if current_status and current_status in status_options:
            status_index = status_options.index(current_status)
        elif not current_status:
            # Default to "To Do" if no status is set
            st.session_state.task_form_data["status"] = Status.TODO.value
        
        selected_status = st.selectbox(
            "Status *",
            options=status_options,
            index=status_index,
            help="Required field. Select the current status of the task."
        )
        st.session_state.task_form_data["status"] = selected_status
        
        # Submit button
        if st.button("Submit", type="primary"):
            logger.info("Task form submit button clicked")
            _handle_form_submission()
        
        logger.info("Task creation form rendered successfully")
        
    except Exception as e:
        logger.error(f"Error rendering task creation form: {e}", exc_info=True)
        st.error("An error occurred while rendering the task form. Please try again.")


def _initialize_form_data() -> None:
    """Initialize task_form_data in session state with default values.
    
    This function ensures that st.session_state.task_form_data exists and
    contains all required form fields with appropriate default values.
    """
    logger.debug("Initializing task form data in session state")
    
    try:
        # Initialize task_form_data if it doesn't exist
        if "task_form_data" not in st.session_state:
            st.session_state.task_form_data = {}
        
        # Ensure all form fields have default values
        defaults = {
            "title": "",
            "assignee": "",
            "due_date": None,
            "description": "",
            "priority": Priority.MEDIUM.value,  # Default to Medium priority
            "labels": [],
            "estimated_time": 0.0,
            "status": Status.TODO.value  # Default to To Do status
        }
        
        for field, default_value in defaults.items():
            if field not in st.session_state.task_form_data:
                st.session_state.task_form_data[field] = default_value
        
        logger.debug("Task form data initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing task form data: {e}", exc_info=True)
        raise


def _handle_form_submission() -> None:
    """Handle task form submission.
    
    This function processes the form submission by updating a submission flag
    in session state. Future implementations will include validation and
    backend submission logic.
    """
    logger.info("Handling task form submission")
    
    try:
        # For now, just set a submission flag in session state
        st.session_state.task_form_submitted = True
        
        # Log the form data for debugging
        form_data = st.session_state.task_form_data
        logger.info(f"Task form submitted with data: {form_data}")
        
        # Show success message
        st.success("Task form submitted successfully! (Backend submission not yet implemented)")
        
        # Future implementation will include:
        # - Form validation
        # - Backend service call to create task
        # - Session state updates
        # - Form reset on successful submission
        
    except Exception as e:
        logger.error(f"Error handling task form submission: {e}", exc_info=True)
        st.error("An error occurred while submitting the task form. Please try again.")
