"""Unit tests for the task card UI component.

These tests verify the task card rendering, field display,
and error handling using mocked Streamlit components.
"""

import sys
from unittest.mock import MagicMock, patch, call
from datetime import date

import pytest


class TestTaskCard:
    """Test cases for task card UI component."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Remove any previously imported modules to ensure clean state
        modules_to_remove = [
            'kb_web_svc.components.task_card',
            'kb_web_svc.components'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def test_render_task_card_full_task_dictionary(self):
        """Test that render_task_card correctly displays all fields with a full task dictionary."""
        # Create a full task dictionary with all fields
        full_task = {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'title': 'Implement Feature X',
            'assignee': 'John Doe',
            'due_date': '2024-12-31',
            'priority': 'High',
            'status': 'In Progress',
            'description': 'This is a detailed description of the task.',
            'labels': ['Feature', 'Backend'],
            'estimated_time': 4.5,
            'created_at': '2024-01-15T10:30:00Z',
            'last_modified': '2024-01-16T14:20:00Z'
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.code') as mock_code, \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(full_task)
            
            # Verify expander is called with header containing title and status
            expected_header = "**Implement Feature X** • `In Progress`"
            mock_expander.assert_called_once_with(expected_header, expanded=False)
            
            # Verify task title is displayed prominently inside expander
            mock_markdown.assert_any_call("### Implement Feature X")
            
            # Verify columns are created for layout
            mock_columns.assert_called_once_with(2)
            
            # Verify all captions are displayed
            expected_captions = [
                "**Assignee**", "**Priority**", "**Labels**",
                "**Due Date**", "**Status**", "**Estimated Time**",
                "**Description**", "**Task ID**"
            ]
            for caption in expected_captions:
                mock_caption.assert_any_call(caption)
            
            # Verify field values are written
            mock_write.assert_any_call("John Doe")  # assignee
            mock_write.assert_any_call("2024-12-31")  # due_date
            mock_write.assert_any_call("Feature, Backend")  # labels
            mock_write.assert_any_call("4.5 hours")  # estimated_time
            
            # Verify styled priority and status with HTML
            mock_markdown.assert_any_call('<span style="color: orange;">🟠 High</span>', unsafe_allow_html=True)
            mock_markdown.assert_any_call('<span style="color: blue;">🔵 In Progress</span>', unsafe_allow_html=True)
            
            # Verify description is displayed as markdown
            mock_markdown.assert_any_call("This is a detailed description of the task.")
            
            # Verify task ID is displayed as code
            mock_code.assert_called_once_with('123e4567-e89b-12d3-a456-426614174000', language=None)

    def test_render_task_card_with_optional_fields_none(self):
        """Test that render_task_card handles missing/None optional fields correctly."""
        # Create task dictionary with some None/missing optional fields
        minimal_task = {
            'title': 'Minimal Task',
            'status': 'To Do',
            'assignee': None,
            'due_date': None,
            'priority': None,
            'description': None,
            'labels': None,
            'estimated_time': None
            # Missing: id, created_at, last_modified
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.write') as mock_write, \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(minimal_task)
            
            # Verify expander is called with header containing title and status
            expected_header = "**Minimal Task** • `To Do`"
            mock_expander.assert_called_once_with(expected_header, expanded=False)
            
            # Verify task title is displayed prominently
            mock_markdown.assert_any_call("### Minimal Task")
            
            # Verify placeholders ("—") are used for None/missing fields
            mock_write.assert_any_call("—")  # Should appear multiple times for different None fields
            
            # Count how many times "—" placeholder is written
            dash_calls = [call for call in mock_write.call_args_list if call[0][0] == "—"]
            # Should have dashes for: assignee, due_date, priority, labels, estimated_time, description
            assert len(dash_calls) >= 5
            
            # Verify styled status with HTML (To Do should be gray circle)
            mock_markdown.assert_any_call('<span style="color: gray;">⚪ To Do</span>', unsafe_allow_html=True)

    def test_render_task_card_with_empty_labels_list(self):
        """Test that render_task_card handles empty labels list correctly."""
        task_with_empty_labels = {
            'title': 'Task with Empty Labels',
            'status': 'Done',
            'labels': []  # Empty list
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.write') as mock_write, \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(task_with_empty_labels)
            
            # Verify expander is called
            mock_expander.assert_called_once()
            
            # Verify that empty labels are displayed as "—"
            # Find the labels write call by looking for the call that comes after "**Labels**" caption
            labels_caption_found = False
            for i, call_args in enumerate(mock_caption.call_args_list):
                if call_args[0][0] == "**Labels**":
                    labels_caption_found = True
                    break
            
            assert labels_caption_found, "Labels caption not found"
            # Should have a write call with "—" for empty labels
            mock_write.assert_any_call("—")

    def test_render_task_card_priority_styling(self):
        """Test that different priority values get correct styling."""
        priorities_and_styles = [
            ("Critical", '<span style="color: red;">🔴 Critical</span>'),
            ("High", '<span style="color: orange;">🟠 High</span>'),
            ("Medium", '<span style="color: blue;">🔵 Medium</span>'),
            ("Low", '<span style="color: green;">🟢 Low</span>')
        ]
        
        for priority, expected_html in priorities_and_styles:
            with patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.markdown') as mock_markdown, \
                 patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.caption'), \
                 patch('streamlit.write'), \
                 patch('logging.getLogger'):
                
                # Mock the expander context manager
                mock_context = MagicMock()
                mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
                mock_expander.return_value.__exit__ = MagicMock(return_value=False)
                
                # Mock columns
                col1, col2 = MagicMock(), MagicMock()
                mock_columns.return_value = [col1, col2]
                
                task = {
                    'title': f'Task with {priority} Priority',
                    'status': 'To Do',
                    'priority': priority
                }
                
                # Import and call the function
                from kb_web_svc.components.task_card import render_task_card
                render_task_card(task)
                
                # Verify the correct styled priority is displayed
                mock_markdown.assert_any_call(expected_html, unsafe_allow_html=True)

    def test_render_task_card_status_styling(self):
        """Test that different status values get correct styling."""
        statuses_and_styles = [
            ("To Do", '<span style="color: gray;">⚪ To Do</span>'),
            ("In Progress", '<span style="color: blue;">🔵 In Progress</span>'),
            ("Done", '<span style="color: green;">✅ Done</span>')
        ]
        
        for status, expected_html in statuses_and_styles:
            with patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.markdown') as mock_markdown, \
                 patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.caption'), \
                 patch('streamlit.write'), \
                 patch('logging.getLogger'):
                
                # Mock the expander context manager
                mock_context = MagicMock()
                mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
                mock_expander.return_value.__exit__ = MagicMock(return_value=False)
                
                # Mock columns
                col1, col2 = MagicMock(), MagicMock()
                mock_columns.return_value = [col1, col2]
                
                task = {
                    'title': f'Task with {status} Status',
                    'status': status
                }
                
                # Import and call the function
                from kb_web_svc.components.task_card import render_task_card
                render_task_card(task)
                
                # Verify the correct styled status is displayed
                mock_markdown.assert_any_call(expected_html, unsafe_allow_html=True)

    def test_render_task_card_expander_usage(self):
        """Test that st.expander is used and content is rendered within it."""
        task = {
            'title': 'Test Task',
            'status': 'To Do',
            'assignee': 'Test User'
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.write') as mock_write, \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(task)
            
            # Verify expander is called exactly once
            mock_expander.assert_called_once_with("**Test Task** • `To Do`", expanded=False)
            
            # Verify that the context manager is used (enter and exit called)
            mock_expander.return_value.__enter__.assert_called_once()
            mock_expander.return_value.__exit__.assert_called_once()
            
            # Verify that content is rendered (these should be called after expander is entered)
            mock_markdown.assert_called()  # Title and other markdown content
            mock_columns.assert_called()  # Layout columns
            mock_caption.assert_called()  # Field labels
            mock_write.assert_called()  # Field values

    def test_render_task_card_unknown_priority_no_styling(self):
        """Test that unknown priority values are displayed without special styling."""
        task = {
            'title': 'Task with Unknown Priority',
            'status': 'To Do',
            'priority': 'Urgent'  # Not a standard priority value
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption'), \
             patch('streamlit.write') as mock_write, \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(task)
            
            # Verify that unknown priority is displayed with plain write (no HTML styling)
            mock_write.assert_any_call("Urgent")
            
            # Verify that no HTML styling is applied for unknown priority
            html_calls = [call for call in mock_markdown.call_args_list 
                         if len(call[0]) > 0 and 'color:' in str(call[0][0]) and 'Urgent' in str(call[0][0])]
            assert len(html_calls) == 0, "Unknown priority should not have HTML styling"

    def test_render_task_card_error_handling(self):
        """Test that errors during task card rendering are handled gracefully."""
        # Create a task that might cause issues
        problematic_task = {
            'title': 'Error Task',
            'status': 'To Do'
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown', side_effect=Exception("Markdown error")) as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption'), \
             patch('streamlit.write'), \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.json') as mock_json, \
             patch('logging.getLogger') as mock_get_logger:
            
            # Setup mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Mock the expander context manager for the error case
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(problematic_task)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error rendering task card:" in str(mock_logger.error.call_args[0][0])
            
            # Verify fallback error display
            mock_error.assert_called_once_with("An error occurred while displaying this task card.")
            
            # Verify raw task data is shown as JSON fallback
            mock_json.assert_called_once_with(problematic_task)

    def test_render_task_card_estimated_time_formatting(self):
        """Test that estimated_time is formatted correctly as hours."""
        test_cases = [
            (2.0, "2.0 hours"),
            (0.5, "0.5 hours"),
            (4.75, "4.75 hours"),
            (1, "1 hours"),  # Integer should work too
            (None, "—"),  # None should show placeholder
        ]
        
        for estimated_time, expected_display in test_cases:
            with patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.markdown'), \
                 patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.caption'), \
                 patch('streamlit.write') as mock_write, \
                 patch('logging.getLogger'):
                
                # Mock the expander context manager
                mock_context = MagicMock()
                mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
                mock_expander.return_value.__exit__ = MagicMock(return_value=False)
                
                # Mock columns
                col1, col2 = MagicMock(), MagicMock()
                mock_columns.return_value = [col1, col2]
                
                task = {
                    'title': f'Task with {estimated_time} hours',
                    'status': 'To Do',
                    'estimated_time': estimated_time
                }
                
                # Import and call the function
                from kb_web_svc.components.task_card import render_task_card
                render_task_card(task)
                
                # Verify the correct estimated time format is displayed
                mock_write.assert_any_call(expected_display)

    def test_render_task_card_labels_formatting(self):
        """Test that labels list is formatted correctly as comma-separated string."""
        test_cases = [
            (["Feature", "Backend"], "Feature, Backend"),
            (["Bug"], "Bug"),
            (["Feature", "Frontend", "UI"], "Feature, Frontend, UI"),
            ([], "—"),  # Empty list should show placeholder
            (None, "—"),  # None should show placeholder
        ]
        
        for labels, expected_display in test_cases:
            with patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.markdown'), \
                 patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.caption'), \
                 patch('streamlit.write') as mock_write, \
                 patch('logging.getLogger'):
                
                # Mock the expander context manager
                mock_context = MagicMock()
                mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
                mock_expander.return_value.__exit__ = MagicMock(return_value=False)
                
                # Mock columns
                col1, col2 = MagicMock(), MagicMock()
                mock_columns.return_value = [col1, col2]
                
                task = {
                    'title': f'Task with labels {labels}',
                    'status': 'To Do',
                    'labels': labels
                }
                
                # Import and call the function
                from kb_web_svc.components.task_card import render_task_card
                render_task_card(task)
                
                # Verify the correct labels format is displayed
                mock_write.assert_any_call(expected_display)

    def test_render_task_card_missing_title_uses_fallback(self):
        """Test that missing title uses fallback 'Untitled Task'."""
        task_without_title = {
            'status': 'To Do'
            # Missing title
        }
        
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.caption'), \
             patch('streamlit.write'), \
             patch('logging.getLogger'):
            
            # Mock the expander context manager
            mock_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock columns
            col1, col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [col1, col2]
            
            # Import and call the function
            from kb_web_svc.components.task_card import render_task_card
            render_task_card(task_without_title)
            
            # Verify fallback title is used in expander header
            expected_header = "**Untitled Task** • `To Do`"
            mock_expander.assert_called_once_with(expected_header, expanded=False)
            
            # Verify fallback title is displayed prominently inside expander
            mock_markdown.assert_any_call("### Untitled Task")
