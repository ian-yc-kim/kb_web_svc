"""Unit tests for task service docstring verification.

These tests verify that the update_task function has comprehensive
documentation with the required format and content.
"""

import pytest

from kb_web_svc.services.task_service import update_task


class TestTaskServiceDocstring:
    """Test cases for verifying update_task docstring format and content."""

    def test_update_task_docstring_exists(self):
        """Test that update_task has a non-None docstring."""
        assert update_task.__doc__ is not None
        assert len(update_task.__doc__.strip()) > 0

    def test_update_task_docstring_contains_required_tags(self):
        """Test that docstring contains all required @param/@returns/@raises tags."""
        docstring = update_task.__doc__
        
        # Check for required @param tags
        assert '@param task_id' in docstring
        assert '@param payload' in docstring
        assert '@param db' in docstring
        
        # Check for @returns tag
        assert '@returns' in docstring
        
        # Check for @raises tag
        assert '@raises' in docstring

    def test_update_task_docstring_contains_required_types(self):
        """Test that docstring mentions all required type annotations."""
        docstring = update_task.__doc__
        
        # Check for parameter types
        assert 'UUID' in docstring
        assert 'TaskUpdate' in docstring
        assert 'Session' in docstring
        
        # Check for return type
        assert 'Dict[str, Any]' in docstring

    def test_update_task_docstring_contains_all_exceptions(self):
        """Test that docstring mentions all custom exceptions that can be raised."""
        docstring = update_task.__doc__
        
        # Check for all expected exceptions
        assert 'TaskNotFoundError' in docstring
        assert 'OptimisticConcurrencyError' in docstring
        assert 'InvalidStatusError' in docstring
        assert 'InvalidPriorityError' in docstring
        assert 'PastDueDateError' in docstring
        assert 'ValueError' in docstring

    def test_update_task_docstring_contains_optimistic_concurrency_concept(self):
        """Test that docstring mentions optimistic concurrency control in summary."""
        docstring = update_task.__doc__
        
        # Check for optimistic concurrency control mention
        assert 'optimistic concurrency control' in docstring

    def test_update_task_docstring_contains_expected_summary(self):
        """Test that docstring starts with the required summary."""
        docstring = update_task.__doc__
        
        # Check for the specific summary line
        expected_summary = "Update an existing task with partial field changes, ensuring atomic operations and optimistic concurrency control."
        assert expected_summary in docstring

    def test_update_task_docstring_parameter_descriptions(self):
        """Test that docstring contains comprehensive parameter descriptions."""
        docstring = update_task.__doc__
        
        # Check that each parameter has meaningful description content
        # task_id parameter
        assert 'task_id' in docstring
        assert 'unique identifier' in docstring or 'UUID' in docstring
        
        # payload parameter
        assert 'payload' in docstring
        assert 'TaskUpdate' in docstring
        assert 'expected_last_modified' in docstring
        
        # db parameter
        assert 'db' in docstring
        assert 'Session' in docstring
        assert 'database' in docstring

    def test_update_task_docstring_exception_descriptions(self):
        """Test that docstring contains detailed exception descriptions."""
        docstring = update_task.__doc__
        
        # Check that exceptions have meaningful descriptions
        assert 'not found' in docstring or 'does not exist' in docstring
        assert 'concurrency' in docstring
        assert 'status' in docstring and 'invalid' in docstring
        assert 'priority' in docstring and 'invalid' in docstring
        assert 'past' in docstring and 'due' in docstring
        assert 'negative' in docstring or 'validation' in docstring

    def test_update_task_docstring_mentions_timezone_handling(self):
        """Test that docstring mentions timezone handling for expected_last_modified."""
        docstring = update_task.__doc__
        
        # Check for timezone-related mentions
        assert 'timezone' in docstring or 'UTC' in docstring

    def test_update_task_docstring_mentions_automatic_last_modified_update(self):
        """Test that docstring mentions automatic last_modified updates via SQLAlchemy events."""
        docstring = update_task.__doc__
        
        # Check for SQLAlchemy event mention
        assert 'SQLAlchemy' in docstring and 'event' in docstring
        assert 'last_modified' in docstring and 'automatically' in docstring
