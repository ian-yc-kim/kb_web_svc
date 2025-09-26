"""Unit tests for task form validation functionality.

These tests verify the client-side validation logic for the task creation form,
including form state initialization, real-time validation feedback, and error handling.
"""

import sys
from unittest.mock import MagicMock, patch, call
from datetime import date, timedelta

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
    
    def pop(self, name, default=None):
        return self._data.pop(name, default)


class TestTaskFormValidation:
    """Test cases for task form validation functionality."""

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

    def test_initializes_form_state(self):
        """Test that render_task_form initializes form_data and form_errors in session state."""
        mock_session_state = MockSessionState()
        mock_db_session = MagicMock()
        
        with patch('streamlit.text_input', return_value=""), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value, 0.5]), \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.session_state', mock_session_state), \
             patch('logging.getLogger'):
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form(mock_db_session)
            
            # Verify form_data is initialized with expected defaults
            assert 'form_data' in mock_session_state
            assert isinstance(mock_session_state.form_data, dict)
            
            form_data = mock_session_state.form_data
            expected_fields = ['title', 'assignee', 'due_date', 'description', 'priority', 'labels', 'estimated_time', 'status']
            for field in expected_fields:
                assert field in form_data
            
            # Verify default values
            assert form_data['title'] == ""
            assert form_data['assignee'] == ""
            assert form_data['due_date'] is None
            assert form_data['description'] == ""
            assert form_data['priority'] == Priority.MEDIUM.value
            assert form_data['labels'] == []
            assert form_data['estimated_time'] == 0.5  # Updated to match new default
            assert form_data['status'] == Status.TODO.value
            
            # Verify form_errors is initialized
            assert 'form_errors' in mock_session_state
            assert isinstance(mock_session_state.form_errors, dict)
            assert mock_session_state.form_errors == {}

    def test_title_empty_whitespace_error(self):
        """Test that empty or whitespace-only title displays 'Title is required.' error."""
        mock_session_state = MockSessionState()
        
        # Test empty title
        mock_session_state.form_data = {'title': ''}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('title', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'title' in updated_errors
            assert updated_errors['title'] == "Title is required."
        
        # Test whitespace-only title
        mock_session_state.form_data = {'title': '   '}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('title', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'title' in updated_errors
            assert updated_errors['title'] == "Title is required."

    def test_due_date_past_triggers_error(self):
        """Test that due date in the past triggers the correct error."""
        mock_session_state = MockSessionState()
        
        # Test past due date
        yesterday = date.today() - timedelta(days=1)
        mock_session_state.form_data = {'due_date': yesterday}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('due_date', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'due_date' in updated_errors
            assert updated_errors['due_date'] == "Due date cannot be in the past."
        
        # Test today's date (should be valid)
        today = date.today()
        mock_session_state.form_data = {'due_date': today}
        mock_session_state.form_errors = {'due_date': "Due date cannot be in the past."}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('due_date', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error is cleared
            assert 'due_date' not in updated_errors

    def test_priority_invalid_triggers_error(self):
        """Test that invalid priority string triggers the correct error."""
        mock_session_state = MockSessionState()
        
        # Test invalid priority
        mock_session_state.form_data = {'priority': 'Urgent'}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('priority', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'priority' in updated_errors
            assert updated_errors['priority'] == "Invalid priority. Must be 'Critical', 'High', 'Medium', or 'Low'."
        
        # Test valid priority clears error
        mock_session_state.form_data = {'priority': Priority.HIGH.value}
        mock_session_state.form_errors = {'priority': "Invalid priority. Must be 'Critical', 'High', 'Medium', or 'Low'."}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('priority', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error is cleared
            assert 'priority' not in updated_errors

    def test_estimated_time_out_of_range_triggers_error(self):
        """Test that estimated_time values outside of the [0.5, 8.0] range trigger the correct error."""
        mock_session_state = MockSessionState()
        
        # Test values outside valid range
        invalid_values = [0.0, 0.4, 8.1, -1.0]
        
        for invalid_value in invalid_values:
            mock_session_state.form_data = {'estimated_time': invalid_value}
            mock_session_state.form_errors = {}
            
            with patch('logging.getLogger'):
                from kb_web_svc.components.task_form import _validate_field
                
                # Call validation function directly
                updated_errors = _validate_field('estimated_time', mock_session_state.form_data, mock_session_state.form_errors)
                
                # Verify error message is set
                assert 'estimated_time' in updated_errors, f"No error for invalid value: {invalid_value}"
                assert updated_errors['estimated_time'] == "Estimated time must be between 0.5 and 8.0 hours."
        
        # Test valid values clear error
        valid_values = [0.5, 1.0, 4.0, 8.0]
        
        for valid_value in valid_values:
            mock_session_state.form_data = {'estimated_time': valid_value}
            mock_session_state.form_errors = {'estimated_time': "Estimated time must be between 0.5 and 8.0 hours."}
            
            with patch('logging.getLogger'):
                from kb_web_svc.components.task_form import _validate_field
                
                # Call validation function directly
                updated_errors = _validate_field('estimated_time', mock_session_state.form_data, mock_session_state.form_errors)
                
                # Verify error is cleared
                assert 'estimated_time' not in updated_errors, f"Error not cleared for valid value: {valid_value}"

    def test_labels_invalid_types_or_empty_strings_trigger_error(self):
        """Test that labels with invalid types or containing empty strings trigger the correct error."""
        mock_session_state = MockSessionState()
        
        # Test case: labels with empty strings after stripping
        mock_session_state.form_data = {'labels': [" ", "", " valid "]}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('labels', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'labels' in updated_errors
            assert updated_errors['labels'] == "Labels must be a list of non-empty text values."
        
        # Test case: labels with non-string values
        mock_session_state.form_data = {'labels': ["Feature", 123]}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('labels', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'labels' in updated_errors
            assert updated_errors['labels'] == "Labels must be a list of non-empty text values."
        
        # Test case: labels not a list
        mock_session_state.form_data = {'labels': "not-a-list"}
        mock_session_state.form_errors = {}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('labels', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error message is set
            assert 'labels' in updated_errors
            assert updated_errors['labels'] == "Labels must be a list of non-empty text values."
        
        # Test case: valid labels clear error
        mock_session_state.form_data = {'labels': ["Feature", "Bug", " Documentation "]}
        mock_session_state.form_errors = {'labels': "Labels must be a list of non-empty text values."}
        
        with patch('logging.getLogger'):
            from kb_web_svc.components.task_form import _validate_field
            
            # Call validation function directly
            updated_errors = _validate_field('labels', mock_session_state.form_data, mock_session_state.form_errors)
            
            # Verify error is cleared and labels are cleaned
            assert 'labels' not in updated_errors
            assert mock_session_state.form_data['labels'] == ["Feature", "Bug", "Documentation"]

    def test_form_submission_validation_blocks_on_errors(self):
        """Test that form submission is blocked when validation errors exist and shows updated error message."""
        mock_session_state = MockSessionState()
        mock_session_state.form_data = {
            'title': '',  # Invalid: empty title
            'status': Status.TODO.value,
            'assignee': '',
            'due_date': None,
            'description': '',
            'priority': Priority.MEDIUM.value,
            'labels': [],
            'estimated_time': 0.5
        }
        mock_session_state.form_errors = {}
        mock_db_session = MagicMock()
        
        with patch('streamlit.text_input', return_value=""), \
             patch('streamlit.date_input', return_value=None), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value, 0.5]), \
             patch('streamlit.multiselect', return_value=[]), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.session_state', mock_session_state), \
             patch('logging.getLogger'):
            
            # Import and call the function
            from kb_web_svc.components.task_form import render_task_form
            render_task_form(mock_db_session)
            
            # Verify that updated validation error message is displayed and submission is blocked
            mock_error.assert_any_call("Please correct the errors before submitting.")
            # Success message should not be called when there are validation errors
            mock_success.assert_not_called()

    def test_submission_blocked_when_any_new_validation_fails(self):
        """Test that submission is blocked when backend validation fails with InvalidPriorityError."""
        mock_session_state = MockSessionState()
        mock_db_session = MagicMock()
        
        # Test with valid form_data (no client-side errors)
        future_date = date.today() + timedelta(days=7)
        mock_session_state.form_data = {
            'title': 'Valid Title',
            'status': Status.TODO.value,
            'assignee': 'John Doe',
            'due_date': future_date,
            'description': 'Valid description',
            'priority': Priority.MEDIUM.value,  # Client-side valid but backend will fail
            'labels': ['Feature'],
            'estimated_time': 2.0
        }
        mock_session_state.form_errors = {}
        
        with patch('streamlit.text_input', side_effect=["Valid Title", "John Doe", "Valid description"]), \
             patch('streamlit.date_input', return_value=future_date), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value, 2.0]), \
             patch('streamlit.multiselect', return_value=['Feature']), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.rerun') as mock_rerun, \
             patch('logging.getLogger'):
            
            # Mock backend services to fail
            with patch('kb_web_svc.components.task_form.create_task') as mock_create_task, \
                 patch('kb_web_svc.components.task_form.add_task_to_session') as mock_add_task:
                
                # Mock create_task to raise InvalidPriorityError
                from kb_web_svc.services.task_service import InvalidPriorityError
                mock_create_task.side_effect = InvalidPriorityError("Invalid priority 'X'. Must be one of: ['Critical', 'High', 'Medium', 'Low']")
                
                # Import and call the function
                from kb_web_svc.components.task_form import render_task_form
                render_task_form(mock_db_session)
                
                # Verify that backend error is displayed with correct prefix
                mock_error.assert_any_call("Invalid priority: Invalid priority 'X'. Must be one of: ['Critical', 'High', 'Medium', 'Low']")
                
                # Verify success is not called and rerun is not called
                mock_success.assert_not_called()
                mock_rerun.assert_not_called()
                
                # Verify add_task_to_session is not called
                mock_add_task.assert_not_called()
                
                # Verify form_data is NOT reset (unchanged from initial values)
                assert mock_session_state.form_data['title'] == 'Valid Title'
                assert mock_session_state.form_data['assignee'] == 'John Doe'
                assert mock_session_state.form_data['priority'] == Priority.MEDIUM.value

    @pytest.mark.parametrize("exception_class, exception_message, expected_error_prefix", [
        (
            "InvalidStatusError",
            "Invalid status 'Invalid'. Must be one of: ['To Do', 'In Progress', 'Done']",
            "Invalid status:"
        ),
        (
            "PastDueDateError",
            "Due date 2023-01-01 cannot be in the past. Current date: 2024-01-01",
            "Invalid due date:"
        )
    ])
    def test_form_submission_handles_backend_errors(self, exception_class, exception_message, expected_error_prefix):
        """Test that form submission handles backend errors correctly and preserves form data."""
        mock_session_state = MockSessionState()
        mock_db_session = MagicMock()
        
        # Set up valid form_data (no client-side validation errors)
        future_date = date.today() + timedelta(days=7)
        original_form_data = {
            'title': 'Valid Task Title',
            'status': Status.TODO.value,
            'assignee': 'John Doe',
            'due_date': future_date,
            'description': 'Task description',
            'priority': Priority.HIGH.value,
            'labels': ['Feature', 'Bug'],
            'estimated_time': 4.0
        }
        mock_session_state.form_data = original_form_data.copy()
        mock_session_state.form_errors = {}
        
        with patch('streamlit.text_input', side_effect=["Valid Task Title", "John Doe", "Task description"]), \
             patch('streamlit.date_input', return_value=future_date), \
             patch('streamlit.selectbox', side_effect=[Priority.HIGH.value, Status.TODO.value, 4.0]), \
             patch('streamlit.multiselect', return_value=['Feature', 'Bug']), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.rerun') as mock_rerun, \
             patch('logging.getLogger'):
            
            # Mock backend services
            with patch('kb_web_svc.components.task_form.create_task') as mock_create_task, \
                 patch('kb_web_svc.components.task_form.add_task_to_session') as mock_add_task:
                
                # Import the specific exception class dynamically
                from kb_web_svc.services.task_service import InvalidStatusError, PastDueDateError
                exception_map = {
                    "InvalidStatusError": InvalidStatusError,
                    "PastDueDateError": PastDueDateError
                }
                
                # Mock create_task to raise the parametrized exception
                mock_create_task.side_effect = exception_map[exception_class](exception_message)
                
                # Import and call the function
                from kb_web_svc.components.task_form import render_task_form
                render_task_form(mock_db_session)
                
                # Verify that error is displayed with correct prefix
                expected_full_message = f"{expected_error_prefix} {exception_message}"
                mock_error.assert_any_call(expected_full_message)
                
                # Verify add_task_to_session is not called
                mock_add_task.assert_not_called()
                
                # Verify st.rerun is not called
                mock_rerun.assert_not_called()
                
                # Verify success message is not shown
                mock_success.assert_not_called()
                
                # Verify form_data is NOT reset (unchanged from initial values)
                assert mock_session_state.form_data == original_form_data
                assert mock_session_state.form_data['title'] == 'Valid Task Title'
                assert mock_session_state.form_data['assignee'] == 'John Doe'
                assert mock_session_state.form_data['due_date'] == future_date
                assert mock_session_state.form_data['description'] == 'Task description'
                assert mock_session_state.form_data['priority'] == Priority.HIGH.value
                assert mock_session_state.form_data['labels'] == ['Feature', 'Bug']
                assert mock_session_state.form_data['estimated_time'] == 4.0
                assert mock_session_state.form_data['status'] == Status.TODO.value

    def test_form_submission_succeeds_with_valid_data(self):
        """Test that form submission succeeds when all required fields are valid."""
        mock_session_state = MockSessionState()
        future_date = date.today() + timedelta(days=7)
        mock_session_state.form_data = {
            'title': 'Valid Task Title',
            'status': Status.TODO.value,
            'assignee': 'John Doe',
            'due_date': future_date,
            'description': 'Task description',
            'priority': Priority.MEDIUM.value,
            'labels': ['Feature'],
            'estimated_time': 2.5
        }
        mock_session_state.form_errors = {}
        mock_db_session = MagicMock()
        
        with patch('streamlit.text_input', return_value="Valid Task Title"), \
             patch('streamlit.date_input', return_value=future_date), \
             patch('streamlit.selectbox', side_effect=[Priority.MEDIUM.value, Status.TODO.value, 2.5]), \
             patch('streamlit.multiselect', return_value=['Feature']), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.rerun') as mock_rerun, \
             patch('logging.getLogger'):
            
            # Mock backend services for successful task creation
            with patch('kb_web_svc.components.task_form.create_task') as mock_create_task, \
                 patch('kb_web_svc.components.task_form.add_task_to_session') as mock_add_task:
                
                # Mock successful task creation
                mock_create_task.return_value = {"id": "test-uuid", "title": "Valid Task Title", "status": "To Do"}
                
                # Import and call the function
                from kb_web_svc.components.task_form import render_task_form
                render_task_form(mock_db_session)
                
                # Verify that success message is displayed with backend integration
                mock_success.assert_called_with("Task created successfully!")
                
                # Verify backend create_task was called
                mock_create_task.assert_called_once()
                mock_add_task.assert_called_once_with({"id": "test-uuid", "title": "Valid Task Title", "status": "To Do"})
                mock_rerun.assert_called_once()
                
                # Verify no validation errors are displayed for submission
                # Should not call error with the submission blocking message
                error_calls = [call[0][0] for call in mock_error.call_args_list if mock_error.call_args_list]
                assert "Please correct the errors before submitting." not in error_calls
