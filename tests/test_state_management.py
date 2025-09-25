"""Unit tests for state management module.

These tests verify session state initialization, task loading from database,
and proper error handling using mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Status
from kb_web_svc.schemas.task import TaskFilterParams
from kb_web_svc.state_management import initialize_session_state, load_tasks_from_db_to_session


class TestInitializeSessionState:
    """Test cases for the initialize_session_state function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock streamlit session state
        self.mock_session_state = MagicMock()
        self.mock_session_state.get.return_value = False  # Not initialized by default
        
    def test_initialize_session_state_first_run_sets_defaults(self, monkeypatch):
        """Test that first run initializes all required session state keys."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock get_db to avoid database calls during initialization
        mock_get_db = MagicMock()
        mock_db_gen = MagicMock()
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db_gen
        mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
        
        monkeypatch.setattr('kb_web_svc.state_management.get_db', mock_get_db)
        
        # Mock load_tasks_from_db_to_session to avoid actual database calls
        mock_load_tasks = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.load_tasks_from_db_to_session', mock_load_tasks)
        
        # Call the function
        initialize_session_state()
        
        # Verify initialization flag is set
        assert mock_st.session_state.initialized == True
        
        # Verify tasks_by_status is initialized with correct structure
        expected_tasks_by_status = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        assert mock_st.session_state.tasks_by_status == expected_tasks_by_status
        
        # Verify form_states and ui_states are initialized as empty dicts
        assert mock_st.session_state.form_states == {}
        assert mock_st.session_state.ui_states == {}
        
        # Verify load_tasks_from_db_to_session was called
        mock_load_tasks.assert_called_once_with(mock_db)

    def test_initialize_session_state_idempotent(self, monkeypatch):
        """Test that subsequent calls do not re-initialize if already done."""
        # Mock streamlit with already initialized state
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        mock_st.session_state.get.return_value = True  # Already initialized
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock get_db and load_tasks - they should not be called
        mock_get_db = MagicMock()
        mock_load_tasks = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.get_db', mock_get_db)
        monkeypatch.setattr('kb_web_svc.state_management.load_tasks_from_db_to_session', mock_load_tasks)
        
        # Call the function
        initialize_session_state()
        
        # Verify get_db and load_tasks were not called
        mock_get_db.assert_not_called()
        mock_load_tasks.assert_not_called()
        
        # The key point is that the function should return early and not perform any setup
        # We verify this by checking that the initialization logic was not executed
        # (i.e., the session_state attributes were not assigned new values)
        
        # Since the function returns early, these assignments should not happen
        # We can't easily check hasattr due to MagicMock behavior, but we can verify
        # that the expected database operations didn't occur (which we already did above)

    def test_initialize_session_state_with_existing_tasks_skips_load(self, monkeypatch):
        """Test that initialization skips loading if tasks already exist in session."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        
        # Setup session state with existing tasks
        mock_st.session_state.tasks_by_status = {
            Status.TODO.value: [{"id": "1", "title": "existing task"}],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock get_db and load_tasks - they should not be called since tasks exist
        mock_get_db = MagicMock()
        mock_load_tasks = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.get_db', mock_get_db)
        monkeypatch.setattr('kb_web_svc.state_management.load_tasks_from_db_to_session', mock_load_tasks)
        
        # Call the function
        initialize_session_state()
        
        # Verify initialization flag is set
        assert mock_st.session_state.initialized == True
        
        # Verify core structures are initialized
        assert mock_st.session_state.form_states == {}
        assert mock_st.session_state.ui_states == {}
        
        # Verify get_db and load_tasks were not called since tasks already exist
        mock_get_db.assert_not_called()
        mock_load_tasks.assert_not_called()

    def test_initialize_session_state_handles_database_error(self, monkeypatch):
        """Test that database errors during initialization are handled gracefully."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock get_db to raise an exception
        mock_get_db = MagicMock()
        mock_get_db.side_effect = Exception("Database connection failed")
        monkeypatch.setattr('kb_web_svc.state_management.get_db', mock_get_db)
        
        # Mock logging
        mock_logger = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.logger', mock_logger)
        
        # Call the function - should not raise exception
        initialize_session_state()
        
        # Verify initialization still completes
        assert mock_st.session_state.initialized == True
        assert mock_st.session_state.form_states == {}
        assert mock_st.session_state.ui_states == {}
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call_args = mock_logger.error.call_args[0]
        assert "Failed to load tasks from database" in error_call_args[0]

    def test_initialize_session_state_handles_load_tasks_error(self, monkeypatch):
        """Test that errors from load_tasks_from_db_to_session are handled gracefully."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock get_db to return a valid session
        mock_get_db = MagicMock()
        mock_db_gen = MagicMock()
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db_gen
        mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
        monkeypatch.setattr('kb_web_svc.state_management.get_db', mock_get_db)
        
        # Mock load_tasks_from_db_to_session to raise an exception
        mock_load_tasks = MagicMock()
        mock_load_tasks.side_effect = Exception("Task loading failed")
        monkeypatch.setattr('kb_web_svc.state_management.load_tasks_from_db_to_session', mock_load_tasks)
        
        # Mock logging
        mock_logger = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.logger', mock_logger)
        
        # Call the function - should not raise exception
        initialize_session_state()
        
        # Verify initialization still completes
        assert mock_st.session_state.initialized == True
        assert mock_st.session_state.form_states == {}
        assert mock_st.session_state.ui_states == {}
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call_args = mock_logger.error.call_args[0]
        assert "Failed to load tasks from database" in error_call_args[0]


class TestLoadTasksFromDbToSession:
    """Test cases for the load_tasks_from_db_to_session function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock streamlit session state
        self.mock_session_state = MagicMock()
        self.mock_db = MagicMock(spec=Session)

    def test_load_tasks_from_db_populates_tasks_by_status(self, monkeypatch):
        """Test that tasks are correctly categorized by status and deleted tasks are filtered."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock task data with mix of statuses and deleted/active tasks
        mock_tasks = [
            {"id": "1", "title": "Todo Task 1", "status": "To Do", "deleted_at": None},
            {"id": "2", "title": "Todo Task 2", "status": "To Do", "deleted_at": None},
            {"id": "3", "title": "In Progress Task", "status": "In Progress", "deleted_at": None},
            {"id": "4", "title": "Done Task", "status": "Done", "deleted_at": None},
            {"id": "5", "title": "Deleted Task", "status": "To Do", "deleted_at": "2024-01-01T00:00:00Z"},
            {"id": "6", "title": "Unknown Status", "status": "Invalid", "deleted_at": None}
        ]
        
        # Mock list_tasks service
        mock_list_tasks = MagicMock()
        mock_list_tasks.return_value = (mock_tasks, len(mock_tasks))
        monkeypatch.setattr('kb_web_svc.state_management.list_tasks', mock_list_tasks)
        
        # Mock logging to verify warning for unknown status
        mock_logger = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.logger', mock_logger)
        
        # Call the function
        load_tasks_from_db_to_session(self.mock_db)
        
        # Verify list_tasks was called with correct parameters
        expected_filters = TaskFilterParams(limit=10000, offset=0)
        mock_list_tasks.assert_called_once_with(self.mock_db, expected_filters)
        
        # Verify tasks_by_status is properly populated
        expected_tasks_by_status = {
            Status.TODO.value: [
                {"id": "1", "title": "Todo Task 1", "status": "To Do", "deleted_at": None},
                {"id": "2", "title": "Todo Task 2", "status": "To Do", "deleted_at": None}
            ],
            Status.IN_PROGRESS.value: [
                {"id": "3", "title": "In Progress Task", "status": "In Progress", "deleted_at": None}
            ],
            Status.DONE.value: [
                {"id": "4", "title": "Done Task", "status": "Done", "deleted_at": None}
            ]
        }
        assert mock_st.session_state.tasks_by_status == expected_tasks_by_status
        
        # Verify warning was logged for unknown status
        mock_logger.warning.assert_called_once()
        warning_call_args = mock_logger.warning.call_args[0]
        assert "unknown status" in warning_call_args[0]
        assert "Invalid" in warning_call_args[0]

    def test_load_tasks_from_db_with_empty_result(self, monkeypatch):
        """Test handling when no tasks are returned from database."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock empty task list
        mock_list_tasks = MagicMock()
        mock_list_tasks.return_value = ([], 0)
        monkeypatch.setattr('kb_web_svc.state_management.list_tasks', mock_list_tasks)
        
        # Call the function
        load_tasks_from_db_to_session(self.mock_db)
        
        # Verify empty tasks_by_status structure
        expected_tasks_by_status = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        assert mock_st.session_state.tasks_by_status == expected_tasks_by_status

    def test_load_tasks_from_db_only_deleted_tasks(self, monkeypatch):
        """Test filtering when all tasks are deleted."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock task data with only deleted tasks
        mock_tasks = [
            {"id": "1", "title": "Deleted Task 1", "status": "To Do", "deleted_at": "2024-01-01T00:00:00Z"},
            {"id": "2", "title": "Deleted Task 2", "status": "In Progress", "deleted_at": "2024-01-02T00:00:00Z"}
        ]
        
        # Mock list_tasks service
        mock_list_tasks = MagicMock()
        mock_list_tasks.return_value = (mock_tasks, len(mock_tasks))
        monkeypatch.setattr('kb_web_svc.state_management.list_tasks', mock_list_tasks)
        
        # Call the function
        load_tasks_from_db_to_session(self.mock_db)
        
        # Verify empty tasks_by_status structure (all tasks were deleted)
        expected_tasks_by_status = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        assert mock_st.session_state.tasks_by_status == expected_tasks_by_status

    def test_load_tasks_handles_service_exception(self, monkeypatch):
        """Test that service exceptions are logged and session state is cleared."""
        # Mock streamlit
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock list_tasks to raise an exception
        mock_list_tasks = MagicMock()
        mock_list_tasks.side_effect = Exception("Database query failed")
        monkeypatch.setattr('kb_web_svc.state_management.list_tasks', mock_list_tasks)
        
        # Mock logging
        mock_logger = MagicMock()
        monkeypatch.setattr('kb_web_svc.state_management.logger', mock_logger)
        
        # Call the function - should raise exception
        with pytest.raises(Exception, match="Database query failed"):
            load_tasks_from_db_to_session(self.mock_db)
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call_args = mock_logger.error.call_args[0]
        assert "Error loading tasks from database" in error_call_args[0]
        
        # Verify session state was cleared on error
        expected_cleared_state = {
            Status.TODO.value: [],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: []
        }
        assert mock_st.session_state.tasks_by_status == expected_cleared_state

    def test_load_tasks_clears_existing_session_tasks(self, monkeypatch):
        """Test that existing session state tasks are cleared before loading new ones."""
        # Mock streamlit with existing tasks
        mock_st = MagicMock()
        mock_st.session_state = self.mock_session_state
        mock_st.session_state.tasks_by_status = {
            Status.TODO.value: [{"id": "existing", "title": "Existing Task"}],
            Status.IN_PROGRESS.value: [{"id": "existing2", "title": "Another Existing Task"}],
            Status.DONE.value: []
        }
        monkeypatch.setattr('kb_web_svc.state_management.st', mock_st)
        
        # Mock new task data
        mock_tasks = [
            {"id": "new1", "title": "New Task 1", "status": "To Do", "deleted_at": None},
            {"id": "new2", "title": "New Task 2", "status": "Done", "deleted_at": None}
        ]
        
        # Mock list_tasks service
        mock_list_tasks = MagicMock()
        mock_list_tasks.return_value = (mock_tasks, len(mock_tasks))
        monkeypatch.setattr('kb_web_svc.state_management.list_tasks', mock_list_tasks)
        
        # Call the function
        load_tasks_from_db_to_session(self.mock_db)
        
        # Verify existing tasks were cleared and new tasks loaded
        expected_tasks_by_status = {
            Status.TODO.value: [
                {"id": "new1", "title": "New Task 1", "status": "To Do", "deleted_at": None}
            ],
            Status.IN_PROGRESS.value: [],
            Status.DONE.value: [
                {"id": "new2", "title": "New Task 2", "status": "Done", "deleted_at": None}
            ]
        }
        assert mock_st.session_state.tasks_by_status == expected_tasks_by_status
        
        # Verify the existing tasks are no longer present
        all_tasks = (mock_st.session_state.tasks_by_status[Status.TODO.value] +
                     mock_st.session_state.tasks_by_status[Status.IN_PROGRESS.value] +
                     mock_st.session_state.tasks_by_status[Status.DONE.value])
        task_ids = [task["id"] for task in all_tasks]
        assert "existing" not in task_ids
        assert "existing2" not in task_ids
        assert "new1" in task_ids
        assert "new2" in task_ids
