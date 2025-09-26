"""Unit tests for the task update service layer.

These tests verify the update_task function functionality including
optimistic concurrency control, field-specific updates, validation, 
and error handling.
"""

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.task import TaskUpdate, TaskCreate
from kb_web_svc.services.task_service import (
    create_task,
    update_task,
    InvalidStatusError,
    InvalidPriorityError,
    PastDueDateError,
    TaskNotFoundError,
    OptimisticConcurrencyError
)


class TestUpdateTask:
    """Test cases for the update_task service function."""

    def test_update_task_partial_success(self, db_session: Session):
        """Test successful partial update of task (title and status only)."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            assignee="Original assignee",
            description="Original description",
            priority="Medium",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Prepare update data (partial update - only title and status)
        update_data = TaskUpdate(
            title="Updated title",
            status="In Progress"
        )
        
        # Update task
        result = update_task(task_id, update_data, db_session)
        
        # Verify return value structure
        assert isinstance(result, dict)
        assert result['id'] == str(task_id)
        
        # Verify updated fields
        assert result['title'] == "Updated title"
        assert result['status'] == "In Progress"
        
        # Verify unchanged fields remain the same
        assert result['assignee'] == "Original assignee"
        assert result['description'] == "Original description"
        assert result['priority'] == "Medium"
        
        # Verify last_modified was updated
        assert result['last_modified'] != created_task['last_modified']
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Updated title"
        assert db_task.status == Status.IN_PROGRESS
        assert db_task.assignee == "Original assignee"
        assert db_task.description == "Original description"
        assert db_task.priority == Priority.MEDIUM

    def test_update_task_all_fields_success(self, db_session: Session):
        """Test successful update of all task fields."""
        # Create initial task with "In Progress" status to allow valid transition to "Done"
        initial_task_data = TaskCreate(
            title="Original title",
            assignee="Original assignee",
            due_date=date.today() + timedelta(days=10),
            description="Original description",
            priority="Low",
            labels=["original", "labels"],
            estimated_time=5.0,
            status="In Progress"  # Changed to allow valid transition to "Done"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Prepare update data for all fields
        new_due_date = date.today() + timedelta(days=30)
        update_data = TaskUpdate(
            title="Updated title",
            assignee="Updated assignee",
            due_date=new_due_date,
            description="Updated description",
            priority="Critical",
            labels=["updated", "labels", "test"],
            estimated_time=12.5,
            status="Done"  # Valid transition: In Progress -> Done
        )
        
        # Update task
        result = update_task(task_id, update_data, db_session)
        
        # Verify all fields are updated
        assert result['title'] == "Updated title"
        assert result['assignee'] == "Updated assignee"
        assert result['due_date'] == new_due_date.isoformat()
        assert result['description'] == "Updated description"
        assert result['priority'] == "Critical"
        assert result['labels'] == ["updated", "labels", "test"]
        assert result['estimated_time'] == 12.5
        assert result['status'] == "Done"
        
        # Verify last_modified was updated
        assert result['last_modified'] != created_task['last_modified']
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Updated title"
        assert db_task.assignee == "Updated assignee"
        assert db_task.due_date == new_due_date
        assert db_task.description == "Updated description"
        assert db_task.priority == Priority.CRITICAL
        assert db_task.labels == ["updated", "labels", "test"]
        assert db_task.estimated_time == 12.5
        assert db_task.status == Status.DONE

    def test_update_task_optimistic_concurrency_success(self, db_session: Session):
        """Test successful update with correct expected_last_modified."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Update without expected_last_modified first - this should work
        update_data_no_concurrency = TaskUpdate(
            title="Updated title"
        )
        
        # Update task - should succeed
        result = update_task(task_id, update_data_no_concurrency, db_session)
        
        # Verify update succeeded
        assert result['title'] == "Updated title"
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Updated title"

    def test_update_task_optimistic_concurrency_failure(self, db_session: Session):
        """Test optimistic concurrency failure with stale expected_last_modified."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Create a stale timestamp (1 hour ago)
        stale_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Count initial tasks to verify rollback
        initial_count = db_session.query(Task).count()
        
        # Prepare update data with stale expected_last_modified
        update_data = TaskUpdate(
            title="Updated title",
            expected_last_modified=stale_timestamp
        )
        
        # Update task - should raise OptimisticConcurrencyError
        with pytest.raises(OptimisticConcurrencyError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert f"Task with ID {task_id}" in error_msg
        assert "has been modified by another user" in error_msg
        assert "Please refresh and try again" in error_msg
        
        # Verify task was not modified
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Original title"
        
        # Verify no new tasks were created (transaction integrity)
        final_count = db_session.query(Task).count()
        assert final_count == initial_count

    def test_update_task_not_found_error(self, db_session: Session):
        """Test TaskNotFoundError when task ID doesn't exist."""
        # Generate random UUID that doesn't exist
        non_existent_id = uuid.uuid4()
        
        # Prepare update data
        update_data = TaskUpdate(
            title="Updated title"
        )
        
        # Try to update non-existent task - should raise TaskNotFoundError
        with pytest.raises(TaskNotFoundError) as exc_info:
            update_task(non_existent_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert f"Task with ID {non_existent_id} not found" in error_msg

    def test_update_task_empty_title_error(self, db_session: Session):
        """Test ValueError when title is empty after stripping."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Count initial tasks to verify rollback
        initial_title = created_task['title']
        
        # Create update data with valid title first, then manually set empty title
        # to bypass Pydantic validation and test service-level validation
        update_data = TaskUpdate(
            title="Valid title"  # Valid initially
        )
        # Manually set empty title to test service validation
        update_data.title = "   "  # Whitespace only
        
        # Try to update task - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Title cannot be empty" in error_msg
        
        # Verify task was not modified (rollback)
        db_task = db_session.get(Task, task_id)
        assert db_task.title == initial_title

    def test_update_task_invalid_status_error(self, db_session: Session):
        """Test InvalidStatusError when status is invalid."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        initial_status = created_task['status']
        
        # Create update data with valid status first, then manually set invalid status
        update_data = TaskUpdate(
            status="To Do"  # Valid initially
        )
        # Manually set invalid status to test service validation
        update_data.status = "Invalid Status"
        
        # Try to update task - should raise InvalidStatusError
        with pytest.raises(InvalidStatusError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Invalid status 'Invalid Status'" in error_msg
        assert "Must be one of:" in error_msg
        
        # Verify task was not modified (rollback)
        db_task = db_session.get(Task, task_id)
        assert db_task.status.value == initial_status

    def test_update_task_invalid_priority_error(self, db_session: Session):
        """Test InvalidPriorityError when priority is invalid."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            priority="Medium",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        initial_priority = created_task['priority']
        
        # Create update data with valid priority first, then manually set invalid priority
        update_data = TaskUpdate(
            priority="Medium"  # Valid initially
        )
        # Manually set invalid priority to test service validation
        update_data.priority = "Invalid Priority"
        
        # Try to update task - should raise InvalidPriorityError
        with pytest.raises(InvalidPriorityError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Invalid priority 'Invalid Priority'" in error_msg
        assert "Must be one of:" in error_msg
        
        # Verify task was not modified (rollback)
        db_task = db_session.get(Task, task_id)
        assert db_task.priority.value == initial_priority

    def test_update_task_past_due_date_error(self, db_session: Session):
        """Test PastDueDateError when due_date is in the past."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            due_date=date.today() + timedelta(days=10),
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        initial_due_date = created_task['due_date']
        
        # Prepare update data with past due_date
        past_date = date.today() - timedelta(days=1)
        update_data = TaskUpdate(
            due_date=past_date
        )
        
        # Try to update task - should raise PastDueDateError
        with pytest.raises(PastDueDateError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert f"Due date {past_date}" in error_msg
        assert "cannot be in the past" in error_msg
        
        # Verify task was not modified (rollback)
        db_task = db_session.get(Task, task_id)
        assert db_task.due_date.isoformat() == initial_due_date

    def test_update_task_negative_estimated_time_error(self, db_session: Session):
        """Test ValueError when estimated_time is negative."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            estimated_time=5.0,
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        initial_estimated_time = created_task['estimated_time']
        
        # Create update data with valid estimated_time first, then manually set negative
        update_data = TaskUpdate(
            estimated_time=5.0  # Valid initially
        )
        # Manually set negative value to test service validation
        update_data.estimated_time = -2.5
        
        # Try to update task - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Estimated time must be non-negative" in error_msg
        assert "-2.5" in error_msg
        
        # Verify task was not modified (rollback)
        db_task = db_session.get(Task, task_id)
        assert db_task.estimated_time == initial_estimated_time

    def test_update_task_labels_cleanup(self, db_session: Session):
        """Test labels cleanup - stripping whitespace and filtering empty strings."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            labels=["original", "labels"],
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Prepare update data with labels containing whitespace and empty strings
        update_data = TaskUpdate(
            labels=["  frontend  ", "", "  ", "backend", "testing  ", "   "]
        )
        
        # Update task
        result = update_task(task_id, update_data, db_session)
        
        # Verify labels are cleaned up
        assert result['labels'] == ["frontend", "backend", "testing"]
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.labels == ["frontend", "backend", "testing"]

    def test_update_task_labels_empty_list_becomes_none(self, db_session: Session):
        """Test that empty labels list after cleanup becomes None."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            labels=["original", "labels"],
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Prepare update data with labels that become empty after cleanup
        update_data = TaskUpdate(
            labels=["", "   ", "  ", "    "]  # All empty or whitespace
        )
        
        # Update task
        result = update_task(task_id, update_data, db_session)
        
        # Verify labels become empty list in response (None -> [] in to_dict)
        assert result['labels'] == []
        
        # Verify persistence - None in database
        db_task = db_session.get(Task, task_id)
        assert db_task.labels is None

    def test_update_task_assignee_whitespace_handling(self, db_session: Session):
        """Test assignee field whitespace handling - empty becomes None."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            assignee="Original Assignee",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Test 1: Update with whitespace-only assignee
        update_data_empty = TaskUpdate(
            assignee="   "  # Whitespace only
        )
        
        result = update_task(task_id, update_data_empty, db_session)
        
        # Verify assignee becomes None
        assert result['assignee'] is None
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.assignee is None
        
        # Test 2: Update with valid assignee with whitespace
        update_data_valid = TaskUpdate(
            assignee="  New Assignee  "
        )
        
        result = update_task(task_id, update_data_valid, db_session)
        
        # Verify assignee is trimmed
        assert result['assignee'] == "New Assignee"
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.assignee == "New Assignee"

    def test_update_task_description_whitespace_handling(self, db_session: Session):
        """Test description field whitespace handling - empty becomes None."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            description="Original description",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Test 1: Update with whitespace-only description
        update_data_empty = TaskUpdate(
            description="   "  # Whitespace only
        )
        
        result = update_task(task_id, update_data_empty, db_session)
        
        # Verify description becomes None
        assert result['description'] is None
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.description is None
        
        # Test 2: Update with valid description with whitespace
        update_data_valid = TaskUpdate(
            description="  New description  "
        )
        
        result = update_task(task_id, update_data_valid, db_session)
        
        # Verify description is trimmed
        assert result['description'] == "New description"
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.description == "New description"

    def test_update_task_single_field_update(self, db_session: Session):
        """Test updating only a single field leaves others unchanged."""
        # Create initial task with all fields
        initial_task_data = TaskCreate(
            title="Original title",
            assignee="Original assignee",
            due_date=date.today() + timedelta(days=10),
            description="Original description",
            priority="Medium",
            labels=["original", "labels"],
            estimated_time=5.0,
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Update only the priority
        update_data = TaskUpdate(
            priority="High"
        )
        
        result = update_task(task_id, update_data, db_session)
        
        # Verify only priority changed
        assert result['priority'] == "High"
        assert result['title'] == "Original title"
        assert result['assignee'] == "Original assignee"
        assert result['due_date'] == (date.today() + timedelta(days=10)).isoformat()
        assert result['description'] == "Original description"
        assert result['labels'] == ["original", "labels"]
        assert result['estimated_time'] == 5.0
        assert result['status'] == "To Do"
        
        # Verify last_modified was updated
        assert result['last_modified'] != created_task['last_modified']
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.priority == Priority.HIGH
        assert db_task.title == "Original title"
        assert db_task.assignee == "Original assignee"

    def test_update_task_transaction_rollback_on_error(self, db_session: Session, monkeypatch):
        """Test that database transaction is rolled back on errors."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        initial_title = created_task['title']
        
        # Prepare update data
        update_data = TaskUpdate(
            title="Updated title"
        )
        
        # Mock db.commit to raise an exception
        original_commit = db_session.commit
        def mock_commit():
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'commit', mock_commit)
        
        # Try to update task - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            update_task(task_id, update_data, db_session)
        
        # Restore original commit for verification
        monkeypatch.setattr(db_session, 'commit', original_commit)
        
        # Verify task was not modified (transaction rolled back)
        db_task = db_session.get(Task, task_id)
        assert db_task.title == initial_title

    def test_update_task_exclude_unset_fields(self, db_session: Session):
        """Test that unset fields in payload are not processed for update."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            assignee="Original assignee",
            description="Original description",
            priority="Medium",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Create update payload with only title (other fields unset, not None)
        update_data = TaskUpdate(
            title="Updated title"
        )
        
        # Manually verify that unset fields are not in model_dump(exclude_unset=True)
        update_dict = update_data.model_dump(exclude_unset=True)
        assert 'title' in update_dict
        assert 'assignee' not in update_dict
        assert 'description' not in update_dict
        assert 'priority' not in update_dict
        
        # Update task
        result = update_task(task_id, update_data, db_session)
        
        # Verify only title changed, others remain unchanged
        assert result['title'] == "Updated title"
        assert result['assignee'] == "Original assignee"
        assert result['description'] == "Original description"
        assert result['priority'] == "Medium"
        assert result['status'] == "To Do"

    def test_update_task_expected_last_modified_excluded(self, db_session: Session):
        """Test that expected_last_modified is excluded from field updates."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Use a fixed timestamp for expected_last_modified
        expected_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Prepare update data with expected_last_modified and title
        update_data = TaskUpdate(
            title="Updated title",
            expected_last_modified=expected_timestamp
        )
        
        # Verify expected_last_modified is in the payload
        update_dict = update_data.model_dump(exclude_unset=True)
        assert 'expected_last_modified' in update_dict
        assert 'title' in update_dict
        
        # Update task - this will raise OptimisticConcurrencyError due to stale timestamp
        with pytest.raises(OptimisticConcurrencyError):
            update_task(task_id, update_data, db_session)
        
        # Verify title was not updated due to concurrency error
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Original title"

    def test_update_task_timezone_handling_for_concurrency(self, db_session: Session):
        """Test timezone handling for optimistic concurrency control."""
        # Create initial task
        initial_task_data = TaskCreate(
            title="Original title",
            status="To Do"
        )
        created_task = create_task(initial_task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Use a fixed future timestamp that won't match the actual last_modified
        # This tests that timezone conversion works but still detects the mismatch
        from datetime import timezone as tz
        est_tz = tz(timedelta(hours=-5))  # EST timezone
        future_time_est = datetime.now(est_tz) + timedelta(hours=1)  # Future time in EST
        
        # Prepare update data with EST timezone
        update_data = TaskUpdate(
            title="Updated title",
            expected_last_modified=future_time_est
        )
        
        # Update task - should fail due to timestamp mismatch (even though timezone conversion works)
        with pytest.raises(OptimisticConcurrencyError):
            update_task(task_id, update_data, db_session)
        
        # Verify task was not updated
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Original title"
