"""Unit tests for status transition validation in task service.

These tests verify that the task update service properly validates
status transitions according to business rules and raises appropriate
exceptions for invalid transitions.
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Status
from kb_web_svc.schemas.task import TaskCreate, TaskUpdate
from kb_web_svc.services.task_service import (
    create_task,
    update_task,
    InvalidStatusTransitionError
)


class TestStatusTransitionValidation:
    """Test cases for status transition validation in update_task."""

    def create_task_with_status(self, db_session: Session, status: str) -> dict:
        """Helper method to create a task with a specific status."""
        task_data = TaskCreate(
            title=f"Test task - {status}",
            status=status
        )
        return create_task(task_data, db_session)

    # Test allowed transitions

    def test_todo_to_in_progress_success(self, db_session: Session):
        """Test successful transition from To Do to In Progress."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update status to In Progress
        update_data = TaskUpdate(status="In Progress")
        result = update_task(task_id, update_data, db_session)
        
        # Verify successful transition
        assert result['status'] == "In Progress"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.IN_PROGRESS

    def test_in_progress_to_done_success(self, db_session: Session):
        """Test successful transition from In Progress to Done."""
        # Create task in In Progress status
        created_task = self.create_task_with_status(db_session, "In Progress")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update status to Done
        update_data = TaskUpdate(status="Done")
        result = update_task(task_id, update_data, db_session)
        
        # Verify successful transition
        assert result['status'] == "Done"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.DONE

    def test_in_progress_to_todo_success(self, db_session: Session):
        """Test successful transition from In Progress to To Do (undo operation)."""
        # Create task in In Progress status
        created_task = self.create_task_with_status(db_session, "In Progress")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update status to To Do
        update_data = TaskUpdate(status="To Do")
        result = update_task(task_id, update_data, db_session)
        
        # Verify successful transition
        assert result['status'] == "To Do"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.TODO

    def test_done_to_in_progress_success(self, db_session: Session):
        """Test successful transition from Done to In Progress (undo operation)."""
        # Create task in Done status
        created_task = self.create_task_with_status(db_session, "Done")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update status to In Progress
        update_data = TaskUpdate(status="In Progress")
        result = update_task(task_id, update_data, db_session)
        
        # Verify successful transition
        assert result['status'] == "In Progress"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.IN_PROGRESS

    def test_done_to_todo_success(self, db_session: Session):
        """Test successful transition from Done to To Do (undo operation)."""
        # Create task in Done status
        created_task = self.create_task_with_status(db_session, "Done")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update status to To Do
        update_data = TaskUpdate(status="To Do")
        result = update_task(task_id, update_data, db_session)
        
        # Verify successful transition
        assert result['status'] == "To Do"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.TODO

    # Test disallowed transitions

    def test_todo_to_done_invalid_transition(self, db_session: Session):
        """Test invalid transition from To Do directly to Done."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        original_status = created_task['status']
        original_last_modified = created_task['last_modified']
        
        # Attempt invalid transition to Done
        update_data = TaskUpdate(status="Done")
        
        # Should raise InvalidStatusTransitionError
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "Invalid status transition from 'To Do' to 'Done'" in error_msg
        assert "Allowed transitions from 'To Do' are: ['In Progress']" in error_msg
        
        # Verify task status and timestamp remain unchanged
        db_task = db_session.get(Task, task_id)
        assert db_task.status.value == original_status
        assert db_task.last_modified.isoformat() == original_last_modified

    # Test no-op transitions (same status)

    def test_todo_to_todo_no_op_success(self, db_session: Session):
        """Test that updating to the same status (To Do -> To Do) is allowed."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update to the same status
        update_data = TaskUpdate(status="To Do")
        result = update_task(task_id, update_data, db_session)
        
        # Verify operation succeeds
        assert result['status'] == "To Do"
        # Note: last_modified should still be updated due to the update operation
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.TODO

    def test_in_progress_to_in_progress_no_op_success(self, db_session: Session):
        """Test that updating to the same status (In Progress -> In Progress) is allowed."""
        # Create task in In Progress status
        created_task = self.create_task_with_status(db_session, "In Progress")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update to the same status
        update_data = TaskUpdate(status="In Progress")
        result = update_task(task_id, update_data, db_session)
        
        # Verify operation succeeds
        assert result['status'] == "In Progress"
        # Note: last_modified should still be updated due to the update operation
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.IN_PROGRESS

    def test_done_to_done_no_op_success(self, db_session: Session):
        """Test that updating to the same status (Done -> Done) is allowed."""
        # Create task in Done status
        created_task = self.create_task_with_status(db_session, "Done")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update to the same status
        update_data = TaskUpdate(status="Done")
        result = update_task(task_id, update_data, db_session)
        
        # Verify operation succeeds
        assert result['status'] == "Done"
        # Note: last_modified should still be updated due to the update operation
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.DONE

    # Test updates without status in payload

    def test_update_without_status_no_transition_validation(self, db_session: Session):
        """Test that updates without status field do not trigger transition validation."""
        # Create task in any status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        original_status = created_task['status']
        
        # Update only title (no status in payload)
        update_data = TaskUpdate(title="Updated title without status change")
        result = update_task(task_id, update_data, db_session)
        
        # Verify update succeeds and status remains unchanged
        assert result['title'] == "Updated title without status change"
        assert result['status'] == original_status
        
        # Verify persistence in database
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Updated title without status change"
        assert db_task.status.value == original_status

    # Test comprehensive status transition matrix

    def test_all_invalid_transitions(self, db_session: Session):
        """Test all invalid status transitions to ensure they are properly blocked."""
        # Define all invalid transitions
        invalid_transitions = [
            ("To Do", "Done"),  # Only invalid transition since others are covered above
        ]
        
        for from_status, to_status in invalid_transitions:
            # Create task with initial status
            created_task = self.create_task_with_status(db_session, from_status)
            task_id = uuid.UUID(created_task['id'])
            original_status = created_task['status']
            original_last_modified = created_task['last_modified']
            
            # Attempt invalid transition
            update_data = TaskUpdate(status=to_status)
            
            with pytest.raises(InvalidStatusTransitionError) as exc_info:
                update_task(task_id, update_data, db_session)
            
            # Verify error message format
            error_msg = str(exc_info.value)
            assert f"Invalid status transition from '{from_status}' to '{to_status}'" in error_msg
            assert f"Allowed transitions from '{from_status}' are:" in error_msg
            
            # Verify task remains unchanged
            db_task = db_session.get(Task, task_id)
            assert db_task.status.value == original_status
            assert db_task.last_modified.isoformat() == original_last_modified

    # Test transition validation with optimistic concurrency control

    def test_status_transition_with_optimistic_concurrency_success(self, db_session: Session):
        """Test valid status transition combined with optimistic concurrency control."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        
        # Parse the last_modified timestamp
        expected_last_modified = datetime.fromisoformat(created_task['last_modified'])
        if expected_last_modified.tzinfo is None:
            expected_last_modified = expected_last_modified.replace(tzinfo=timezone.utc)
        
        # Update with valid transition and correct expected_last_modified
        update_data = TaskUpdate(
            status="In Progress",
            expected_last_modified=expected_last_modified
        )
        
        result = update_task(task_id, update_data, db_session)
        
        # Verify both transition and concurrency control work
        assert result['status'] == "In Progress"
        assert result['last_modified'] != created_task['last_modified']
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.IN_PROGRESS

    def test_invalid_status_transition_with_optimistic_concurrency_failure(self, db_session: Session):
        """Test that invalid status transition is caught even with correct optimistic concurrency."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        
        # Parse the last_modified timestamp
        expected_last_modified = datetime.fromisoformat(created_task['last_modified'])
        if expected_last_modified.tzinfo is None:
            expected_last_modified = expected_last_modified.replace(tzinfo=timezone.utc)
        
        # Attempt invalid transition with correct expected_last_modified
        update_data = TaskUpdate(
            status="Done",  # Invalid: To Do -> Done
            expected_last_modified=expected_last_modified
        )
        
        # Should raise InvalidStatusTransitionError (not OptimisticConcurrencyError)
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            update_task(task_id, update_data, db_session)
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Invalid status transition from 'To Do' to 'Done'" in error_msg
        
        # Verify task remains unchanged
        db_task = db_session.get(Task, task_id)
        assert db_task.status == Status.TODO
        assert db_task.last_modified.isoformat() == created_task['last_modified']

    # Test multiple field updates with status transition

    def test_multiple_field_update_with_valid_status_transition(self, db_session: Session):
        """Test updating multiple fields including a valid status transition."""
        # Create task in To Do status
        created_task = self.create_task_with_status(db_session, "To Do")
        task_id = uuid.UUID(created_task['id'])
        original_last_modified = created_task['last_modified']
        
        # Update multiple fields including valid status transition
        update_data = TaskUpdate(
            title="Updated title with status change",
            assignee="New Assignee",
            priority="High",
            status="In Progress"  # Valid transition
        )
        
        result = update_task(task_id, update_data, db_session)
        
        # Verify all updates succeeded
        assert result['title'] == "Updated title with status change"
        assert result['assignee'] == "New Assignee"
        assert result['priority'] == "High"
        assert result['status'] == "In Progress"
        assert result['last_modified'] != original_last_modified
        
        # Verify persistence
        db_task = db_session.get(Task, task_id)
        assert db_task.title == "Updated title with status change"
        assert db_task.assignee == "New Assignee"
        assert db_task.priority.value == "High"
        assert db_task.status == Status.IN_PROGRESS

    def test_multiple_field_update_with_invalid_status_transition_rollback(self, db_session: Session):
        """Test that invalid status transition rolls back all field updates."""
        # Create task in To Do status with initial values
        task_data = TaskCreate(
            title="Original title",
            assignee="Original assignee",
            priority="Low",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Store original values
        original_title = created_task['title']
        original_assignee = created_task['assignee']
        original_priority = created_task['priority']
        original_status = created_task['status']
        original_last_modified = created_task['last_modified']
        
        # Attempt to update multiple fields with invalid status transition
        update_data = TaskUpdate(
            title="Should not be updated",
            assignee="Should not be updated",
            priority="High",
            status="Done"  # Invalid transition: To Do -> Done
        )
        
        # Should raise InvalidStatusTransitionError
        with pytest.raises(InvalidStatusTransitionError):
            update_task(task_id, update_data, db_session)
        
        # Verify ALL fields remain unchanged (transaction rolled back)
        db_task = db_session.get(Task, task_id)
        assert db_task.title == original_title
        assert db_task.assignee == original_assignee
        assert db_task.priority.value == original_priority
        assert db_task.status.value == original_status
        assert db_task.last_modified.isoformat() == original_last_modified
