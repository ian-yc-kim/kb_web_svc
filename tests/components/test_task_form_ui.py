"""Unit tests for the task form UI component.

These tests verify the task form rendering, session state management,
and user interactions using mocked Streamlit components.
"""

import sys
from unittest.mock import MagicMock, patch, call
from datetime import date

import pytest

from kb_web_svc.models.task import Priority, Status


class MockSessionState:
    """Mock implementation of streamlit session state that behaves like a dictionary."""
    
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, name):
        return self._data.get(name)
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __contains__(self, name):
        return name in self._data
    
    def get(self, name, default=None):
        return self._data.get(name, default)


class TestTaskFormUI:
    """Test cases for task form UI component."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Remove any previously imported modules to ensure clean state
        modules_to_remove = [
            'kb_web_svc.components.task_form',
            'kb_web_svc.components'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def test_form_renders_all_fields(self):
        """Test that all required form fields are rendered with correct labels and options."""
        # Create mock session state
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input') as mock_text_input, \
             patch('streamlit.date_input') as mock_date_input, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.number_input') as mock_number_input, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Mock return values for form widgets
            mock_text_input.side_effect = ["", "", ""]  # title, assignee, description
            mock_date_input.return_value = None
            mock_selectbox.side_effect = [Priority.MEDIUM.value, Status.TODO.value]  # priority, status
            mock_multiselect.return_value = []
            mock_number_input.return_value = 0.0
            mock_button.return_value = False
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify all text inputs are called with correct labels
            expected_text_calls = [
                call("Title *", value="", placeholder="Enter task title", 
                     help="Required field. Provide a descriptive title for the task."),
                call("Assignee", value="", placeholder="Enter assignee name",
                     help="Optional field. Specify who the task is assigned to."),
                call("Description", value="", placeholder="Enter task description",
                     help="Optional field. Provide detailed information about the task.")
            ]
            mock_text_input.assert_has_calls(expected_text_calls)
            
            # Verify date input
            mock_date_input.assert_called_once_with(
                "Due Date", value=None, 
                help="Optional field. Select the due date for the task."
            )
            
            # Verify priority selectbox with enum options (Medium is at index 2)
            priority_options = [p.value for p in Priority]
            mock_selectbox.assert_any_call(
                "Priority", options=priority_options, index=2,
                help="Optional field. Select the priority level for the task."
            )
            
            # Verify status selectbox with enum options
            status_options = [s.value for s in Status]
            mock_selectbox.assert_any_call(
                "Status *", options=status_options, index=0,
                help="Required field. Select the current status of the task."
            )
            
            # Verify multiselect for labels
            mock_multiselect.assert_called_once_with(
                "Labels", options=["Bug", "Feature", "Refactor", "Documentation"],
                default=[], help="Optional field. Select relevant labels for task categorization."
            )
            
            # Verify number input for estimated time
            mock_number_input.assert_called_once_with(
                "Estimated Time (hours)", min_value=0.0, step=0.5, value=0.0,
                help="Optional field. Estimate the time required to complete the task."
            )
            
            # Verify submit button
            mock_button.assert_called_once_with("Submit", type="primary")

    def test_session_state_initialization(self):
        """Test that session state is properly initialized with default values."""
        # Create mock session state
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', return_value=""), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value]), \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify session state was initialized
            assert mock_session_state.task_form_data is not None
            
            # Verify default values
            form_data = mock_session_state.task_form_data
            assert form_data["title"] == ""
            assert form_data["assignee"] == ""
            assert form_data["due_date"] is None
            assert form_data["description"] == ""
            assert form_data["priority"] == Priority.MEDIUM.value
            assert form_data["labels"] == []
            assert form_data["estimated_time"] == 0.0
            assert form_data["status"] == Status.TODO.value

    def test_session_state_updates_on_input(self):
        """Test that session state is updated when form inputs change."""
        # Pre-populate session state with existing form data
        mock_session_state = MockSessionState()
        mock_session_state.task_form_data = {
            "title": "Existing Task",
            "assignee": "John Doe",
            "due_date": date(2024, 12, 31),
            "description": "Existing description",
            "priority": Priority.HIGH.value,
            "labels": ["Bug"],
            "estimated_time": 2.5,
            "status": Status.IN_PROGRESS.value
        }
        
        with patch('streamlit.text_input') as mock_text_input, \
             patch('streamlit.date_input') as mock_date_input, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.number_input') as mock_number_input, \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Mock updated return values
            mock_text_input.side_effect = ["Updated Task", "Jane Smith", "Updated description"]
            mock_date_input.return_value = date(2025, 1, 15)
            mock_selectbox.side_effect = [Priority.CRITICAL.value, Status.DONE.value]
            mock_multiselect.return_value = ["Feature", "Documentation"]
            mock_number_input.return_value = 5.0
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify widgets are called with existing values
            mock_text_input.assert_any_call(
                "Title *", value="Existing Task", placeholder="Enter task title",
                help="Required field. Provide a descriptive title for the task."
            )
            mock_text_input.assert_any_call(
                "Assignee", value="John Doe", placeholder="Enter assignee name",
                help="Optional field. Specify who the task is assigned to."
            )
            mock_text_input.assert_any_call(
                "Description", value="Existing description", placeholder="Enter task description",
                help="Optional field. Provide detailed information about the task."
            )
            
            mock_date_input.assert_called_once_with(
                "Due Date", value=date(2024, 12, 31),
                help="Optional field. Select the due date for the task."
            )
            
            mock_multiselect.assert_called_once_with(
                "Labels", options=["Bug", "Feature", "Refactor", "Documentation"],
                default=["Bug"], help="Optional field. Select relevant labels for task categorization."
            )
            
            mock_number_input.assert_called_once_with(
                "Estimated Time (hours)", min_value=0.0, step=0.5, value=2.5,
                help="Optional field. Estimate the time required to complete the task."
            )
            
            # Verify session state is updated with new values
            form_data = mock_session_state.task_form_data
            assert form_data["title"] == "Updated Task"
            assert form_data["assignee"] == "Jane Smith"
            assert form_data["due_date"] == date(2025, 1, 15)
            assert form_data["description"] == "Updated description"
            assert form_data["priority"] == Priority.CRITICAL.value
            assert form_data["labels"] == ["Feature", "Documentation"]
            assert form_data["estimated_time"] == 5.0
            assert form_data["status"] == Status.DONE.value

    def test_submit_button_present_and_functional(self):
        """Test that the submit button is present and functional."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', return_value="Test Task"), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value]), \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=True) as mock_button, \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success') as mock_success, \
             patch('logging.getLogger'):
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify submit button is called
            mock_button.assert_called_once_with("Submit", type="primary")
            
            # Verify success message is shown when button is clicked
            mock_success.assert_called_once_with(
                "Task form submitted successfully! (Backend submission not yet implemented)"
            )
            
            # Verify submission flag is set in session state
            assert mock_session_state.task_form_submitted is True

    def test_priority_enum_options_displayed_correctly(self):
        """Test that Priority enum options are correctly displayed in selectbox."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', return_value=""), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Mock selectbox to return specific values
            mock_selectbox.side_effect = [Priority.HIGH.value, Status.TODO.value]
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify priority selectbox is called with correct enum options
            expected_priority_options = [p.value for p in Priority]
            assert expected_priority_options == ["Critical", "High", "Medium", "Low"]
            
            mock_selectbox.assert_any_call(
                "Priority", options=expected_priority_options, index=2,
                help="Optional field. Select the priority level for the task."
            )

    def test_status_enum_options_displayed_correctly(self):
        """Test that Status enum options are correctly displayed in selectbox."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', return_value=""), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Mock selectbox to return specific values
            mock_selectbox.side_effect = [Priority.MEDIUM.value, Status.IN_PROGRESS.value]
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify status selectbox is called with correct enum options
            expected_status_options = [s.value for s in Status]
            assert expected_status_options == ["To Do", "In Progress", "Done"]
            
            mock_selectbox.assert_any_call(
                "Status *", options=expected_status_options, index=0,
                help="Required field. Select the current status of the task."
            )

    def test_error_handling_in_form_rendering(self):
        """Test that errors during form rendering are handled gracefully."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', side_effect=Exception("Streamlit error")), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.error') as mock_error, \
             patch('logging.getLogger') as mock_get_logger:
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            
            # Verify error message is shown to user
            mock_error.assert_called_once_with(
                "An error occurred while rendering the task form. Please try again."
            )

    def test_existing_session_state_preserved(self):
        """Test that existing session state data is preserved during initialization."""
        # Pre-populate session state with partial data
        mock_session_state = MockSessionState()
        mock_session_state.task_form_data = {
            "title": "Existing Title",
            "priority": Priority.CRITICAL.value
            # Missing other fields
        }
        
        with patch('streamlit.text_input') as mock_text_input, \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success'), \
             patch('logging.getLogger'):
            
            # Mock text_input to return existing values when they exist
            # The form will call text_input with value="Existing Title" for title
            # We want it to return that same value to preserve it
            mock_text_input.side_effect = ["Existing Title", "", ""]  # title, assignee, description
            
            # Mock selectbox to return existing priority and default status
            mock_selectbox.side_effect = [Priority.CRITICAL.value, Status.TODO.value]
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify existing data is preserved
            form_data = mock_session_state.task_form_data
            assert form_data["title"] == "Existing Title"
            assert form_data["priority"] == Priority.CRITICAL.value
            
            # Verify missing fields are initialized with defaults
            assert form_data["assignee"] == ""
            assert form_data["due_date"] is None
            assert form_data["description"] == ""
            assert form_data["labels"] == []
            assert form_data["estimated_time"] == 0.0
            assert form_data["status"] == Status.TODO.value

    def test_form_submission_error_handling(self):
        """Test that errors during form submission are handled gracefully."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.text_input', return_value="Test Task"), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value]), \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.number_input', return_value=0.0), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.success', side_effect=Exception("Submission error")), \
             patch('streamlit.error') as mock_error, \
             patch('logging.getLogger') as mock_get_logger:
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form()
            
            # Verify error was logged
            mock_logger.error.assert_called()
            
            # Verify error message is shown to user
            mock_error.assert_called_once_with(
                "An error occurred while submitting the task form. Please try again."
            )
