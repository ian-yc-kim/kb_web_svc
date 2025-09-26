"""Unit tests for the delete_task service function.

These tests verify the delete_task function functionality including
soft deletion, hard deletion, error handling, and transaction management.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.task import TaskCreate
from kb_web_svc.services.task_service import (
    create_task,
    delete_task,
    TaskNotFoundError
)


class TestDeleteTask:
    """Test cases for the delete_task service function."""

    def test_soft_delete_existing_task_success(self, db_session: Session):
        """Test successful soft deletion of an existing task."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task to be soft deleted",
            assignee="John Doe",
            priority="High",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Capture original last_modified timestamp
        original_last_modified = created_task['last_modified']
        
        # Wait a brief moment to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Perform soft delete
        result = delete_task(task_id, soft=True, db=db_session)
        
        # Verify response structure and content
        assert isinstance(result, dict)
        assert result["message"] == "Task soft-deleted successfully"
        assert result["task_id"] == str(task_id)
        
        # Fetch task from database to verify soft deletion
        db_task = db_session.get(Task, task_id)
        assert db_task is not None  # Task still exists in database
        assert db_task.deleted_at is not None  # deleted_at is set
        assert isinstance(db_task.deleted_at, datetime)
        
        # Verify deleted_at is recent (within last few seconds)
        now = datetime.now(timezone.utc)
        time_diff = now - db_task.deleted_at.replace(tzinfo=timezone.utc)
        assert time_diff.total_seconds() < 5  # Should be very recent
        
        # Verify last_modified was updated (automatic via event listener)
        current_last_modified = db_task.last_modified.isoformat()
        assert current_last_modified != original_last_modified
        
        # Verify other fields remain unchanged
        assert db_task.title == "Task to be soft deleted"
        assert db_task.assignee == "John Doe"
        assert db_task.priority == Priority.HIGH
        assert db_task.status == Status.IN_PROGRESS

    def test_hard_delete_existing_task_success(self, db_session: Session):
        """Test successful hard deletion of an existing task."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task to be hard deleted",
            assignee="Jane Smith",
            priority="Low",
            status="Done"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Verify task exists before deletion
        db_task_before = db_session.get(Task, task_id)
        assert db_task_before is not None
        
        # Perform hard delete
        result = delete_task(task_id, soft=False, db=db_session)
        
        # Verify response structure and content
        assert isinstance(result, dict)
        assert result["message"] == "Task hard-deleted successfully"
        assert result["task_id"] == str(task_id)
        
        # Verify task is completely removed from database
        db_task_after = db_session.get(Task, task_id)
        assert db_task_after is None  # Task no longer exists
        
        # Verify task cannot be found via query either
        query_result = db_session.query(Task).filter(Task.id == task_id).first()
        assert query_result is None

    def test_delete_nonexistent_task_raises_task_not_found_error(self, db_session: Session):
        """Test that attempting to delete a non-existent task raises TaskNotFoundError."""
        # Generate a random UUID that doesn't exist in database
        nonexistent_task_id = uuid.uuid4()
        
        # Verify task doesn't exist
        db_task = db_session.get(Task, nonexistent_task_id)
        assert db_task is None
        
        # Attempt soft delete - should raise TaskNotFoundError
        with pytest.raises(TaskNotFoundError) as exc_info:
            delete_task(nonexistent_task_id, soft=True, db=db_session)
        
        # Verify error message contains the task ID
        error_msg = str(exc_info.value)
        assert f"Task with ID {nonexistent_task_id} not found" in error_msg
        
        # Attempt hard delete - should also raise TaskNotFoundError
        with pytest.raises(TaskNotFoundError) as exc_info:
            delete_task(nonexistent_task_id, soft=False, db=db_session)
        
        # Verify error message contains the task ID
        error_msg = str(exc_info.value)
        assert f"Task with ID {nonexistent_task_id} not found" in error_msg

    def test_soft_delete_transaction_rollback_on_error(self, db_session: Session, monkeypatch):
        """Test that transaction rollback occurs on database error during soft delete."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task for rollback test",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Verify task exists and is not soft-deleted
        db_task_before = db_session.get(Task, task_id)
        assert db_task_before is not None
        assert db_task_before.deleted_at is None
        
        # Mock db_session.commit to raise an exception
        original_commit = db_session.commit
        def mock_commit():
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'commit', mock_commit)
        
        # Attempt soft delete - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            delete_task(task_id, soft=True, db=db_session)
        
        # Restore original commit for verification
        monkeypatch.setattr(db_session, 'commit', original_commit)
        
        # Verify rollback happened - task should remain not soft-deleted
        db_task_after = db_session.get(Task, task_id)
        assert db_task_after is not None  # Task still exists
        assert db_task_after.deleted_at is None  # deleted_at is still None
        
        # Verify task data is unchanged
        assert db_task_after.title == "Task for rollback test"
        assert db_task_after.status == Status.TODO

    def test_hard_delete_transaction_rollback_on_error(self, db_session: Session, monkeypatch):
        """Test that transaction rollback occurs on database error during hard delete."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task for hard delete rollback test",
            assignee="Test User",
            status="Done"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Verify task exists before deletion attempt
        db_task_before = db_session.get(Task, task_id)
        assert db_task_before is not None
        assert db_task_before.title == "Task for hard delete rollback test"
        
        # Mock db_session.commit to raise an exception
        original_commit = db_session.commit
        def mock_commit():
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'commit', mock_commit)
        
        # Attempt hard delete - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            delete_task(task_id, soft=False, db=db_session)
        
        # Restore original commit for verification
        monkeypatch.setattr(db_session, 'commit', original_commit)
        
        # Verify rollback happened - task should still exist unchanged
        db_task_after = db_session.get(Task, task_id)
        assert db_task_after is not None  # Task still exists
        assert db_task_after.title == "Task for hard delete rollback test"
        assert db_task_after.assignee == "Test User"
        assert db_task_after.status == Status.DONE
        
        # Verify task can still be queried
        query_result = db_session.query(Task).filter(Task.id == task_id).first()
        assert query_result is not None
        assert query_result.title == "Task for hard delete rollback test"

    def test_soft_delete_sets_deleted_at_timestamp(self, db_session: Session):
        """Test that soft delete properly sets deleted_at timestamp."""
        # Create a task
        task_data = TaskCreate(
            title="Timestamp test task",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Record time before deletion
        time_before_deletion = datetime.now(timezone.utc)
        
        # Perform soft delete
        result = delete_task(task_id, soft=True, db=db_session)
        
        # Record time after deletion
        time_after_deletion = datetime.now(timezone.utc)
        
        # Verify response
        assert result["message"] == "Task soft-deleted successfully"
        
        # Fetch task and verify deleted_at timestamp
        db_task = db_session.get(Task, task_id)
        assert db_task.deleted_at is not None
        
        # Handle timezone-naive datetime from SQLite
        deleted_at = db_task.deleted_at
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=timezone.utc)
        
        # Verify deleted_at is within reasonable time range
        assert time_before_deletion <= deleted_at <= time_after_deletion
        
        # Verify it's a proper datetime object
        assert isinstance(deleted_at, datetime)

    def test_hard_delete_removes_task_completely(self, db_session: Session):
        """Test that hard delete completely removes task from database."""
        # Create multiple tasks
        task_data_1 = TaskCreate(title="Task 1", status="To Do")
        task_data_2 = TaskCreate(title="Task 2", status="In Progress")
        task_data_3 = TaskCreate(title="Task 3", status="Done")
        
        created_task_1 = create_task(task_data_1, db_session)
        created_task_2 = create_task(task_data_2, db_session)
        created_task_3 = create_task(task_data_3, db_session)
        
        task_id_1 = uuid.UUID(created_task_1['id'])
        task_id_2 = uuid.UUID(created_task_2['id'])
        task_id_3 = uuid.UUID(created_task_3['id'])
        
        # Verify all tasks exist
        assert db_session.get(Task, task_id_1) is not None
        assert db_session.get(Task, task_id_2) is not None
        assert db_session.get(Task, task_id_3) is not None
        
        # Count total tasks
        total_tasks_before = db_session.query(Task).count()
        assert total_tasks_before == 3
        
        # Hard delete the middle task
        result = delete_task(task_id_2, soft=False, db=db_session)
        
        # Verify response
        assert result["message"] == "Task hard-deleted successfully"
        assert result["task_id"] == str(task_id_2)
        
        # Verify only the targeted task is removed
        assert db_session.get(Task, task_id_1) is not None  # Still exists
        assert db_session.get(Task, task_id_2) is None       # Deleted
        assert db_session.get(Task, task_id_3) is not None  # Still exists
        
        # Verify total count decreased by 1
        total_tasks_after = db_session.query(Task).count()
        assert total_tasks_after == 2
        
        # Verify remaining tasks are correct ones
        remaining_tasks = db_session.query(Task).all()
        remaining_ids = [task.id for task in remaining_tasks]
        assert task_id_1 in remaining_ids
        assert task_id_2 not in remaining_ids
        assert task_id_3 in remaining_ids

    def test_delete_task_default_soft_parameter(self, db_session: Session):
        """Test that delete_task defaults to soft=True when soft parameter is not provided."""
        # Create a task
        task_data = TaskCreate(
            title="Default parameter test",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Call delete_task without specifying soft parameter
        result = delete_task(task_id, db=db_session)  # soft parameter omitted, should default to True
        
        # Verify it performed soft delete
        assert result["message"] == "Task soft-deleted successfully"
        
        # Verify task still exists but is soft-deleted
        db_task = db_session.get(Task, task_id)
        assert db_task is not None  # Task still exists
        assert db_task.deleted_at is not None  # But is soft-deleted

    def test_delete_task_last_modified_updated_on_soft_delete(self, db_session: Session):
        """Test that last_modified is updated during soft delete operations."""
        # Create a task
        task_data = TaskCreate(
            title="Last modified test",
            assignee="Test User",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Get original last_modified timestamp
        original_last_modified = datetime.fromisoformat(created_task['last_modified'])
        
        # Wait a brief moment to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Perform soft delete
        delete_task(task_id, soft=True, db=db_session)
        
        # Fetch updated task
        db_task = db_session.get(Task, task_id)
        
        # Convert to timezone-aware datetime for comparison
        updated_last_modified = db_task.last_modified
        if updated_last_modified.tzinfo is None:
            updated_last_modified = updated_last_modified.replace(tzinfo=timezone.utc)
        
        if original_last_modified.tzinfo is None:
            original_last_modified = original_last_modified.replace(tzinfo=timezone.utc)
        
        # Verify last_modified was updated (soft delete is an update operation)
        assert updated_last_modified > original_last_modified
        
        # Verify last_modified is different from deleted_at (should be same or very close, but checking they're both set)
        assert db_task.deleted_at is not None
        assert db_task.last_modified is not None

    def test_delete_task_preserves_task_data_on_soft_delete(self, db_session: Session):
        """Test that soft delete preserves all task data except deleted_at and last_modified."""
        # Create a comprehensive task with all fields
        task_data = TaskCreate(
            title="Comprehensive test task",
            assignee="Alice Johnson",
            due_date=datetime.now().date() + timedelta(days=7),
            description="This is a detailed task description for testing",
            priority="Critical",
            labels=["testing", "critical", "preserve-data"],
            estimated_time=8.0,  # Fixed: changed from 12.5 to 8.0 to comply with validation constraint
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Capture original timestamp values before operation
        db_task_before = db_session.get(Task, task_id)
        original_last_modified_value = db_task_before.last_modified
        
        # Verify task exists with expected data
        assert db_task_before.deleted_at is None
        
        # Wait a brief moment to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Perform soft delete
        delete_task(task_id, soft=True, db=db_session)
        
        # Fetch task after soft delete
        db_task_after = db_session.get(Task, task_id)
        
        # Verify task still exists
        assert db_task_after is not None
        
        # Verify deleted_at is now set
        assert db_task_after.deleted_at is not None
        
        # Verify last_modified was updated by comparing with captured original value
        assert db_task_after.last_modified != original_last_modified_value
        
        # Verify all other data is preserved
        assert db_task_after.id == db_task_before.id
        assert db_task_after.title == "Comprehensive test task"
        assert db_task_after.assignee == "Alice Johnson"
        assert db_task_after.due_date == db_task_before.due_date
        assert db_task_after.description == "This is a detailed task description for testing"
        assert db_task_after.priority == Priority.CRITICAL
        assert db_task_after.labels == ["testing", "critical", "preserve-data"]
        assert db_task_after.estimated_time == 8.0  # Updated expected value to match fix
        assert db_task_after.status == Status.IN_PROGRESS
        assert db_task_after.created_at == db_task_before.created_at