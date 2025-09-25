"""Unit tests for the task service layer.

These tests verify the create_task function functionality including
input validation, data sanitization, database persistence, and error handling.
"""

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.task import TaskCreate
from kb_web_svc.services.task_service import (
    create_task,
    InvalidStatusError,
    InvalidPriorityError,
    PastDueDateError
)


class TestCreateTask:
    """Test cases for the create_task service function."""

    def test_create_task_all_fields_success(self, db_session: Session):
        """Test successful task creation with all fields provided (happy path)."""
        # Prepare input data with all fields
        task_data = TaskCreate(
            title="Complete project documentation",
            assignee="John Doe",
            due_date=date.today() + timedelta(days=30),
            description="Write comprehensive documentation for the project",
            priority="High",
            labels=["documentation", "high-priority"],
            estimated_time=8.5,
            status="In Progress"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify return value structure and types
        assert isinstance(result, dict)
        assert 'id' in result
        assert isinstance(result['id'], str)
        
        # Verify all fields are correctly set
        assert result['title'] == "Complete project documentation"
        assert result['assignee'] == "John Doe"
        assert result['due_date'] == (date.today() + timedelta(days=30)).isoformat()
        assert result['description'] == "Write comprehensive documentation for the project"
        assert result['priority'] == "High"
        assert result['labels'] == ["documentation", "high-priority"]
        assert result['estimated_time'] == 8.5
        assert result['status'] == "In Progress"
        assert 'created_at' in result
        assert 'last_modified' in result
        
        # Verify task is persisted in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task is not None
        assert db_task.title == "Complete project documentation"
        assert db_task.assignee == "John Doe"
        assert db_task.priority == Priority.HIGH
        assert db_task.status == Status.IN_PROGRESS
        assert db_task.labels == ["documentation", "high-priority"]

    def test_create_task_required_fields_only_success(self, db_session: Session):
        """Test successful task creation with only required fields."""
        # Prepare input data with only required fields
        task_data = TaskCreate(
            title="Minimal task",
            status="To Do"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify return value structure
        assert isinstance(result, dict)
        assert result['title'] == "Minimal task"
        assert result['status'] == "To Do"
        
        # Verify optional fields are handled correctly
        assert result['assignee'] is None
        assert result['due_date'] is None
        assert result['description'] is None
        assert result['priority'] is None
        assert result['labels'] == []  # None becomes empty list in to_dict()
        assert result['estimated_time'] is None
        
        # Verify task is persisted in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task is not None
        assert db_task.title == "Minimal task"
        assert db_task.status == Status.TODO
        assert db_task.priority is None
        assert db_task.labels is None

    def test_create_task_missing_title_validation_error(self):
        """Test that missing title raises Pydantic ValidationError."""
        # Try to create TaskCreate without title
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                status="To Do"
            )
        
        # Verify the validation error is for the title field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('title',)
        assert errors[0]['type'] == 'missing'

    def test_create_task_missing_status_validation_error(self):
        """Test that missing status raises Pydantic ValidationError."""
        # Try to create TaskCreate without status
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Test task"
            )
        
        # Verify the validation error is for the status field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('status',)
        assert errors[0]['type'] == 'missing'

    def test_create_task_empty_title_validation_error(self):
        """Test that empty title raises Pydantic ValidationError."""
        # Try to create TaskCreate with empty title
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="   ",  # Whitespace only
                status="To Do"
            )
        
        # Verify the validation error is for the title field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('title',)
        assert 'Title cannot be empty' in str(errors[0]['msg'])

    def test_create_task_empty_status_validation_error(self):
        """Test that empty status raises Pydantic ValidationError."""
        # Try to create TaskCreate with empty status
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Test task",
                status="   "  # Whitespace only
            )
        
        # Verify the validation error is for the status field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('status',)
        assert 'Status cannot be empty' in str(errors[0]['msg'])

    def test_create_task_invalid_priority_error(self, db_session: Session):
        """Test that invalid priority value raises InvalidPriorityError."""
        # Create task data with invalid priority
        task_data = TaskCreate(
            title="Test task",
            priority="Urgent",  # Invalid priority
            status="To Do"
        )
        
        # Count initial tasks in database
        initial_count = db_session.query(Task).count()
        
        # Try to create task - should raise InvalidPriorityError
        with pytest.raises(InvalidPriorityError) as exc_info:
            create_task(task_data, db_session)
        
        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "Invalid priority 'Urgent'" in error_msg
        assert "Must be one of:" in error_msg
        assert "Critical" in error_msg
        assert "High" in error_msg
        assert "Medium" in error_msg
        assert "Low" in error_msg
        
        # Verify transaction was rolled back - no new task created
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_create_task_invalid_status_error(self, db_session: Session):
        """Test that invalid status value raises InvalidStatusError."""
        # Create task data with invalid status
        task_data = TaskCreate(
            title="Test task",
            status="Invalid Status"  # Invalid status
        )
        
        # Count initial tasks in database
        initial_count = db_session.query(Task).count()
        
        # Try to create task - should raise InvalidStatusError
        with pytest.raises(InvalidStatusError) as exc_info:
            create_task(task_data, db_session)
        
        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "Invalid status 'Invalid Status'" in error_msg
        assert "Must be one of:" in error_msg
        assert "To Do" in error_msg
        assert "In Progress" in error_msg
        assert "Done" in error_msg
        
        # Verify transaction was rolled back - no new task created
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_create_task_past_due_date_error(self, db_session: Session):
        """Test that due date in the past raises PastDueDateError."""
        # Create task data with past due date
        past_date = date.today() - timedelta(days=1)
        task_data = TaskCreate(
            title="Test task",
            due_date=past_date,
            status="To Do"
        )
        
        # Count initial tasks in database
        initial_count = db_session.query(Task).count()
        
        # Try to create task - should raise PastDueDateError
        with pytest.raises(PastDueDateError) as exc_info:
            create_task(task_data, db_session)
        
        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert f"Due date {past_date}" in error_msg
        assert "cannot be in the past" in error_msg
        
        # Verify transaction was rolled back - no new task created
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_create_task_invalid_due_date_format_validation_error(self):
        """Test that invalid due_date format raises Pydantic ValidationError."""
        # Try to create TaskCreate with invalid due_date format
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Test task",
                due_date="not-a-date",  # Invalid date format
                status="To Do"
            )
        
        # Verify the validation error is for the due_date field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('due_date',)
        # Pydantic should reject this as not a valid date

    def test_create_task_negative_estimated_time_validation_error(self):
        """Test that negative estimated_time raises Pydantic ValidationError."""
        # Try to create TaskCreate with negative estimated_time
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Test task",
                estimated_time=-1.0,  # Negative time
                status="To Do"
            )
        
        # Verify the validation error is for the estimated_time field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('estimated_time',)
        assert errors[0]['type'] == 'greater_than_equal'

    def test_create_task_negative_estimated_time_service_error(self, db_session: Session):
        """Test that negative estimated_time in service raises ValueError."""
        # Create task data with negative estimated time
        # (bypassing Pydantic validation by creating manually)
        task_data = TaskCreate(
            title="Test task",
            estimated_time=0.0,  # Valid for Pydantic
            status="To Do"
        )
        # Manually set negative value to test service validation
        task_data.estimated_time = -5.0
        
        # Count initial tasks in database
        initial_count = db_session.query(Task).count()
        
        # Try to create task - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            create_task(task_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Estimated time must be non-negative" in error_msg
        assert "-5.0" in error_msg
        
        # Verify transaction was rolled back - no new task created
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_create_task_empty_labels_list_success(self, db_session: Session):
        """Test that empty labels list works correctly."""
        # Create task data with empty labels list
        task_data = TaskCreate(
            title="Test task with empty labels",
            labels=[],  # Empty list
            status="To Do"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify labels are handled correctly
        assert result['labels'] == []
        
        # Verify in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task.labels is None  # Empty list becomes None in service

    def test_create_task_none_labels_success(self, db_session: Session):
        """Test that None labels work correctly."""
        # Create task data with None labels
        task_data = TaskCreate(
            title="Test task with None labels",
            labels=None,  # None
            status="To Do"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify labels are handled correctly - to_dict() converts None to []
        assert result['labels'] == []
        
        # Verify in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task.labels is None

    def test_create_task_labels_with_whitespace_cleanup(self, db_session: Session):
        """Test that labels with whitespace are cleaned up properly."""
        # Create task data with labels containing whitespace
        task_data = TaskCreate(
            title="Test task with whitespace labels",
            labels=["  frontend  ", "", "  ", "backend", "testing  "],
            status="To Do"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify labels are cleaned up (empty strings removed, whitespace stripped)
        assert result['labels'] == ["frontend", "backend", "testing"]
        
        # Verify in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task.labels == ["frontend", "backend", "testing"]

    def test_create_task_database_persistence_verification(self, db_session: Session):
        """Test that created task is properly persisted and queryable from database."""
        # Create task
        task_data = TaskCreate(
            title="Database persistence test",
            assignee="Test User",
            priority="Medium",
            status="In Progress"
        )
        
        result = create_task(task_data, db_session)
        task_id = uuid.UUID(result['id'])
        
        # Query task from database using different methods
        
        # 1. Direct get by ID
        db_task_by_id = db_session.get(Task, task_id)
        assert db_task_by_id is not None
        assert db_task_by_id.title == "Database persistence test"
        
        # 2. Query by title
        db_task_by_title = db_session.query(Task).filter(Task.title == "Database persistence test").first()
        assert db_task_by_title is not None
        assert db_task_by_title.id == task_id
        
        # 3. Query by status
        db_tasks_by_status = db_session.query(Task).filter(Task.status == Status.IN_PROGRESS).all()
        task_ids = [task.id for task in db_tasks_by_status]
        assert task_id in task_ids
        
        # 4. Verify the task's to_dict() method matches returned result
        assert db_task_by_id.to_dict() == result

    def test_create_task_transaction_rollback_on_database_error(self, db_session: Session, monkeypatch):
        """Test that database transaction is rolled back on errors."""
        task_data = TaskCreate(
            title="Transaction rollback test",
            status="To Do"
        )
        
        # Count initial tasks
        initial_count = db_session.query(Task).count()
        
        # Mock db.commit to raise an exception
        original_commit = db_session.commit
        def mock_commit():
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'commit', mock_commit)
        
        # Try to create task - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            create_task(task_data, db_session)
        
        # Restore original commit for verification
        monkeypatch.setattr(db_session, 'commit', original_commit)
        
        # Verify no new task was persisted (transaction rolled back)
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_create_task_whitespace_handling(self, db_session: Session):
        """Test that input fields with whitespace are properly handled."""
        # Create task with whitespace in various fields
        task_data = TaskCreate(
            title="  Whitespace test task  ",
            assignee="  John Doe  ",
            description="  Task description with whitespace  ",
            priority="  High  ",
            status="  To Do  "
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify whitespace is trimmed
        assert result['title'] == "Whitespace test task"
        assert result['assignee'] == "John Doe"
        assert result['description'] == "Task description with whitespace"
        assert result['priority'] == "High"
        assert result['status'] == "To Do"
        
        # Verify in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Whitespace test task"
        assert db_task.assignee == "John Doe"
        assert db_task.priority == Priority.HIGH

    def test_create_task_empty_strings_become_none(self, db_session: Session):
        """Test that empty strings (after stripping) become None for optional fields."""
        # Create task with empty strings for optional fields
        task_data = TaskCreate(
            title="Empty strings test",
            assignee="   ",  # Whitespace only
            description="   ",  # Whitespace only
            priority="   ",  # Whitespace only
            status="To Do"
        )
        
        # Create task
        result = create_task(task_data, db_session)
        
        # Verify empty strings become None
        assert result['assignee'] is None
        assert result['description'] is None
        assert result['priority'] is None
        
        # Verify in database
        task_id = uuid.UUID(result['id'])
        db_task = db_session.get(Task, task_id)
        assert db_task.assignee is None
        assert db_task.description is None
        assert db_task.priority is None