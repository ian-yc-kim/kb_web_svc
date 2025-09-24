"""Tests for README.md Database Configuration documentation.

Verifies that the README.md file contains proper documentation for
database configuration including PostgreSQL and SQLite examples.
"""

import pytest
from pathlib import Path


class TestReadmeDbConfig:
    """Test class for README.md database configuration documentation."""
    
    @pytest.fixture
    def readme_content(self):
        """Read README.md content for testing."""
        readme_path = Path("README.md")
        if not readme_path.exists():
            pytest.fail("README.md file not found")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_database_configuration_section_exists(self, readme_content):
        """Test that Database Configuration section header is present."""
        assert "## Database Configuration" in readme_content, \
            "README.md should contain 'Database Configuration' section header"
    
    def test_database_url_and_env_mentioned(self, readme_content):
        """Test that DATABASE_URL and .env usage are explained."""
        assert "DATABASE_URL" in readme_content, \
            "README.md should reference DATABASE_URL environment variable"
        assert ".env" in readme_content, \
            "README.md should explain .env file usage"
    
    def test_postgresql_example_present(self, readme_content):
        """Test that PostgreSQL example is provided."""
        postgresql_example = "postgresql://username:password@host:port/dbname"
        assert postgresql_example in readme_content, \
            "README.md should contain PostgreSQL DATABASE_URL example"
    
    def test_sqlite_file_based_example_present(self, readme_content):
        """Test that SQLite file-based example is provided."""
        sqlite_example = "sqlite:///./test.db"
        assert sqlite_example in readme_content, \
            "README.md should contain SQLite file-based DATABASE_URL example"
    
    def test_in_memory_default_explanation(self, readme_content):
        """Test that in-memory SQLite default behavior is explained."""
        # Check for key phrases that explain the default behavior
        assert "in-memory" in readme_content.lower(), \
            "README.md should mention in-memory SQLite database"
        assert "omit" in readme_content.lower() or "omitted" in readme_content.lower(), \
            "README.md should explain that DATABASE_URL can be omitted for default behavior"
        assert "default" in readme_content.lower(), \
            "README.md should explain the default database behavior"
    
    def test_run_command_present(self, readme_content):
        """Test that poetry run command is included."""
        run_command = "poetry run kb_web_svc"
        assert run_command in readme_content, \
            "README.md should include 'poetry run kb_web_svc' command"
    
    def test_poetry_install_command_present(self, readme_content):
        """Test that poetry install command is included."""
        install_command = "poetry install"
        assert install_command in readme_content, \
            "README.md should include 'poetry install' command"
    
    def test_env_file_setup_section_exists(self, readme_content):
        """Test that .env file setup instructions are present."""
        assert "Setting up your `.env` file" in readme_content or \
               "Setting up your .env file" in readme_content, \
            "README.md should contain .env file setup instructions"
    
    def test_running_application_section_exists(self, readme_content):
        """Test that running the application section is present."""
        assert "Running the Application" in readme_content, \
            "README.md should contain 'Running the Application' section"
    
    def test_postgresql_production_label(self, readme_content):
        """Test that PostgreSQL is labeled as production configuration."""
        assert "PostgreSQL (Production)" in readme_content, \
            "README.md should label PostgreSQL example as production"
    
    def test_sqlite_development_label(self, readme_content):
        """Test that SQLite file-based is labeled as development configuration."""
        assert "SQLite File-based (Development)" in readme_content, \
            "README.md should label SQLite file-based example as development"
    
    def test_sqlite_inmemory_default_label(self, readme_content):
        """Test that SQLite in-memory is labeled as default configuration."""
        assert "SQLite In-memory (Default)" in readme_content, \
            "README.md should label SQLite in-memory as default configuration"