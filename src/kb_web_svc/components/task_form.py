"""Task form component for creating new tasks.

This module provides a Streamlit form component for task creation with all
required fields, client-side validation, and session state management.
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any

import streamlit as st
from sqlalchemy.orm import Session

from ..models.task import Priority, Status

logger = logging.getLogger(__name__)


def render_task_form(db: Session) -> None:
    """Render the task creation form with all required fields and validation.
    
    This function creates a comprehensive task creation form using Streamlit widgets
    with real-time client-side validation. Form data is managed through session state
    with error handling and validation feedback.
    
    Args:
        db: SQLAlchemy database session for future backend integration
    
    The form includes:
    - title: Text input for task title (required)
    - assignee: Text input for assignee name
    - due_date: Date picker for due date (cannot be in the past)
    - description: Text input for task description
    - priority: Selectbox with Priority enum options (must be valid enum value)
    - labels: Multiselect for task categorization (list of non-empty strings)
    - estimated_time: Number input for time estimation (range 0.5-8.0 hours)
    - status: Selectbox with Status enum options (required)
    - Submit button for form submission with validation
    """
    logger.info("Rendering task creation form with validation")
    
    try:
        # Initialize form data and error states in session state
        _initialize_form_state()
        
        # Render form fields with validation
        col1, col2 = st.columns(2)
        
        with col1:
            # Title field (required)
            st.session_state.form_data["title"] = st.text_input(
                "Title *",
                value=st.session_state.form_data.get("title", ""),
                placeholder="Enter task title",
                help="Required field. Provide a descriptive title for the task.",
                key="form_data_title",
                on_change=lambda: _on_title_change()
            )
            
            # Display title error if exists
            if "title" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["title"])
            
            # Assignee field
            st.session_state.form_data["assignee"] = st.text_input(
                "Assignee",
                value=st.session_state.form_data.get("assignee", ""),
                placeholder="Enter assignee name",
                help="Optional field. Specify who the task is assigned to."
            )
            
            # Due date field
            st.session_state.form_data["due_date"] = st.date_input(
                "Due Date",
                value=st.session_state.form_data.get("due_date"),
                help="Optional field. Select the due date for the task.",
                key="form_data_due_date",
                on_change=lambda: _on_due_date_change()
            )
            
            # Display due date error if exists
            if "due_date" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["due_date"])
            
            # Description field
            st.session_state.form_data["description"] = st.text_input(
                "Description",
                value=st.session_state.form_data.get("description", ""),
                placeholder="Enter task description",
                help="Optional field. Provide detailed information about the task."
            )
        
        with col2:
            # Priority selectbox with enum options
            priority_options = [p.value for p in Priority]
            priority_index = 0
            current_priority = st.session_state.form_data.get("priority")
            if current_priority and current_priority in priority_options:
                priority_index = priority_options.index(current_priority)
            
            selected_priority = st.selectbox(
                "Priority",
                options=priority_options,
                index=priority_index,
                help="Optional field. Select the priority level for the task.",
                key="form_data_priority",
                on_change=lambda: _on_priority_change()
            )
            st.session_state.form_data["priority"] = selected_priority
            
            # Display priority error if exists
            if "priority" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["priority"])
            
            # Status selectbox with enum options (required)
            status_options = [s.value for s in Status]
            status_index = 0
            current_status = st.session_state.form_data.get("status")
            if current_status and current_status in status_options:
                status_index = status_options.index(current_status)
            elif not current_status:
                # Default to "To Do" if no status is set
                st.session_state.form_data["status"] = Status.TODO.value
            
            selected_status = st.selectbox(
                "Status *",
                options=status_options,
                index=status_index,
                help="Required field. Select the current status of the task.",
                key="form_data_status",
                on_change=lambda: _on_status_change()
            )
            st.session_state.form_data["status"] = selected_status
            
            # Display status error if exists
            if "status" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["status"])
            
            # Labels multiselect with predefined options
            st.session_state.form_data["labels"] = st.multiselect(
                "Labels",
                options=["Bug", "Feature", "Refactor", "Documentation"],
                default=st.session_state.form_data.get("labels", []),
                help="Optional field. Select relevant labels for task categorization.",
                key="form_data_labels",
                on_change=lambda: _on_labels_change()
            )
            
            # Display labels error if exists
            if "labels" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["labels"])
            
            # Estimated time field with constraints
            st.session_state.form_data["estimated_time"] = st.number_input(
                "Estimated Time (hours)",
                min_value=0.5,
                max_value=8.0,
                step=0.5,
                value=st.session_state.form_data.get("estimated_time", 0.5),
                help="Optional field. Estimate the time required to complete the task (0.5 to 8.0 hours).",
                key="form_data_estimated_time",
                on_change=lambda: _on_estimated_time_change()
            )
            
            # Display estimated time error if exists
            if "estimated_time" in st.session_state.form_errors:
                st.error(st.session_state.form_errors["estimated_time"])
        
        # Submit button
        if st.button("Submit", type="primary"):
            logger.info("Task form submit button clicked")
            _handle_form_submission()
        
        logger.info("Task creation form rendered successfully")
        
    except Exception as e:
        logger.error(f"Error rendering task creation form: {e}", exc_info=True)
        st.error("An error occurred while rendering the task form. Please try again.")


def _initialize_form_state() -> None:
    """Initialize form_data and form_errors in session state with default values.
    
    This function ensures that st.session_state.form_data and st.session_state.form_errors
    exist and contain all required form fields with appropriate default values.
    Maintains compatibility with existing task_form_data for backward compatibility.
    """
    logger.debug("Initializing task form state in session state")
    
    try:
        # Initialize form_data if it doesn't exist
        if "form_data" not in st.session_state:
            st.session_state.form_data = {}
        
        # Initialize form_errors if it doesn't exist
        if "form_errors" not in st.session_state:
            st.session_state.form_errors = {}
        
        # Ensure all form fields have default values
        defaults = {
            "title": "",
            "assignee": "",
            "due_date": None,
            "description": "",
            "priority": Priority.MEDIUM.value,  # Default to Medium priority
            "labels": [],
            "estimated_time": 0.5,  # Updated default to match constraints
            "status": Status.TODO.value  # Default to To Do status
        }
        
        # Migrate from legacy task_form_data if it exists
        if "task_form_data" in st.session_state and st.session_state.task_form_data:
            for field, value in st.session_state.task_form_data.items():
                if field in defaults and value is not None:
                    st.session_state.form_data[field] = value
        
        # Set defaults for any missing fields
        for field, default_value in defaults.items():
            if field not in st.session_state.form_data:
                st.session_state.form_data[field] = default_value
        
        # Maintain backward compatibility by syncing form_data to task_form_data
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
        logger.debug("Task form state initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing task form state: {e}", exc_info=True)
        raise


def _validate_field(field_name: str, current_form_data: Dict[str, Any], current_errors: Dict[str, str]) -> Dict[str, str]:
    """Validate a specific field and update error messages.
    
    Args:
        field_name: Name of the field to validate
        current_form_data: Current form data dictionary
        current_errors: Current errors dictionary
    
    Returns:
        Updated errors dictionary with validation results
    """
    logger.debug(f"Validating field: {field_name}")
    
    try:
        updated_errors = current_errors.copy()
        
        if field_name == "title":
            title_value = current_form_data.get("title", "")
            if not title_value or not title_value.strip():
                updated_errors["title"] = "Title is required."
            else:
                # Remove error if validation passes
                updated_errors.pop("title", None)
        
        elif field_name == "status":
            status_value = current_form_data.get("status", "")
            valid_statuses = [s.value for s in Status]
            if not status_value or status_value not in valid_statuses:
                updated_errors["status"] = "Status is required and must be 'To Do', 'In Progress', or 'Done'."
            else:
                # Remove error if validation passes
                updated_errors.pop("status", None)
        
        elif field_name == "due_date":
            due_date_value = current_form_data.get("due_date")
            if due_date_value is not None and due_date_value < date.today():
                updated_errors["due_date"] = "Due date cannot be in the past."
            else:
                # Remove error if validation passes
                updated_errors.pop("due_date", None)
        
        elif field_name == "priority":
            priority_value = current_form_data.get("priority")
            if priority_value is not None:
                valid_priorities = [p.value for p in Priority]
                if priority_value not in valid_priorities:
                    updated_errors["priority"] = "Invalid priority. Must be 'Critical', 'High', 'Medium', or 'Low'."
                else:
                    # Remove error if validation passes
                    updated_errors.pop("priority", None)
            else:
                # Remove error if no priority is provided (optional field)
                updated_errors.pop("priority", None)
        
        elif field_name == "labels":
            labels_value = current_form_data.get("labels")
            if labels_value is not None:
                if not isinstance(labels_value, list):
                    updated_errors["labels"] = "Labels must be a list of non-empty text values."
                else:
                    # Check if any label is invalid (non-string or empty after stripping)
                    cleaned_labels = []
                    has_error = False
                    for label in labels_value:
                        if not isinstance(label, str):
                            has_error = True
                            break
                        stripped = label.strip()
                        if not stripped:
                            has_error = True
                            break
                        cleaned_labels.append(stripped)
                    
                    if has_error:
                        updated_errors["labels"] = "Labels must be a list of non-empty text values."
                    else:
                        # Update cleaned list back to form_data for consistency
                        current_form_data["labels"] = cleaned_labels
                        # Remove error if validation passes
                        updated_errors.pop("labels", None)
            else:
                # Remove error if no labels are provided (optional field)
                updated_errors.pop("labels", None)
        
        elif field_name == "estimated_time":
            estimated_time_value = current_form_data.get("estimated_time")
            if estimated_time_value is not None:
                if not isinstance(estimated_time_value, (int, float)) or not (0.5 <= estimated_time_value <= 8.0):
                    updated_errors["estimated_time"] = "Estimated time must be between 0.5 and 8.0 hours."
                else:
                    # Remove error if validation passes
                    updated_errors.pop("estimated_time", None)
            else:
                # Remove error if no estimated time is provided (optional field)
                updated_errors.pop("estimated_time", None)
        
        # Update session state with new errors
        st.session_state.form_errors = updated_errors
        
        return updated_errors
        
    except Exception as e:
        logger.error(f"Error validating field {field_name}: {e}", exc_info=True)
        return current_errors


def _on_title_change() -> None:
    """Handle title field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_title" in st.session_state:
            st.session_state.form_data["title"] = st.session_state.form_data_title
        
        # Trigger validation
        _validate_field("title", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling title change: {e}", exc_info=True)


def _on_status_change() -> None:
    """Handle status field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_status" in st.session_state:
            st.session_state.form_data["status"] = st.session_state.form_data_status
        
        # Trigger validation
        _validate_field("status", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling status change: {e}", exc_info=True)


def _on_due_date_change() -> None:
    """Handle due date field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_due_date" in st.session_state:
            st.session_state.form_data["due_date"] = st.session_state.form_data_due_date
        
        # Trigger validation
        _validate_field("due_date", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling due date change: {e}", exc_info=True)


def _on_priority_change() -> None:
    """Handle priority field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_priority" in st.session_state:
            st.session_state.form_data["priority"] = st.session_state.form_data_priority
        
        # Trigger validation
        _validate_field("priority", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling priority change: {e}", exc_info=True)


def _on_labels_change() -> None:
    """Handle labels field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_labels" in st.session_state:
            st.session_state.form_data["labels"] = st.session_state.form_data_labels
        
        # Trigger validation
        _validate_field("labels", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling labels change: {e}", exc_info=True)


def _on_estimated_time_change() -> None:
    """Handle estimated time field change and trigger validation."""
    try:
        # Update form_data from widget state
        if "form_data_estimated_time" in st.session_state:
            st.session_state.form_data["estimated_time"] = st.session_state.form_data_estimated_time
        
        # Trigger validation
        _validate_field("estimated_time", st.session_state.form_data, st.session_state.form_errors)
        
        # Sync to legacy task_form_data for backward compatibility
        st.session_state.task_form_data = st.session_state.form_data.copy()
        
    except Exception as e:
        logger.error(f"Error handling estimated time change: {e}", exc_info=True)


def _handle_form_submission() -> None:
    """Handle task form submission with validation.
    
    This function processes the form submission by validating all required fields
    and displaying appropriate error messages or success confirmation.
    """
    logger.info("Handling task form submission")
    
    try:
        # Validate all fields before submission
        _validate_field("title", st.session_state.form_data, st.session_state.form_errors)
        _validate_field("status", st.session_state.form_data, st.session_state.form_errors)
        _validate_field("due_date", st.session_state.form_data, st.session_state.form_errors)
        _validate_field("priority", st.session_state.form_data, st.session_state.form_errors)
        _validate_field("labels", st.session_state.form_data, st.session_state.form_errors)
        _validate_field("estimated_time", st.session_state.form_data, st.session_state.form_errors)
        
        # Check if there are any validation errors
        if st.session_state.form_errors:
            logger.warning(f"Form submission blocked due to validation errors: {st.session_state.form_errors}")
            st.error("Please correct the errors before submitting.")
            return
        
        # Set submission flag in session state
        st.session_state.task_form_submitted = True
        
        # Log the form data for debugging
        form_data = st.session_state.form_data
        logger.info(f"Task form submitted with valid data: {form_data}")
        
        # Show success message
        st.success("Task form submitted successfully! (Backend submission not yet implemented)")
        
        # Future implementation will include:
        # - Backend service call to create task using db session
        # - Session state updates with new task
        # - Form reset on successful submission
        
    except Exception as e:
        logger.error(f"Error handling task form submission: {e}", exc_info=True)
        st.error("An error occurred while submitting the task form. Please try again.")
