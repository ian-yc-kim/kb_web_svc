"""Unit tests for the kanban board UI component.

These tests verify the kanban board rendering, column layout, task organization,
and error handling using mocked Streamlit components and dependencies.
"""

import sys
from unittest.mock import MagicMock, patch, call

import pytest


class TestKanbanBoard:
    """Test cases for kanban board UI component."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Remove any previously imported modules to ensure clean state
        modules_to_remove = [
            'kb_web_svc.components.kanban_board',
            'kb_web_svc.components'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def test_render_kanban_board_creates_three_columns(self):
        """Test that render_kanban_board creates exactly three columns."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status', return_value=[]), \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify st.columns was called with 3
            mock_columns.assert_called_once_with(3)

    def test_render_kanban_board_headers_reflect_correct_counts(self):
        """Test that column headers display correct task counts for each status."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status') as mock_get_tasks, \
             patch('kb_web_svc.components.task_card.render_task_card'), \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Setup different task counts for each status
            def mock_get_tasks_side_effect(status_value):
                if status_value == "To Do":
                    return [{"id": "1", "title": "Task 1"}, {"id": "2", "title": "Task 2"}]  # 2 tasks
                elif status_value == "In Progress":
                    return [{"id": "3", "title": "Task 3"}]  # 1 task
                elif status_value == "Done":
                    return []  # 0 tasks
                return []
            
            mock_get_tasks.side_effect = mock_get_tasks_side_effect
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify subheaders are called with correct counts
            expected_calls = [
                call("To Do (2)"),
                call("In Progress (1)"),
                call("Done (0)")
            ]
            mock_subheader.assert_has_calls(expected_calls)

    def test_render_kanban_board_tasks_rendered_in_correct_columns(self):
        """Test that tasks are rendered in their respective status columns."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status') as mock_get_tasks, \
             patch('kb_web_svc.components.task_card.render_task_card') as mock_render_card, \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Setup distinct tasks for each status
            todo_tasks = [{"id": "1", "title": "Todo Task 1"}, {"id": "2", "title": "Todo Task 2"}]
            progress_tasks = [{"id": "3", "title": "Progress Task 1"}]
            done_tasks = [{"id": "4", "title": "Done Task 1"}]
            
            def mock_get_tasks_side_effect(status_value):
                if status_value == "To Do":
                    return todo_tasks
                elif status_value == "In Progress":
                    return progress_tasks
                elif status_value == "Done":
                    return done_tasks
                return []
            
            mock_get_tasks.side_effect = mock_get_tasks_side_effect
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify render_task_card was called for each task
            expected_calls = [
                call(todo_tasks[0]),
                call(todo_tasks[1]),
                call(progress_tasks[0]),
                call(done_tasks[0])
            ]
            mock_render_card.assert_has_calls(expected_calls, any_order=False)
            
            # Verify total number of render_task_card calls
            assert mock_render_card.call_count == 4

    def test_render_kanban_board_with_empty_task_lists(self):
        """Test that empty task lists are handled correctly for all statuses."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status', return_value=[]), \
             patch('kb_web_svc.components.task_card.render_task_card') as mock_render_card, \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify all subheaders show (0) count
            expected_calls = [
                call("To Do (0)"),
                call("In Progress (0)"),
                call("Done (0)")
            ]
            mock_subheader.assert_has_calls(expected_calls)
            
            # Verify render_task_card was not called since no tasks
            mock_render_card.assert_not_called()

    def test_render_kanban_board_handles_task_render_error(self):
        """Test that errors from individual task rendering are handled gracefully."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status') as mock_get_tasks, \
             patch('kb_web_svc.components.task_card.render_task_card') as mock_render_card, \
             patch('logging.getLogger') as mock_get_logger:
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Setup tasks where one will fail to render
            todo_tasks = [
                {"id": "1", "title": "Good Task"},
                {"id": "2", "title": "Bad Task"},
                {"id": "3", "title": "Another Good Task"}
            ]
            
            def mock_get_tasks_side_effect(status_value):
                if status_value == "To Do":
                    return todo_tasks
                return []
            
            mock_get_tasks.side_effect = mock_get_tasks_side_effect
            
            # Make render_task_card raise exception for the second task
            def render_card_side_effect(task):
                if task["id"] == "2":
                    raise Exception("Task render failed")
                return None
            
            mock_render_card.side_effect = render_card_side_effect
            
            # Import and call the function - should not raise exception
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify all three tasks were attempted to be rendered
            assert mock_render_card.call_count == 3
            
            # Verify error was logged for the failed task
            mock_logger.error.assert_called()
            error_args = mock_logger.error.call_args[0]
            assert "Error rendering task card for task 2:" in error_args[0]
            
            # Verify the function completed successfully (logged success)
            info_calls = mock_logger.info.call_args_list
            success_logged = any("Kanban board rendered successfully" in str(call) for call in info_calls)
            assert success_logged

    def test_render_kanban_board_handles_get_tasks_error(self):
        """Test that errors from get_tasks_by_status are handled gracefully."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown'), \
             patch('streamlit.error') as mock_st_error, \
             patch('kb_web_svc.state_management.get_tasks_by_status') as mock_get_tasks, \
             patch('kb_web_svc.components.task_card.render_task_card'), \
             patch('logging.getLogger') as mock_get_logger:
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Make get_tasks_by_status raise exception for "To Do" status only
            def mock_get_tasks_side_effect(status_value):
                if status_value == "To Do":
                    raise Exception("Database error")
                return []  # Other statuses return empty list
            
            mock_get_tasks.side_effect = mock_get_tasks_side_effect
            
            # Import and call the function - should not raise exception
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify error was logged for the failed column
            mock_logger.error.assert_called()
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "Error rendering column for status To Do:" in str(call)]
            assert len(error_calls) >= 1
            
            # Verify error message was displayed in Streamlit for the failed column
            mock_st_error.assert_called_with("Error loading To Do tasks")

    def test_render_kanban_board_handles_complete_failure(self):
        """Test that complete failures are handled gracefully with fallback error message."""
        with patch('streamlit.columns', side_effect=Exception("Complete failure")) as mock_columns, \
             patch('streamlit.error') as mock_st_error, \
             patch('logging.getLogger') as mock_get_logger:
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Import and call the function - should not raise exception
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify columns creation was attempted
            mock_columns.assert_called_once_with(3)
            
            # Verify error was logged
            mock_logger.error.assert_called()
            error_args = mock_logger.error.call_args[0]
            assert "Error rendering kanban board:" in error_args[0]
            
            # Verify fallback error message was displayed
            mock_st_error.assert_called_once_with(
                "An error occurred while loading the kanban board. Please refresh the page."
            )

    def test_render_kanban_board_visual_separation_added(self):
        """Test that visual separation is added to each column."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown') as mock_markdown, \
             patch('kb_web_svc.state_management.get_tasks_by_status', return_value=[]), \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify markdown horizontal rule is called three times (once per column)
            expected_calls = [call("---"), call("---"), call("---")]
            mock_markdown.assert_has_calls(expected_calls)
            assert mock_markdown.call_count == 3

    def test_render_kanban_board_uses_status_enum_values(self):
        """Test that the function uses Status enum values correctly."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status') as mock_get_tasks, \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Setup mock to track which status values are requested
            mock_get_tasks.return_value = []
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify get_tasks_by_status was called with correct Status enum values
            expected_calls = [
                call("To Do"),
                call("In Progress"),
                call("Done")
            ]
            mock_get_tasks.assert_has_calls(expected_calls)
            
            # Verify subheaders use the correct Status enum values
            expected_subheader_calls = [
                call("To Do (0)"),
                call("In Progress (0)"),
                call("Done (0)")
            ]
            mock_subheader.assert_has_calls(expected_subheader_calls)

    def test_render_kanban_board_handles_none_tasks_return(self):
        """Test that None return from get_tasks_by_status is handled correctly."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status', return_value=None), \
             patch('kb_web_svc.components.task_card.render_task_card') as mock_render_card, \
             patch('logging.getLogger'):
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify all subheaders show (0) count (None treated as empty)
            expected_calls = [
                call("To Do (0)"),
                call("In Progress (0)"),
                call("Done (0)")
            ]
            mock_subheader.assert_has_calls(expected_calls)
            
            # Verify render_task_card was not called since None/empty tasks
            mock_render_card.assert_not_called()

    def test_render_kanban_board_logging_behavior(self):
        """Test that appropriate logging occurs during normal operation."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.subheader'), \
             patch('streamlit.markdown'), \
             patch('kb_web_svc.state_management.get_tasks_by_status', return_value=[]), \
             patch('logging.getLogger') as mock_get_logger:
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Mock columns to return three context managers
            col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2, col3]
            
            # Import and call the function
            from kb_web_svc.components.kanban_board import render_kanban_board
            render_kanban_board()
            
            # Verify appropriate info logging occurred
            info_calls = mock_logger.info.call_args_list
            
            # Should have start and success logging
            start_logged = any("Rendering kanban board" in str(call) for call in info_calls)
            success_logged = any("Kanban board rendered successfully" in str(call) for call in info_calls)
            
            assert start_logged, "Should log start of rendering"
            assert success_logged, "Should log successful completion"
