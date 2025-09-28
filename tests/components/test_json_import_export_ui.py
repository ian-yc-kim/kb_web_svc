"""Unit tests for the JSON import/export UI component.

Tests cover UI element presence, export/import functionality, validation,
backup/rollback operations, error handling scenarios, and accessibility features.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
from pydantic import ValidationError

from kb_web_svc.components.json_import_export_ui import render_json_import_export_ui
from kb_web_svc.schemas.import_export_schemas import TaskImportData


class MockUploadedFile:
    """Mock class for Streamlit UploadedFile."""
    
    def __init__(self, content: str, name: str = "test.json"):
        self.content = content
        self.name = name
    
    def getvalue(self):
        return self.content.encode('utf-8') if isinstance(self.content, str) else self.content
    
    def read(self):
        return self.content


class TestJsonImportExportUI:
    """Test class for JSON import/export UI component."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Fixture providing mocked Streamlit functions."""
        with patch('kb_web_svc.components.json_import_export_ui.st') as mock_st:
            # Configure button to return False by default
            mock_st.button.return_value = False
            mock_st.file_uploader.return_value = None
            mock_st.radio.return_value = "Skip duplicates (keep existing tasks unchanged)"
            mock_st.session_state = {}
            # Configure spinner as context manager
            mock_spinner = MagicMock()
            mock_st.spinner.return_value.__enter__ = lambda x: mock_spinner
            mock_st.spinner.return_value.__exit__ = lambda x, y, z, a: None
            yield mock_st
    
    @pytest.fixture
    def mock_services(self):
        """Fixture providing mocked service functions."""
        with patch('kb_web_svc.components.json_import_export_ui.export_all_tasks_to_json') as mock_export, \
             patch('kb_web_svc.components.json_import_export_ui.import_tasks_logic') as mock_import, \
             patch('kb_web_svc.components.json_import_export_ui.restore_database_from_json_backup') as mock_restore, \
             patch('kb_web_svc.components.json_import_export_ui.load_tasks_from_db_to_session') as mock_load:
            yield {
                'export': mock_export,
                'import': mock_import,
                'restore': mock_restore,
                'load': mock_load
            }
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample valid task data matching TaskImportData schema."""
        return [
            {
                "title": "Test Task 1",
                "description": "Test description 1",
                "assignee": "user1",
                "due_date": "2024-12-31",
                "priority": "HIGH",
                "labels": ["test", "ui"],
                "estimated_time": 8.0,
                "status": "TODO"
            },
            {
                "title": "Test Task 2",
                "description": "Test description 2",
                "assignee": "user2",
                "due_date": "2024-12-25",
                "priority": "MEDIUM",
                "labels": ["test"],
                "estimated_time": 4.0,
                "status": "IN_PROGRESS"
            }
        ]
    
    @pytest.fixture
    def sample_json_content(self, sample_task_data):
        """Sample JSON content as string."""
        return json.dumps(sample_task_data)
    
    def test_ui_elements_presence(self, db_session, mock_streamlit, mock_services):
        """Test that all required UI elements are rendered."""
        render_json_import_export_ui(db_session)
        
        # Verify UI structure calls
        mock_streamlit.subheader.assert_any_call("Export Tasks")
        mock_streamlit.subheader.assert_any_call("Import Tasks")
        mock_streamlit.write.assert_called()
        
        # Verify export button (now with accessibility parameters)
        export_button_calls = [call for call in mock_streamlit.button.call_args_list 
                             if "Export All Tasks to JSON" in str(call)]
        assert len(export_button_calls) >= 1, "Export button should be rendered"
        
        # Verify file uploader
        mock_streamlit.file_uploader.assert_called_once_with(
            "Upload JSON file for Import",
            type=["json"],
            help="Select a JSON file containing task data to import. The file must contain a valid list of task objects.",
            key="import_file_uploader"
        )
        
        # Verify markdown separator
        mock_streamlit.markdown.assert_called_with("---")
    
    def test_accessibility_export_button(self, db_session, mock_streamlit, mock_services):
        """Test that export button has accessibility features (help text and key)."""
        render_json_import_export_ui(db_session)
        
        # Find the export button call
        export_button_calls = [call for call in mock_streamlit.button.call_args_list 
                             if call[0][0] == "Export All Tasks to JSON"]
        assert len(export_button_calls) == 1
        
        # Verify help parameter is present and descriptive
        call_args, call_kwargs = export_button_calls[0]
        assert 'help' in call_kwargs
        help_text = call_kwargs['help']
        assert len(help_text) > 10  # Should be descriptive
        assert 'export' in help_text.lower()
        assert 'backup' in help_text.lower() or 'sharing' in help_text.lower()
        
        # Verify key parameter is present and stable
        assert 'key' in call_kwargs
        assert call_kwargs['key'] == 'export_tasks_button'
    
    def test_accessibility_file_uploader(self, db_session, mock_streamlit, mock_services):
        """Test that file uploader has accessibility features (help text and key)."""
        render_json_import_export_ui(db_session)
        
        # Verify file uploader accessibility
        mock_streamlit.file_uploader.assert_called_once()
        call_args, call_kwargs = mock_streamlit.file_uploader.call_args
        
        # Check label is descriptive
        label = call_args[0]
        assert "Upload JSON file for Import" == label
        
        # Check help parameter is present and descriptive
        assert 'help' in call_kwargs
        help_text = call_kwargs['help']
        assert len(help_text) > 10  # Should be descriptive
        assert 'json' in help_text.lower()
        assert 'import' in help_text.lower()
        
        # Check key parameter is present and stable
        assert 'key' in call_kwargs
        assert call_kwargs['key'] == 'import_file_uploader'
        
        # Check type parameter
        assert 'type' in call_kwargs
        assert call_kwargs['type'] == ['json']
    
    def test_accessibility_conflict_strategy_radio(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that conflict strategy radio has accessibility features (help text and key)."""
        # Upload a file to trigger the radio display
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify radio button accessibility
        mock_streamlit.radio.assert_called_once()
        call_args, call_kwargs = mock_streamlit.radio.call_args
        
        # Check label is descriptive
        label = call_args[0]
        assert "How should conflicts with existing tasks be handled" in label
        
        # Check help parameter is present and descriptive
        assert 'help' in call_kwargs
        help_text = call_kwargs['help']
        assert len(help_text) > 20  # Should be descriptive
        assert 'conflict' in help_text.lower() or 'duplicate' in help_text.lower()
        
        # Check key parameter is present and stable
        assert 'key' in call_kwargs
        assert call_kwargs['key'] == 'conflict_strategy_radio'
    
    def test_accessibility_import_button(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that import button has accessibility features (help text and key)."""
        # Upload a file to trigger the import button display
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Find the import button call
        import_button_calls = [call for call in mock_streamlit.button.call_args_list 
                             if call[0][0] == "Import Tasks"]
        assert len(import_button_calls) == 1
        
        # Verify help parameter is present and descriptive
        call_args, call_kwargs = import_button_calls[0]
        assert 'help' in call_kwargs
        help_text = call_kwargs['help']
        assert len(help_text) > 10  # Should be descriptive
        assert 'import' in help_text.lower()
        assert 'strategy' in help_text.lower() or 'conflict' in help_text.lower()
        
        # Verify key parameter is present and stable
        assert 'key' in call_kwargs
        assert call_kwargs['key'] == 'import_tasks_button'
        
        # Verify button type is set to primary
        assert 'type' in call_kwargs
        assert call_kwargs['type'] == 'primary'
    
    def test_accessibility_download_button(self, db_session, mock_streamlit, mock_services):
        """Test that download button has accessibility features (help text and key)."""
        # Configure export button to return True
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Export All Tasks to JSON"
        
        # Configure export service to return sample data
        sample_json = '{"tasks": []}'
        mock_services['export'].return_value = sample_json
        
        with patch('kb_web_svc.components.json_import_export_ui.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            
            render_json_import_export_ui(db_session)
        
        # Verify download button accessibility
        mock_streamlit.download_button.assert_called_once()
        call_args, call_kwargs = mock_streamlit.download_button.call_args
        
        # Check help parameter is present and descriptive
        assert 'help' in call_kwargs
        help_text = call_kwargs['help']
        assert len(help_text) > 5  # Should reference filename
        assert 'download' in help_text.lower()
        
        # Check key parameter is present and stable
        assert 'key' in call_kwargs
        assert call_kwargs['key'] == 'download_exported_json'
    
    def test_accessibility_success_error_messages_have_clear_text(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that success and error messages contain clear text beyond emojis."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Check that success messages have clear text beyond emojis
        success_calls = mock_streamlit.success.call_args_list
        for call in success_calls:
            message = call[0][0]
            # Remove common emojis and check if there's still meaningful text
            text_without_emojis = message.replace('✅', '').replace('🎉', '').replace('📊', '').strip()
            assert len(text_without_emojis) > 5  # Should have substantial text beyond emojis
            # Should contain descriptive words
            assert any(word in text_without_emojis.lower() for word in ['successfully', 'found', 'tasks', 'complete', 'imported'])
    
    def test_export_button_functionality(self, db_session, mock_streamlit, mock_services):
        """Test export button triggers export service and download button."""
        # Configure export button to return True
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Export All Tasks to JSON"
        
        # Configure export service to return sample data
        sample_json = '{"tasks": []}'
        mock_services['export'].return_value = sample_json
        
        with patch('kb_web_svc.components.json_import_export_ui.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            
            render_json_import_export_ui(db_session)
        
        # Verify export service called
        mock_services['export'].assert_called_once_with(db_session)
        
        # Verify download button called with correct parameters
        mock_streamlit.download_button.assert_called_once_with(
            label="Download JSON File",
            data=sample_json,
            file_name="kanban_tasks_export_20240101_120000.json",
            mime="application/json",
            help="Click to download the exported tasks as kanban_tasks_export_20240101_120000.json",
            key="download_exported_json"
        )
    
    def test_export_error_handling(self, db_session, mock_streamlit, mock_services):
        """Test export error handling."""
        # Configure export button to return True
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Export All Tasks to JSON"
        
        # Configure export service to raise exception
        mock_services['export'].side_effect = Exception("Export failed")
        
        render_json_import_export_ui(db_session)
        
        # Verify error message displayed
        mock_streamlit.error.assert_any_call("❌ Failed to export tasks. Please try again or contact support if the problem persists.")
    
    def test_file_upload_valid_json(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test file upload with valid JSON content."""
        # Configure file uploader to return mock file
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify success message for valid file
        mock_streamlit.success.assert_any_call("✅ File uploaded successfully! Found 2 tasks to import.")
        
        # Verify strategy selection UI is rendered
        mock_streamlit.radio.assert_called_once()
        
        # Verify import button is rendered
        import_button_calls = [call for call in mock_streamlit.button.call_args_list 
                             if call[0][0] == "Import Tasks"]
        assert len(import_button_calls) >= 1, "Import button should be rendered"
    
    def test_file_upload_invalid_json(self, db_session, mock_streamlit, mock_services):
        """Test file upload with invalid JSON content."""
        # Configure file uploader to return mock file with invalid JSON
        uploaded_file = MockUploadedFile("invalid json content")
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify error message for invalid JSON
        mock_streamlit.error.assert_any_call("❌ Invalid JSON format: Expecting value: line 1 column 1 (char 0)")
    
    def test_file_upload_invalid_schema(self, db_session, mock_streamlit, mock_services):
        """Test file upload with JSON that doesn't match TaskImportData schema."""
        # Invalid task data (missing required fields)
        invalid_data = json.dumps([{"invalid_field": "value"}])
        uploaded_file = MockUploadedFile(invalid_data)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify validation error messages
        mock_streamlit.error.assert_any_call("❌ **Validation Errors Found:**")
        # Should show task-specific error
        error_calls = [call for call in mock_streamlit.error.call_args_list 
                      if "Task 1:" in str(call)]
        assert len(error_calls) > 0
    
    def test_file_upload_not_list(self, db_session, mock_streamlit, mock_services):
        """Test file upload with JSON that's not a list."""
        # JSON object instead of list
        non_list_data = json.dumps({"not": "a list"})
        uploaded_file = MockUploadedFile(non_list_data)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify error message
        mock_streamlit.error.assert_any_call("❌ JSON file must contain a list of task objects.")
    
    def test_file_upload_empty_list(self, db_session, mock_streamlit, mock_services):
        """Test file upload with empty task list."""
        empty_list = json.dumps([])
        uploaded_file = MockUploadedFile(empty_list)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        render_json_import_export_ui(db_session)
        
        # Verify warning message
        mock_streamlit.warning.assert_any_call("⚠️ The JSON file contains no tasks to import.")
    
    def test_strategy_selection_mapping(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that conflict strategy selection maps correctly to service values."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        # Test different strategy selections
        strategies = {
            "Skip duplicates (keep existing tasks unchanged)": "skip",
            "Replace existing with imported data": "replace",
            "Merge (update if imported is newer)": "merge_with_timestamp"
        }
        
        for user_option, service_value in strategies.items():
            mock_streamlit.radio.return_value = user_option
            mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
            
            render_json_import_export_ui(db_session)
            
            # Verify the service is called with correct strategy
            if mock_services['import'].called:
                args, kwargs = mock_services['import'].call_args
                assert args[2] == service_value  # third argument is strategy
            
            # Reset mocks for next iteration
            mock_services['import'].reset_mock()
    
    def test_successful_import_flow(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test successful import operation flow."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
        
        # Configure services
        mock_services['export'].return_value = "backup_json_data"
        mock_services['import'].return_value = {
            "imported": 2,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        render_json_import_export_ui(db_session)
        
        # Verify backup was created before import
        mock_services['export'].assert_called_with(db_session)
        
        # Verify import was called with correct parameters
        mock_services['import'].assert_called_once()
        args, kwargs = mock_services['import'].call_args
        assert len(args[1]) == 2  # 2 tasks in sample data
        assert args[2] == "skip"  # default strategy
        
        # Verify success messages
        mock_streamlit.success.assert_any_call("🎉 **Import Complete!**")
        
        # Verify metrics displayed
        mock_streamlit.metric.assert_any_call("Imported", 2, delta="new tasks")
        mock_streamlit.metric.assert_any_call("Updated", 0, delta="existing tasks")
        mock_streamlit.metric.assert_any_call("Skipped", 0, delta="duplicates")
        mock_streamlit.metric.assert_any_call("Failed", 0, delta="errors")
        
        # Verify UI refresh was called
        mock_services['load'].assert_called_once_with(db_session)
    
    def test_failed_import_with_successful_rollback(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test failed import with successful rollback."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
        
        # Configure services
        mock_services['export'].return_value = "backup_json_data"
        mock_services['import'].side_effect = Exception("Import failed")
        
        # Setup session state with backup
        mock_streamlit.session_state = {'db_backup_json': 'backup_json_data'}
        
        render_json_import_export_ui(db_session)
        
        # Verify backup was created
        mock_services['export'].assert_called_with(db_session)
        
        # Verify import was attempted
        mock_services['import'].assert_called_once()
        
        # Verify rollback was attempted
        mock_services['restore'].assert_called_once_with(db_session, 'backup_json_data')
        
        # Verify error messages
        mock_streamlit.error.assert_any_call("❌ **Import failed! Attempting rollback...**")
        mock_streamlit.error.assert_any_call("❌ **Import failed and rolled back successfully.**")
        
        # Verify UI refresh was called
        mock_services['load'].assert_called_once_with(db_session)
    
    def test_failed_import_with_failed_rollback(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test failed import with failed rollback."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
        
        # Configure services
        mock_services['export'].return_value = "backup_json_data"
        mock_services['import'].side_effect = Exception("Import failed")
        mock_services['restore'].side_effect = Exception("Rollback failed")
        
        # Setup session state with backup
        mock_streamlit.session_state = {'db_backup_json': 'backup_json_data'}
        
        render_json_import_export_ui(db_session)
        
        # Verify critical error message
        mock_streamlit.error.assert_any_call("❌ **Import failed. Rollback also failed! Manual intervention may be required.**")
        
        # Verify both error messages are shown
        error_calls = [str(call) for call in mock_streamlit.error.call_args_list]
        assert any("Original error:" in call for call in error_calls)
        assert any("Rollback error:" in call for call in error_calls)
    
    def test_no_import_when_no_file_uploaded(self, db_session, mock_streamlit, mock_services):
        """Test that no import occurs when no file is uploaded."""
        # No file uploaded (default None)
        mock_streamlit.file_uploader.return_value = None
        
        render_json_import_export_ui(db_session)
        
        # Verify import service is not called
        mock_services['import'].assert_not_called()
        mock_services['restore'].assert_not_called()
    
    def test_no_import_when_validation_fails(self, db_session, mock_streamlit, mock_services):
        """Test that no import occurs when JSON validation fails."""
        # Invalid JSON file
        uploaded_file = MockUploadedFile("invalid json")
        mock_streamlit.file_uploader.return_value = uploaded_file
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
        
        render_json_import_export_ui(db_session)
        
        # Verify import service is not called
        mock_services['import'].assert_not_called()
        mock_services['restore'].assert_not_called()
    
    def test_backup_created_before_import(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that database backup is created before import operation starts."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Import Tasks"
        
        # Track call order
        call_order = []
        
        def track_export(*args, **kwargs):
            call_order.append('export')
            return "backup_data"
        
        def track_import(*args, **kwargs):
            call_order.append('import')
            return {"imported": 1, "updated": 0, "skipped": 0, "failed": 0}
        
        mock_services['export'].side_effect = track_export
        mock_services['import'].side_effect = track_import
        
        render_json_import_export_ui(db_session)
        
        # Verify export (backup) was called before import
        assert call_order == ['export', 'import']
        
        # Verify session state was updated with backup
        assert hasattr(mock_streamlit.session_state, '__setitem__')
    
    def test_database_connection_error_handling(self, mock_streamlit, mock_services):
        """Test handling when database connection is None."""
        render_json_import_export_ui(None)  # Pass None as db
        
        # Verify error message is displayed
        mock_streamlit.error.assert_called_with(
            "Database connection is not available. Please refresh the page and try again."
        )
        
        # Verify no services are called
        mock_services['export'].assert_not_called()
        mock_services['import'].assert_not_called()
        mock_services['restore'].assert_not_called()
        mock_services['load'].assert_not_called()
    
    def test_session_state_strategy_persistence(self, db_session, mock_streamlit, mock_services, sample_json_content):
        """Test that conflict strategy selection persists in session state."""
        uploaded_file = MockUploadedFile(sample_json_content)
        mock_streamlit.file_uploader.return_value = uploaded_file
        
        # Mock session state as dictionary
        mock_session_state = {}
        mock_streamlit.session_state = mock_session_state
        
        # Configure radio to return specific selection
        selected_strategy = "Replace existing with imported data"
        mock_streamlit.radio.return_value = selected_strategy
        
        render_json_import_export_ui(db_session)
        
        # Verify strategy was stored in session state
        assert mock_session_state.get('import_conflict_strategy') == selected_strategy
    
    @patch('kb_web_svc.components.json_import_export_ui.logger')
    def test_logging_behavior(self, mock_logger, db_session, mock_streamlit, mock_services):
        """Test that appropriate logging occurs during operations."""
        render_json_import_export_ui(db_session)
        
        # Verify info logging
        mock_logger.info.assert_any_call("Rendering JSON import/export UI")
        mock_logger.info.assert_any_call("JSON import/export UI rendered successfully")
    
    @patch('kb_web_svc.components.json_import_export_ui.logger')
    def test_exception_logging(self, mock_logger, db_session, mock_streamlit, mock_services):
        """Test that exceptions are properly logged."""
        # Configure export to raise exception
        mock_streamlit.button.side_effect = lambda text, **kwargs: text == "Export All Tasks to JSON"
        mock_services['export'].side_effect = Exception("Test exception")
        
        render_json_import_export_ui(db_session)
        
        # Verify error was logged with exc_info
        assert mock_logger.error.called
        # Check that exc_info=True was used in at least one call
        error_calls = mock_logger.error.call_args_list
        assert any(call.kwargs.get('exc_info') is True for call in error_calls)
