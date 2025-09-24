"""Unit tests for the Task SQLAlchemy ORM model.

These tests verify the Task model functionality including field validation,
enum constraints, automatic timestamp management, and serialization.
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import List

import pytest
from sqlalchemy.exc import IntegrityError

from kb_web_svc.models.task import Task, Priority, Status


class TestTaskModel:
    """Test cases for the Task ORM model functionality."""

    def test_task_creation_and_retrieval(self, db_session):
        """Test basic Task model creation, saving, and retrieval."""
        # Create a task with all fields
        task = Task(
            title="Test Task",
            assignee="John Doe",
            due_date=date(2024, 12, 31),
            description="This is a test task",
            priority=Priority.HIGH,
            labels=["urgent", "frontend"],
            estimated_time=8.5,
            status=Status.TODO
        )
        
        # Save to database
        db_session.add(task)
        db_session.commit()
        
        # Verify task was saved and can be retrieved
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task is not None
        assert retrieved_task.title == "Test Task"
        assert retrieved_task.assignee == "John Doe"
        assert retrieved_task.due_date == date(2024, 12, 31)
        assert retrieved_task.description == "This is a test task"
        assert retrieved_task.priority == Priority.HIGH
        assert retrieved_task.labels == ["urgent", "frontend"]
        assert retrieved_task.estimated_time == 8.5
        assert retrieved_task.status == Status.TODO
        assert isinstance(retrieved_task.id, uuid.UUID)

    def test_task_required_fields_title(self, db_session):
        """Test that title field is required and cannot be null."""
        # Try to create task without title
        task = Task(
            status=Status.TODO
        )
        
        db_session.add(task)
        
        # Should raise IntegrityError due to nullable=False constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_task_required_fields_status(self, db_session):
        """Test that status field is required and cannot be null."""
        # Try to create task without status
        task = Task(
            title="Test Task"
        )
        
        db_session.add(task)
        
        # Should raise IntegrityError due to nullable=False constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_priority_enum_validation_valid_values(self, db_session):
        """Test Priority enum accepts valid values."""
        # Test all valid Priority enum values
        priorities = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        
        for priority in priorities:
            task = Task(
                title=f"Task with {priority.value} priority",
                priority=priority,
                status=Status.TODO
            )
            
            db_session.add(task)
            db_session.commit()
            
            # Retrieve and verify
            retrieved_task = db_session.get(Task, task.id)
            assert retrieved_task.priority == priority
            
            # Clean up for next iteration
            db_session.delete(retrieved_task)
            db_session.commit()

    def test_priority_enum_validation_invalid_values(self, db_session):
        """Test Priority enum rejects invalid values."""
        from kb_web_svc.models.task import PriorityEnumType
        
        priority_type = PriorityEnumType()
        
        # Test invalid string values
        with pytest.raises(ValueError, match="Invalid priority value: InvalidPriority. Must be one of:"):
            priority_type.process_bind_param("InvalidPriority", None)
        
        # Test invalid type
        with pytest.raises(ValueError, match="Priority must be a Priority enum or valid string"):
            priority_type.process_bind_param(123, None)

    def test_status_enum_validation_valid_values(self, db_session):
        """Test Status enum accepts valid values."""
        # Test all valid Status enum values
        statuses = [Status.TODO, Status.IN_PROGRESS, Status.DONE]
        
        for status in statuses:
            task = Task(
                title=f"Task with {status.value} status",
                status=status
            )
            
            db_session.add(task)
            db_session.commit()
            
            # Retrieve and verify
            retrieved_task = db_session.get(Task, task.id)
            assert retrieved_task.status == status
            
            # Clean up for next iteration
            db_session.delete(retrieved_task)
            db_session.commit()

    def test_status_enum_validation_invalid_values(self, db_session):
        """Test Status enum rejects invalid values."""
        from kb_web_svc.models.task import StatusEnumType
        
        status_type = StatusEnumType()
        
        # Test invalid string values
        with pytest.raises(ValueError, match="Invalid status value: InvalidStatus. Must be one of:"):
            status_type.process_bind_param("InvalidStatus", None)
        
        # Test invalid type
        with pytest.raises(ValueError, match="Status must be a Status enum or valid string"):
            status_type.process_bind_param(123, None)

    def test_automatic_timestamp_management(self, db_session):
        """Test automatic created_at and last_modified timestamp management."""
        # Record time before creation
        before_creation = datetime.now(timezone.utc)
        
        # Create task
        task = Task(
            title="Timestamp Test Task",
            status=Status.TODO
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Record time after creation
        after_creation = datetime.now(timezone.utc)
        
        # Verify created_at is set and within expected range
        assert task.created_at is not None
        assert isinstance(task.created_at, datetime)
        assert task.created_at.tzinfo is not None  # Timezone-aware
        assert before_creation <= task.created_at <= after_creation
        
        # Verify last_modified is initially equal to created_at
        assert task.last_modified is not None
        assert isinstance(task.last_modified, datetime)
        assert task.last_modified.tzinfo is not None  # Timezone-aware
        assert task.created_at == task.last_modified
        
        # Wait a small amount and update the task
        original_created_at = task.created_at
        original_last_modified = task.last_modified
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Update task
        before_update = datetime.now(timezone.utc)
        task.title = "Updated Timestamp Test Task"
        db_session.commit()
        after_update = datetime.now(timezone.utc)
        
        # Verify created_at didn't change
        assert task.created_at == original_created_at
        
        # Verify last_modified was updated
        assert task.last_modified != original_last_modified
        assert before_update <= task.last_modified <= after_update

    def test_uuid_primary_key_generation(self, db_session):
        """Test UUID primary key is automatically generated."""
        # Create task without specifying id
        task = Task(
            title="UUID Test Task",
            status=Status.TODO
        )
        
        # Verify id is None before saving
        assert task.id is None
        
        # Save to database
        db_session.add(task)
        db_session.commit()
        
        # Verify id is automatically generated as UUID
        assert task.id is not None
        assert isinstance(task.id, uuid.UUID)
        
        # Create another task to verify uniqueness
        task2 = Task(
            title="Second UUID Test Task",
            status=Status.IN_PROGRESS
        )
        
        db_session.add(task2)
        db_session.commit()
        
        # Verify different UUIDs
        assert task2.id != task.id

    def test_labels_json_field_storage_retrieval(self, db_session):
        """Test labels field JSON storage and retrieval as Python list."""
        # Test with list of strings
        labels_list = ["urgent", "frontend", "bug-fix"]
        
        task = Task(
            title="Labels Test Task",
            labels=labels_list,
            status=Status.TODO
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Retrieve and verify labels as Python list
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task.labels == labels_list
        assert isinstance(retrieved_task.labels, list)
        
        # Test with empty list
        task.labels = []
        db_session.commit()
        
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task.labels == []
        
        # Test with None
        task.labels = None
        db_session.commit()
        
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task.labels is None

    def test_to_dict_serialization_method(self, db_session):
        """Test to_dict() method for correct serialization."""
        # Create task with all fields populated
        task = Task(
            title="Serialization Test Task",
            assignee="Jane Smith",
            due_date=date(2024, 6, 15),
            description="Test description",
            priority=Priority.MEDIUM,
            labels=["test", "serialization"],
            estimated_time=4.5,
            status=Status.IN_PROGRESS
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Get dictionary representation
        task_dict = task.to_dict()
        
        # Verify all fields are present and correctly serialized
        assert isinstance(task_dict, dict)
        assert task_dict['id'] == str(task.id)  # UUID as string
        assert task_dict['title'] == "Serialization Test Task"
        assert task_dict['assignee'] == "Jane Smith"
        assert task_dict['due_date'] == "2024-06-15"  # Date as ISO string
        assert task_dict['description'] == "Test description"
        assert task_dict['priority'] == "Medium"  # Enum value as string
        assert task_dict['labels'] == ["test", "serialization"]  # List preserved
        assert task_dict['estimated_time'] == 4.5
        assert task_dict['status'] == "In Progress"  # Enum value as string
        assert isinstance(task_dict['created_at'], str)  # DateTime as ISO string
        assert isinstance(task_dict['last_modified'], str)  # DateTime as ISO string
        
        # Verify timestamp formats are valid ISO strings
        datetime.fromisoformat(task_dict['created_at'].replace('Z', '+00:00'))
        datetime.fromisoformat(task_dict['last_modified'].replace('Z', '+00:00'))

    def test_to_dict_serialization_with_none_values(self, db_session):
        """Test to_dict() method handles None values correctly."""
        # Create minimal task with only required fields
        task = Task(
            title="Minimal Task",
            status=Status.TODO
        )
        
        db_session.add(task)
        db_session.commit()
        
        task_dict = task.to_dict()
        
        # Verify None values are properly handled
        assert task_dict['assignee'] is None
        assert task_dict['due_date'] is None
        assert task_dict['description'] is None
        assert task_dict['priority'] is None
        assert task_dict['labels'] == []  # None labels become empty list
        assert task_dict['estimated_time'] is None
        
        # Required fields should still be present
        assert task_dict['title'] == "Minimal Task"
        assert task_dict['status'] == "To Do"
        assert task_dict['id'] == str(task.id)
        assert isinstance(task_dict['created_at'], str)
        assert isinstance(task_dict['last_modified'], str)

    def test_task_repr_method(self, db_session):
        """Test Task __repr__ method provides useful string representation."""
        task = Task(
            title="Repr Test Task",
            status=Status.DONE
        )
        
        db_session.add(task)
        db_session.commit()
        
        repr_str = repr(task)
        
        # Verify __repr__ contains key information
        assert "<Task(" in repr_str
        assert f"id={task.id}" in repr_str
        assert "title='Repr Test Task'" in repr_str
        assert "status='Done'" in repr_str
        assert repr_str.endswith(")>")

    def test_task_optional_fields_can_be_none(self, db_session):
        """Test that optional fields can be set to None without errors."""
        task = Task(
            title="Optional Fields Test",
            status=Status.TODO,
            assignee=None,
            due_date=None,
            description=None,
            priority=None,
            labels=None,
            estimated_time=None
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Retrieve and verify all None values are preserved
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task.assignee is None
        assert retrieved_task.due_date is None
        assert retrieved_task.description is None
        assert retrieved_task.priority is None
        assert retrieved_task.labels is None
        assert retrieved_task.estimated_time is None
        
        # Required fields should still work
        assert retrieved_task.title == "Optional Fields Test"
        assert retrieved_task.status == Status.TODO

    def test_task_database_indexes_exist(self, db_session):
        """Test that database indexes are properly created."""
        # This test verifies the table was created with indexes
        # by checking the table structure via SQLAlchemy metadata
        from sqlalchemy import inspect
        
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes('tasks')
        
        # Check that our defined indexes exist
        index_names = [idx['name'] for idx in indexes]
        
        assert 'idx_task_status' in index_names
        assert 'idx_task_priority' in index_names
        assert 'idx_task_due_date' in index_names
        
        # Verify index columns
        for idx in indexes:
            if idx['name'] == 'idx_task_status':
                assert idx['column_names'] == ['status']
            elif idx['name'] == 'idx_task_priority':
                assert idx['column_names'] == ['priority']
            elif idx['name'] == 'idx_task_due_date':
                assert idx['column_names'] == ['due_date']
