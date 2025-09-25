"""Tests for README.md Session State Management documentation.

Verifies that the README.md file contains proper documentation for
session state management including initialization, structure, and usage.
"""

import pytest
from pathlib import Path


class TestReadmeSessionState:
    """Test class for README.md session state management documentation."""
    
    @pytest.fixture
    def readme_content(self):
        """Read README.md content for testing."""
        readme_path = Path("README.md")
        if not readme_path.exists():
            pytest.fail("README.md file not found")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_session_state_management_section_exists(self, readme_content):
        """Test that Session State Management section header is present."""
        assert "## Session State Management" in readme_content, \
            "README.md should contain 'Session State Management' section header"
    
    def test_session_state_purpose_explained(self, readme_content):
        """Test that the purpose of st.session_state is explained."""
        assert "st.session_state" in readme_content, \
            "README.md should reference st.session_state"
        # Check for purpose-related content
        assert "application state" in readme_content.lower() or "task data" in readme_content.lower(), \
            "README.md should explain the purpose of session state"
    
    def test_initialize_session_state_mentioned(self, readme_content):
        """Test that initialize_session_state function is mentioned."""
        assert "initialize_session_state" in readme_content, \
            "README.md should reference initialize_session_state() function"
        assert "initialize_session_state()" in readme_content, \
            "README.md should show initialize_session_state() with parentheses"
    
    def test_core_session_variables_documented(self, readme_content):
        """Test that the key session state variables are documented."""
        # Check for all three core variables
        assert "tasks_by_status" in readme_content, \
            "README.md should document tasks_by_status variable"
        assert "form_states" in readme_content, \
            "README.md should document form_states variable"
        assert "ui_states" in readme_content, \
            "README.md should document ui_states variable"
    
    def test_tasks_by_status_structure_explained(self, readme_content):
        """Test that tasks_by_status structure is explained with examples."""
        # Should contain status values
        assert "To Do" in readme_content, \
            "README.md should mention 'To Do' status in tasks_by_status structure"
        assert "In Progress" in readme_content, \
            "README.md should mention 'In Progress' status in tasks_by_status structure"
        assert "Done" in readme_content, \
            "README.md should mention 'Done' status in tasks_by_status structure"
        
        # Should describe the dictionary structure
        assert "dictionary" in readme_content.lower(), \
            "README.md should explain that tasks_by_status is a dictionary"
    
    def test_state_management_module_referenced(self, readme_content):
        """Test that src/kb_web_svc/state_management.py is referenced."""
        assert "src/kb_web_svc/state_management.py" in readme_content, \
            "README.md should reference src/kb_web_svc/state_management.py module"
    
    def test_app_py_initialization_mentioned(self, readme_content):
        """Test that app.py calls initialize_session_state is mentioned."""
        assert "app.py" in readme_content, \
            "README.md should mention that app.py calls initialize_session_state"
    
    def test_developer_usage_examples_present(self, readme_content):
        """Test that developer usage examples are provided."""
        # Should contain helper function names
        assert "add_task_to_session" in readme_content, \
            "README.md should reference add_task_to_session function"
        assert "update_task_in_session" in readme_content, \
            "README.md should reference update_task_in_session function"
        assert "delete_task_from_session" in readme_content, \
            "README.md should reference delete_task_from_session function"
        assert "get_tasks_by_status" in readme_content, \
            "README.md should reference get_tasks_by_status function"
    
    def test_code_example_present(self, readme_content):
        """Test that code examples are provided for developers."""
        # Should contain import statement example
        assert "from kb_web_svc.state_management import" in readme_content, \
            "README.md should contain import example from kb_web_svc.state_management"
        
        # Should contain code block markers
        assert "```python" in readme_content, \
            "README.md should contain Python code block examples"
    
    def test_session_state_persistence_explained(self, readme_content):
        """Test that session state persistence across interactions is explained."""
        # Should explain persistence concept
        assert "persist" in readme_content.lower() or "maintain" in readme_content.lower(), \
            "README.md should explain that session state persists data"
        assert "browser session" in readme_content.lower() or "user session" in readme_content.lower(), \
            "README.md should explain session scope"
    
    def test_form_states_and_ui_states_purpose_explained(self, readme_content):
        """Test that form_states and ui_states purposes are explained."""
        # Should explain form_states purpose
        assert "form" in readme_content.lower() and ("ephemeral" in readme_content.lower() or "temporary" in readme_content.lower()), \
            "README.md should explain form_states purpose for ephemeral/temporary data"
        
        # Should explain ui_states purpose
        assert "ui" in readme_content.lower() and ("component" in readme_content.lower() or "interface" in readme_content.lower()), \
            "README.md should explain ui_states purpose for UI component state"
    
    def test_idempotent_initialization_explained(self, readme_content):
        """Test that idempotent initialization behavior is explained."""
        assert "idempotent" in readme_content.lower(), \
            "README.md should explain that initialize_session_state is idempotent"
    
    def test_database_sync_mentioned(self, readme_content):
        """Test that database synchronization is mentioned."""
        # Should mention database interaction
        assert "database" in readme_content.lower() and "sync" in readme_content.lower(), \
            "README.md should mention session state syncs with database"