"""Unit tests for app.py module.

These tests verify the integration of session state initialization and task loading
into the Streamlit application using mocking for isolation.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch, call

import pytest


class TestApp:
    """Test cases for app.py module functionality."""

    def setup_method(self):
        """Reset module state before each test."""
        # Remove the app module from sys.modules if it exists
        if 'kb_web_svc.app' in sys.modules:
            del sys.modules['kb_web_svc.app']

    def test_initialize_session_state_called_on_app_load(self):
        """Test that initialize_session_state is called when app.py is loaded."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state') as mock_init, \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session') as mock_load_tasks, \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify initialize_session_state was called once
                mock_init.assert_called_once()

    def test_load_tasks_from_db_to_session_called_on_app_load(self):
        """Test that load_tasks_from_db_to_session is called with db session on app load."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session') as mock_load_tasks, \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify get_db was called
                mock_get_db.assert_called_once()
                
                # Verify load_tasks_from_db_to_session was called with the mock db session
                mock_load_tasks.assert_called_once_with(mock_db)

    def test_session_state_tasks_by_status_displayed(self):
        """Test that the task creation form is displayed instead of tasks_by_status JSON."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title') as mock_title, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.json') as mock_json, \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session'), \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form') as mock_render_task_form:
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify UI components were called correctly
                mock_title.assert_called_once_with("Kanban Board")
                
                # Verify only Create Task subheader is called (board state display removed)
                mock_subheader.assert_called_once_with("Create Task")
                
                # Verify JSON display is no longer called (replaced with task form)
                mock_json.assert_not_called()
                
                # Verify task form is rendered with database session
                mock_render_task_form.assert_called_once_with(mock_db)

    def test_no_database_connection_test_button(self):
        """Test that the app no longer contains database connection test button."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('streamlit.button') as mock_button, \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session'), \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify that no button was called (no database connection test button)
                mock_button.assert_not_called()

    def test_render_db_connection_check_function_removed(self):
        """Test that render_db_connection_check function no longer exists."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session'), \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify that render_db_connection_check function does not exist
                assert not hasattr(kb_web_svc.app, 'render_db_connection_check')

    def test_database_error_handled_gracefully(self):
        """Test that database errors during app load are handled gracefully."""
        test_exception = Exception("Database connection failed")
        
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db', side_effect=test_exception) as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session') as mock_load_tasks, \
             patch('logging.getLogger') as mock_get_logger, \
             patch('kb_web_svc.components.task_form.render_task_form'), \
             patch('streamlit.error'):
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify get_db was called
                mock_get_db.assert_called_once()
                
                # Verify load_tasks was not called due to database error
                mock_load_tasks.assert_not_called()
                
                # Verify error was logged
                mock_logger.error.assert_called_once_with(test_exception, exc_info=True)

    def test_load_tasks_error_handled_gracefully(self):
        """Test that errors from load_tasks_from_db_to_session are handled gracefully."""
        test_exception = Exception("Task loading failed")
        
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session', side_effect=test_exception) as mock_load_tasks, \
             patch('logging.getLogger') as mock_get_logger, \
             patch('kb_web_svc.components.task_form.render_task_form'), \
             patch('streamlit.error'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify get_db was called
                mock_get_db.assert_called_once()
                
                # Verify load_tasks was called and raised exception
                mock_load_tasks.assert_called_once_with(mock_db)
                
                # Verify error was logged
                mock_logger.error.assert_called_once_with(test_exception, exc_info=True)

    def test_render_ui_function_exists_and_callable(self):
        """Test that render_ui function exists and is callable after import."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session'), \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify that render_ui function exists and is callable
                assert hasattr(kb_web_svc.app, 'render_ui')
                assert callable(kb_web_svc.app.render_ui)

    def test_database_cleanup_on_success(self):
        """Test that database generator is properly cleaned up on successful execution."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session'), \
             patch('logging.getLogger'), \
             patch('kb_web_svc.components.task_form.render_task_form'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            # First call returns db, second call raises StopIteration for cleanup
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify get_db generator was called twice (once for db, once for cleanup)
                assert mock_db_gen.__next__.call_count == 2

    def test_database_cleanup_on_error(self):
        """Test that database generator is properly cleaned up even when task loading fails."""
        test_exception = Exception("Task loading failed")
        
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.subheader'), \
             patch('streamlit.json'), \
             patch('kb_web_svc.state_management.initialize_session_state'), \
             patch('kb_web_svc.database.get_db') as mock_get_db, \
             patch('kb_web_svc.state_management.load_tasks_from_db_to_session', side_effect=test_exception), \
             patch('logging.getLogger') as mock_get_logger, \
             patch('kb_web_svc.components.task_form.render_task_form'), \
             patch('streamlit.error'):
            
            # Setup get_db to return a generator that yields a mock db session
            mock_db = MagicMock()
            mock_db_gen = MagicMock()
            # First call returns db, second call raises StopIteration for cleanup
            mock_db_gen.__next__ = MagicMock(side_effect=[mock_db, StopIteration()])
            mock_get_db.return_value = mock_db_gen
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Mock streamlit session state directly
            mock_session_state = MagicMock()
            mock_session_state.tasks_by_status = {"To Do": [], "In Progress": [], "Done": []}
            
            with patch('streamlit.session_state', mock_session_state):
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Verify get_db generator was called twice (once for db, once for cleanup)
                assert mock_db_gen.__next__.call_count == 2
                
                # Verify error was logged
                mock_logger.error.assert_called_once_with(test_exception, exc_info=True)
