"""Unit tests for import/export schemas.

Tests the TaskImportData and TaskImportResult schemas for proper validation,
normalization, and error handling during JSON task import/export operations.
"""

import pytest
from datetime import datetime, date, timezone
from uuid import uuid4, UUID
from pydantic import ValidationError

from kb_web_svc.schemas.import_export_schemas import TaskImportData, TaskImportResult


class TestTaskImportData:
    """Test cases for TaskImportData schema validation."""
    
    def test_valid_full_task_data(self):
        """Test successful validation with all fields provided."""
        task_id = uuid4()
        now_utc = datetime.now(timezone.utc)
        
        data = {
            "id": str(task_id),
            "title": "Test Task",
            "assignee": "John Doe",
            "due_date": "2024-12-31",
            "description": "A test task description",
            "priority": "High",
            "labels": ["test", "development"],
            "estimated_time": 4.5,
            "status": "To Do",
            "created_at": now_utc.isoformat(),
            "last_modified": now_utc.isoformat(),
            "deleted_at": None
        }
        
        task = TaskImportData(**data)
        
        assert task.id == task_id
        assert task.title == "Test Task"
        assert task.assignee == "John Doe"
        assert task.due_date == date(2024, 12, 31)
        assert task.description == "A test task description"
        assert task.priority == "High"
        assert task.labels == ["test", "development"]
        assert task.estimated_time == 4.5
        assert task.status == "To Do"
        assert task.created_at == now_utc
        assert task.last_modified == now_utc
        assert task.deleted_at is None
    
    def test_minimal_required_fields_only(self):
        """Test successful validation with only required fields."""
        data = {
            "title": "Minimal Task",
            "status": "In Progress"
        }
        
        task = TaskImportData(**data)
        
        assert task.id is None
        assert task.title == "Minimal Task"
        assert task.assignee is None
        assert task.due_date is None
        assert task.description is None
        assert task.priority is None
        assert task.labels is None
        assert task.estimated_time is None
        assert task.status == "In Progress"
        assert task.created_at is None
        assert task.last_modified is None
        assert task.deleted_at is None
    
    def test_missing_title_raises_error(self):
        """Test validation error when title is missing."""
        data = {"status": "To Do"}
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "title" in str(exc_info.value)
    
    def test_missing_status_raises_error(self):
        """Test validation error when status is missing."""
        data = {"title": "Test Task"}
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "status" in str(exc_info.value)
    
    def test_empty_title_after_strip_raises_error(self):
        """Test validation error when title is empty after stripping."""
        data = {
            "title": "   ",  # Only whitespace
            "status": "To Do"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_empty_status_after_strip_raises_error(self):
        """Test validation error when status is empty after stripping."""
        data = {
            "title": "Test Task",
            "status": "   "  # Only whitespace
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_invalid_priority_enum_raises_error(self):
        """Test validation error for invalid priority enum value."""
        data = {
            "title": "Test Task",
            "priority": "Invalid Priority",
            "status": "To Do"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "Invalid priority" in str(exc_info.value)
        assert "Must be one of" in str(exc_info.value)
    
    def test_invalid_status_enum_raises_error(self):
        """Test validation error for invalid status enum value."""
        data = {
            "title": "Test Task",
            "status": "Invalid Status"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "Invalid status" in str(exc_info.value)
        assert "Must be one of" in str(exc_info.value)
    
    def test_estimated_time_below_minimum_raises_error(self):
        """Test validation error for estimated_time below 0.5."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "estimated_time": 0.25
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "greater than or equal to 0.5" in str(exc_info.value)
    
    def test_estimated_time_above_maximum_raises_error(self):
        """Test validation error for estimated_time above 8.0."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "estimated_time": 10.0
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "less than or equal to 8" in str(exc_info.value)
    
    def test_estimated_time_boundary_values(self):
        """Test that boundary values for estimated_time are accepted."""
        # Test minimum value
        data_min = {
            "title": "Test Task",
            "status": "To Do",
            "estimated_time": 0.5
        }
        task_min = TaskImportData(**data_min)
        assert task_min.estimated_time == 0.5
        
        # Test maximum value
        data_max = {
            "title": "Test Task",
            "status": "To Do",
            "estimated_time": 8.0
        }
        task_max = TaskImportData(**data_max)
        assert task_max.estimated_time == 8.0
    
    def test_string_field_whitespace_stripping(self):
        """Test whitespace stripping for string fields."""
        data = {
            "title": "  Test Task  ",
            "assignee": "  John Doe  ",
            "description": "  A description  ",
            "priority": "  High  ",
            "status": "  To Do  "
        }
        
        task = TaskImportData(**data)
        
        assert task.title == "Test Task"
        assert task.assignee == "John Doe"
        assert task.description == "A description"
        assert task.priority == "High"
        assert task.status == "To Do"
    
    def test_optional_empty_strings_become_none(self):
        """Test that empty optional string fields become None after stripping."""
        data = {
            "title": "Test Task",
            "assignee": "   ",  # Only whitespace
            "description": "",  # Empty string
            "priority": "   ",  # Only whitespace
            "status": "To Do"
        }
        
        task = TaskImportData(**data)
        
        assert task.title == "Test Task"
        assert task.assignee is None
        assert task.description is None
        assert task.priority is None
        assert task.status == "To Do"
    
    def test_labels_cleaning_and_normalization(self):
        """Test labels list cleaning: strip whitespace and remove empty entries."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "labels": ["  test  ", "", "   ", "development", "  bug  "]
        }
        
        task = TaskImportData(**data)
        
        # Should strip whitespace and remove empty strings
        assert task.labels == ["test", "development", "bug"]
    
    def test_labels_becomes_none_when_empty_after_cleanup(self):
        """Test that labels becomes None when all entries are empty after cleanup."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "labels": ["", "   ", "\t\n"]  # All empty/whitespace
        }
        
        task = TaskImportData(**data)
        
        assert task.labels is None
    
    def test_labels_invalid_type_raises_error(self):
        """Test validation error when labels is not a list."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "labels": "not a list"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "must be a list" in str(exc_info.value)
    
    def test_labels_non_string_items_raise_error(self):
        """Test validation error when labels contain non-string items."""
        data = {
            "title": "Test Task",
            "status": "To Do",
            "labels": ["valid", 123, "also valid"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TaskImportData(**data)
        
        assert "must be strings" in str(exc_info.value)
    
    def test_timezone_aware_datetime_preserved(self):
        """Test that timezone-aware datetimes are preserved."""
        utc_time = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        data = {
            "title": "Test Task",
            "status": "To Do",
            "created_at": utc_time,
            "last_modified": utc_time
        }
        
        task = TaskImportData(**data)
        
        assert task.created_at == utc_time
        assert task.last_modified == utc_time
        assert task.created_at.tzinfo is not None
        assert task.last_modified.tzinfo is not None
    
    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetimes are converted to UTC."""
        naive_time = datetime(2024, 1, 15, 10, 30, 45)  # No timezone
        
        data = {
            "title": "Test Task",
            "status": "To Do",
            "created_at": naive_time
        }
        
        task = TaskImportData(**data)
        
        expected_utc = naive_time.replace(tzinfo=timezone.utc)
        assert task.created_at == expected_utc
        assert task.created_at.tzinfo == timezone.utc
    
    def test_valid_priority_enum_values(self):
        """Test all valid priority enum values are accepted."""
        valid_priorities = ["Critical", "High", "Medium", "Low"]
        
        for priority in valid_priorities:
            data = {
                "title": "Test Task",
                "status": "To Do",
                "priority": priority
            }
            
            task = TaskImportData(**data)
            assert task.priority == priority
    
    def test_valid_status_enum_values(self):
        """Test all valid status enum values are accepted."""
        valid_statuses = ["To Do", "In Progress", "Done"]
        
        for status in valid_statuses:
            data = {
                "title": "Test Task",
                "status": status
            }
            
            task = TaskImportData(**data)
            assert task.status == status
    
    def test_uuid_parsing(self):
        """Test UUID parsing from string."""
        task_id = uuid4()
        
        data = {
            "title": "Test Task",
            "status": "To Do",
            "id": str(task_id)
        }
        
        task = TaskImportData(**data)
        assert task.id == task_id
        assert isinstance(task.id, UUID)


class TestTaskImportResult:
    """Test cases for TaskImportResult schema."""
    
    def test_valid_task_import_result(self):
        """Test successful creation of TaskImportResult."""
        task_id = uuid4()
        
        result = TaskImportResult(
            task_id=task_id,
            status="imported",
            message="Task successfully imported"
        )
        
        assert result.task_id == task_id
        assert result.status == "imported"
        assert result.message == "Task successfully imported"
    
    def test_task_import_result_with_uuid_string(self):
        """Test TaskImportResult with UUID provided as string."""
        task_id = uuid4()
        
        result = TaskImportResult(
            task_id=str(task_id),  # UUID as string
            status="updated",
            message="Task successfully updated"
        )
        
        assert result.task_id == task_id
        assert isinstance(result.task_id, UUID)
        assert result.status == "updated"
        assert result.message == "Task successfully updated"
    
    def test_task_import_result_different_statuses(self):
        """Test TaskImportResult with different status values."""
        task_id = uuid4()
        statuses = ["imported", "updated", "skipped", "failed"]
        
        for status in statuses:
            result = TaskImportResult(
                task_id=task_id,
                status=status,
                message=f"Task {status}"
            )
            
            assert result.status == status
            assert result.message == f"Task {status}"
