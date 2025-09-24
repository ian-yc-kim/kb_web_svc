"""Unit tests for app.py module.

These tests verify the integration of database connection checking
into the Streamlit application using mocking for isolation.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestApp:
    """Test cases for app.py module functionality."""

    def setup_method(self):
        """Reset module state before each test."""
        # Remove the app module from sys.modules if it exists
        if 'kb_web_svc.app' in sys.modules:
            del sys.modules['kb_web_svc.app']

    def test_app_imports_check_db_connection(self):
        """Test that app.py successfully imports check_db_connection."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.button'), \
             patch('streamlit.success'), \
             patch('streamlit.error'):
            
            # Import the app module under patched Streamlit environment
            import kb_web_svc.app
            
            # Verify that check_db_connection is accessible in the module
            assert hasattr(kb_web_svc.app, 'check_db_connection')
            assert callable(kb_web_svc.app.check_db_connection)

    def test_button_click_calls_check_db_connection_and_shows_success(self):
        """Test button click calls check_db_connection and shows success message."""
        # Patch all streamlit functions before importing
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title') as mock_title, \
             patch('streamlit.button', return_value=True) as mock_button, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('kb_web_svc.database.check_db_connection', return_value=True) as mock_check_db:
            
            # Import the app module after all patches are in place
            import kb_web_svc.app
            
            # Since render_ui() was already called on import with button returning True,
            # we should verify the expected calls were made
            mock_check_db.assert_called_once()
            mock_success.assert_called_once_with("Database connection successful!")
            mock_error.assert_not_called()

    def test_button_click_calls_check_db_connection_and_shows_error(self):
        """Test button click calls check_db_connection and shows error message on failure."""
        # Patch all streamlit functions before importing
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title') as mock_title, \
             patch('streamlit.button', return_value=True) as mock_button, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('kb_web_svc.database.check_db_connection', return_value=False) as mock_check_db:
            
            # Import the app module after all patches are in place
            import kb_web_svc.app
            
            # Since render_ui() was already called on import with button returning True,
            # we should verify the expected calls were made
            mock_check_db.assert_called_once()
            mock_error.assert_called_once_with("Database connection failed!")
            mock_success.assert_not_called()

    def test_no_click_does_not_call_check_or_show_messages(self):
        """Test that no button click doesn't trigger database check or messages."""
        # Patch all streamlit functions before importing
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title') as mock_title, \
             patch('streamlit.button', return_value=False) as mock_button, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('kb_web_svc.database.check_db_connection') as mock_check_db:
            
            # Import the app module after all patches are in place
            import kb_web_svc.app
            
            # Since render_ui() was called on import but button returned False,
            # verify no database calls or messages were made
            mock_check_db.assert_not_called()
            mock_success.assert_not_called()
            mock_error.assert_not_called()

    def test_exception_from_check_shows_error_and_logs(self):
        """Test that exception from check_db_connection shows error message."""
        test_exception = Exception("Database connection error")
        
        # Patch all streamlit functions and logging before importing
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title') as mock_title, \
             patch('streamlit.button', return_value=True) as mock_button, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('kb_web_svc.database.check_db_connection', side_effect=test_exception) as mock_check_db:
            
            # Patch logging.error directly from logging module
            with patch('logging.error') as mock_logging_error:
                # Import the app module after all patches are in place
                import kb_web_svc.app
                
                # Since render_ui() was called on import with button returning True,
                # and check_db_connection raised an exception, verify expected calls
                mock_check_db.assert_called_once()
                mock_error.assert_called_once_with("Database connection failed!")
                mock_success.assert_not_called()
                mock_logging_error.assert_called_once_with(test_exception, exc_info=True)

    def test_render_ui_function_exists_and_callable(self):
        """Test that render_ui function exists and is callable after import."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.button'), \
             patch('streamlit.success'), \
             patch('streamlit.error'):
            
            # Import the app module under patched Streamlit environment
            import kb_web_svc.app
            
            # Verify that render_ui function exists and is callable
            assert hasattr(kb_web_svc.app, 'render_ui')
            assert callable(kb_web_svc.app.render_ui)