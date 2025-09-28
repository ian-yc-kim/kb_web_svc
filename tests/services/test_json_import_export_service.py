"""Unit tests for JSON import/export service.

This module tests the core logic for task import/export operations including
duplicate detection, conflict resolution, and atomic transaction handling.
"""

import json
import pytest
from datetime import datetime, timezone, date, timedelta
from uuid import uuid4
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.import_export_schemas import TaskImportData
from kb_web_svc.services.json_import_export_service import (
    export_all_tasks_to_json,
    restore_database_from_json_backup,
    import_tasks_logic,
    _create_task_orm_from_import_data,
    _update_task_orm_from_import_data,
    _ensure_utc_datetime
)


class TestExportAllTasksToJson:
    """Test cases for export_all_tasks_to_json function."""
    
    def test_export_empty_database(self, db_session: Session):
        """Test exporting from empty database returns empty JSON list."""
        result = export_all_tasks_to_json(db_session)
        
        parsed_result = json.loads(result)
        assert parsed_result == []
    
    def test_export_active_tasks_only(self, db_session: Session):
        """Test that only active tasks are exported, excluding soft-deleted ones."""
        # Create active task
        active_task = Task(
            title="Active Task",
            status=Status.TODO,
            assignee="John Doe",
            priority=Priority.HIGH
        )
        db_session.add(active_task)
        
        # Create soft-deleted task
        deleted_task = Task(
            title="Deleted Task",
            status=Status.DONE,
            deleted_at=datetime.now(timezone.utc)
        )
        db_session.add(deleted_task)
        db_session.commit()
        
        result = export_all_tasks_to_json(db_session)
        parsed_result = json.loads(result)
        
        assert len(parsed_result) == 1
        assert parsed_result[0]["title"] == "Active Task"
        assert parsed_result[0]["deleted_at"] is None
    
    def test_export_correct_json_format(self, db_session: Session):
        """Test that exported JSON has correct TaskImportData format."""
        task = Task(
            title="Test Task",
            status=Status.IN_PROGRESS,
            assignee="Jane Smith",
            due_date=date(2024, 12, 31),
            description="Test description",
            priority=Priority.MEDIUM,
            labels=["urgent", "frontend"],
            estimated_time=4.5
        )
        db_session.add(task)
        db_session.commit()
        
        result = export_all_tasks_to_json(db_session)
        parsed_result = json.loads(result)
        
        assert len(parsed_result) == 1
        task_data = parsed_result[0]
        
        # Verify all required fields are present
        assert "id" in task_data
        assert task_data["title"] == "Test Task"
        assert task_data["status"] == "In Progress"
        assert task_data["assignee"] == "Jane Smith"
        assert task_data["due_date"] == "2024-12-31"
        assert task_data["description"] == "Test description"
        assert task_data["priority"] == "Medium"
        assert task_data["labels"] == ["urgent", "frontend"]
        assert task_data["estimated_time"] == 4.5
        assert "created_at" in task_data
        assert "last_modified" in task_data
        assert task_data["deleted_at"] is None


class TestRestoreDatabaseFromJsonBackup:
    """Test cases for restore_database_from_json_backup function."""
    
    def test_restore_from_valid_json(self, db_session: Session):
        """Test successful restoration from valid JSON backup."""
        # Create existing task that should be deleted
        existing_task = Task(title="Existing Task", status=Status.TODO)
        db_session.add(existing_task)
        db_session.commit()
        
        # Prepare backup data
        backup_task_id = str(uuid4())
        backup_created_at = "2024-01-15T10:30:00+00:00"
        backup_last_modified = "2024-01-15T11:00:00+00:00"
        
        backup_data = [{
            "id": backup_task_id,
            "title": "Backup Task",
            "status": "Done",
            "assignee": "Backup User",
            "due_date": "2024-02-01",
            "description": "From backup",
            "priority": "Critical",
            "labels": ["backup"],
            "estimated_time": 2.0,
            "created_at": backup_created_at,
            "last_modified": backup_last_modified,
            "deleted_at": None
        }]
        
        json_backup = json.dumps(backup_data)
        
        # Execute restoration
        restore_database_from_json_backup(db_session, json_backup)
        
        # Verify existing task was deleted
        remaining_tasks = db_session.execute(select(Task)).scalars().all()
        assert len(remaining_tasks) == 1
        
        # Verify backup task was created with preserved ID and timestamps
        restored_task = remaining_tasks[0]
        assert str(restored_task.id) == backup_task_id
        assert restored_task.title == "Backup Task"
        assert restored_task.status == Status.DONE
        assert restored_task.assignee == "Backup User"
        assert restored_task.due_date == date(2024, 2, 1)
        assert restored_task.description == "From backup"
        assert restored_task.priority == Priority.CRITICAL
        assert restored_task.labels == ["backup"]
        assert restored_task.estimated_time == 2.0
        # Compare datetime values properly (SQLite may not preserve timezone info)
        expected_created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert restored_task.created_at.replace(tzinfo=timezone.utc) == expected_created_at
        assert restored_task.deleted_at is None
    
    def test_restore_with_deleted_at_timestamp(self, db_session: Session):
        """Test restoration correctly handles tasks with deleted_at timestamp."""
        backup_data = [{
            "id": str(uuid4()),
            "title": "Deleted Task",
            "status": "Done",
            "assignee": None,
            "due_date": None,
            "description": None,
            "priority": None,
            "labels": None,
            "estimated_time": None,
            "created_at": "2024-01-15T10:30:00+00:00",
            "last_modified": "2024-01-15T11:00:00+00:00",
            "deleted_at": "2024-01-15T12:00:00+00:00"
        }]
        
        json_backup = json.dumps(backup_data)
        restore_database_from_json_backup(db_session, json_backup)
        
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].deleted_at is not None
    
    def test_restore_rollback_on_invalid_json(self, db_session: Session):
        """Test transaction rollback when JSON is invalid."""
        # Create existing task
        existing_task = Task(title="Existing Task", status=Status.TODO)
        db_session.add(existing_task)
        db_session.commit()
        
        invalid_json = "{ invalid json }"
        
        with pytest.raises(ValueError, match="Invalid JSON format"):
            restore_database_from_json_backup(db_session, invalid_json)
        
        # Verify existing task is still present (rollback occurred)
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Existing Task"
    
    def test_restore_rollback_on_validation_error(self, db_session: Session):
        """Test transaction rollback when task data validation fails."""
        # Create existing task
        existing_task = Task(title="Existing Task", status=Status.TODO)
        db_session.add(existing_task)
        db_session.commit()
        
        # Invalid task data (missing required title)
        invalid_data = [{
            "title": "",  # Invalid empty title
            "status": "Todo",
        }]
        
        invalid_json = json.dumps(invalid_data)
        
        with pytest.raises(ValueError, match="Validation error in task at index 0"):
            restore_database_from_json_backup(db_session, invalid_json)
        
        # Verify existing task is still present (rollback occurred)
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Existing Task"


class TestImportTasksLogic:
    """Test cases for import_tasks_logic function."""
    
    def test_invalid_conflict_strategy_raises_error(self, db_session: Session):
        """Test that invalid conflict strategy raises ValueError."""
        tasks_data = []
        
        with pytest.raises(ValueError, match="Invalid conflict_strategy 'invalid'"):
            import_tasks_logic(db_session, tasks_data, "invalid")
    
    def test_no_conflicts_all_imported(self, db_session: Session):
        """Test importing tasks with no conflicts - all should be imported."""
        tasks_data = [
            TaskImportData(
                title="Task 1",
                status="To Do",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
            ),
            TaskImportData(
                title="Task 2",
                status="In Progress",
                created_at=datetime(2024, 1, 2, tzinfo=timezone.utc)
            )
        ]
        
        result = import_tasks_logic(db_session, tasks_data, "skip")
        
        assert result["imported"] == 2
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 0
        
        # Verify tasks were created
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 2
    
    def test_conflict_strategy_skip(self, db_session: Session):
        """Test skip conflict strategy - duplicates are identified and skipped."""
        # Create existing task
        existing_task = Task(
            title="Duplicate Task",
            status=Status.TODO,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        db_session.add(existing_task)
        db_session.commit()
        
        # Import data with duplicate (same title, same created_at date)
        tasks_data = [
            TaskImportData(
                title="Duplicate Task",
                status="Done",
                created_at=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc)  # Same date, different time
            ),
            TaskImportData(
                title="New Task",
                status="To Do",
                created_at=datetime(2024, 1, 2, tzinfo=timezone.utc)
            )
        ]
        
        result = import_tasks_logic(db_session, tasks_data, "skip")
        
        assert result["imported"] == 1  # Only new task
        assert result["updated"] == 0
        assert result["skipped"] == 1  # Duplicate was skipped
        assert result["failed"] == 0
        
        # Verify original task unchanged and new task added
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 2
        duplicate_task = next(t for t in tasks if t.title == "Duplicate Task")
        assert duplicate_task.status == Status.TODO  # Original status preserved
    
    def test_conflict_strategy_replace(self, db_session: Session):
        """Test replace conflict strategy - duplicates are hard-deleted and replaced."""
        # Create existing task
        original_id = uuid4()
        existing_task = Task(
            id=original_id,
            title="Duplicate Task",
            status=Status.TODO,
            assignee="Original Assignee",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        db_session.add(existing_task)
        db_session.commit()
        
        # Import data with duplicate and different ID
        new_id = uuid4()
        tasks_data = [
            TaskImportData(
                id=new_id,
                title="Duplicate Task",
                status="Done",
                assignee="New Assignee",
                created_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
            )
        ]
        
        result = import_tasks_logic(db_session, tasks_data, "replace")
        
        assert result["imported"] == 0
        assert result["updated"] == 1  # Replaced
        assert result["skipped"] == 0
        assert result["failed"] == 0
        
        # Verify task was replaced (different ID, updated fields)
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 1
        task = tasks[0]
        assert task.id == new_id  # New ID
        assert task.title == "Duplicate Task"
        assert task.status == Status.DONE  # Updated status
        assert task.assignee == "New Assignee"  # Updated assignee
    
    def test_conflict_strategy_merge_with_timestamp(self, db_session: Session):
        """Test merge_with_timestamp strategy - newer tasks update existing, older are skipped."""
        # Create existing task with specific last_modified
        existing_task = Task(
            title="Task to Merge",
            status=Status.TODO,
            assignee="Original Assignee",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 1, 10, tzinfo=timezone.utc)
        )
        db_session.add(existing_task)
        db_session.commit()
        existing_id = existing_task.id
        
        # Import data: one newer (should update), one older (should skip)
        tasks_data = [
            TaskImportData(
                title="Task to Merge",
                status="In Progress",
                assignee="Newer Assignee",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                last_modified=datetime(2024, 1, 15, tzinfo=timezone.utc)  # Newer
            ),
            TaskImportData(
                title="Task to Merge Old",
                status="Done",
                assignee="Older Assignee",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                last_modified=datetime(2024, 1, 5, tzinfo=timezone.utc)  # Older
            )
        ]
        
        # Note: Need to create another task with same title+date for second test
        another_existing = Task(
            title="Task to Merge Old",
            status=Status.TODO,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 1, 10, tzinfo=timezone.utc)
        )
        db_session.add(another_existing)
        db_session.commit()
        
        result = import_tasks_logic(db_session, tasks_data, "merge_with_timestamp")
        
        assert result["imported"] == 0
        assert result["updated"] == 1  # Only newer one updated
        assert result["skipped"] == 1  # Older one skipped
        assert result["failed"] == 0
        
        # Verify first task was updated
        db_session.refresh(existing_task)
        assert existing_task.id == existing_id  # ID preserved
        assert existing_task.status == Status.IN_PROGRESS  # Updated
        assert existing_task.assignee == "Newer Assignee"  # Updated
        
        # Verify second task was not updated
        db_session.refresh(another_existing)
        assert another_existing.status == Status.TODO  # Unchanged
    
    def test_mixed_scenario_import_update_skip(self, db_session: Session):
        """Test mixed scenario with new tasks, updates, and skips."""
        # Create existing task
        existing_task = Task(
            title="Existing Task",
            status=Status.TODO,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        db_session.add(existing_task)
        db_session.commit()
        
        tasks_data = [
            # New task - should be imported
            TaskImportData(
                title="New Task",
                status="To Do",
                created_at=datetime(2024, 1, 2, tzinfo=timezone.utc)
            ),
            # Duplicate task - should be skipped
            TaskImportData(
                title="Existing Task",
                status="Done",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
            ),
            # Another new task - should be imported
            TaskImportData(
                title="Another New Task",
                status="In Progress",
                created_at=datetime(2024, 1, 3, tzinfo=timezone.utc)
            )
        ]
        
        result = import_tasks_logic(db_session, tasks_data, "skip")
        
        assert result["imported"] == 2
        assert result["updated"] == 0
        assert result["skipped"] == 1
        assert result["failed"] == 0
        
        # Verify total task count
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 3
    
    def test_performance_200_tasks(self, db_session: Session):
        """Test performance: importing 200 tasks completes under 2 seconds."""
        import time
        
        # Create 200 tasks data
        tasks_data = []
        for i in range(200):
            tasks_data.append(
                TaskImportData(
                    title=f"Task {i}",
                    status="To Do",
                    assignee=f"User {i % 10}",
                    priority="Medium" if i % 2 == 0 else None,
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
                )
            )
        
        start_time = time.time()
        result = import_tasks_logic(db_session, tasks_data, "skip")
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 2.0, f"Import took {execution_time:.2f} seconds, expected under 2 seconds"
        
        assert result["imported"] == 200
        assert result["failed"] == 0
    
    def test_performance_200_tasks_with_conflicts(self, db_session: Session):
        """Test performance with conflicts: 200 tasks with 100 conflicts under 2 seconds."""
        import time
        
        # Create 100 existing tasks
        for i in range(100):
            task = Task(
                title=f"Task {i}",
                status=Status.TODO,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
            )
            db_session.add(task)
        db_session.commit()
        
        # Create 200 import tasks (100 conflicts + 100 new)
        tasks_data = []
        for i in range(200):
            tasks_data.append(
                TaskImportData(
                    title=f"Task {i}",
                    status="Done",
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
                )
            )
        
        start_time = time.time()
        result = import_tasks_logic(db_session, tasks_data, "skip")
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 2.0, f"Import took {execution_time:.2f} seconds, expected under 2 seconds"
        
        assert result["imported"] == 100  # Only new tasks
        assert result["skipped"] == 100  # Conflicts skipped
        assert result["failed"] == 0
    
    def test_transactional_integrity_invalid_strategy(self, db_session: Session):
        """Test that invalid conflict strategy leaves database unchanged."""
        # Create existing task
        existing_task = Task(title="Existing Task", status=Status.TODO)
        db_session.add(existing_task)
        db_session.commit()
        
        tasks_data = [TaskImportData(title="New Task", status="To Do")]
        
        with pytest.raises(ValueError):
            import_tasks_logic(db_session, tasks_data, "invalid_strategy")
        
        # Verify no changes occurred
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Existing Task"
    
    def test_transactional_integrity_task_processing_errors(self, db_session: Session):
        """Test rollback when task processing errors cause had_error flag."""
        tasks_data = [
            TaskImportData(title="Valid Task", status="To Do"),
            TaskImportData(title="Invalid Task", status="To Do")
        ]
        
        with patch('kb_web_svc.services.json_import_export_service._create_task_orm_from_import_data') as mock_create:
            # First call succeeds, second call fails
            mock_create.side_effect = [Task(title="Valid Task", status=Status.TODO), ValueError("Mock error")]
            
            with pytest.raises(Exception, match="Import failed with 1 task processing errors"):
                import_tasks_logic(db_session, tasks_data, "skip")
        
        # Verify no partial changes persisted (rollback occurred)
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 0
    
    def test_import_tasks_with_deleted_at(self, db_session: Session):
        """Test that tasks with deleted_at timestamp are correctly imported as soft-deleted."""
        tasks_data = [
            TaskImportData(
                title="Active Task",
                status="To Do",
                deleted_at=None
            ),
            TaskImportData(
                title="Soft Deleted Task",
                status="Done",
                deleted_at=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        result = import_tasks_logic(db_session, tasks_data, "skip")
        
        assert result["imported"] == 2
        assert result["failed"] == 0
        
        tasks = db_session.execute(select(Task)).scalars().all()
        assert len(tasks) == 2
        
        active_task = next(t for t in tasks if t.title == "Active Task")
        deleted_task = next(t for t in tasks if t.title == "Soft Deleted Task")
        
        assert active_task.deleted_at is None
        assert deleted_task.deleted_at is not None
        assert deleted_task.deleted_at.replace(tzinfo=timezone.utc) == datetime(2024, 1, 15, tzinfo=timezone.utc)


class TestHelperFunctions:
    """Test cases for helper functions."""
    
    def test_create_task_orm_from_import_data(self):
        """Test _create_task_orm_from_import_data preserves all fields including ID and timestamps."""
        import_id = uuid4()
        created_at = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        last_modified = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        deleted_at = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        
        task_data = TaskImportData(
            id=import_id,
            title="Test Task",
            status="In Progress",
            assignee="John Doe",
            due_date=date(2024, 12, 31),
            description="Test description",
            priority="High",
            labels=["test", "backend"],
            estimated_time=3.5,
            created_at=created_at,
            last_modified=last_modified,
            deleted_at=deleted_at
        )
        
        task_orm = _create_task_orm_from_import_data(task_data)
        
        # Verify all fields are correctly set
        assert task_orm.id == import_id
        assert task_orm.title == "Test Task"
        assert task_orm.status == Status.IN_PROGRESS
        assert task_orm.assignee == "John Doe"
        assert task_orm.due_date == date(2024, 12, 31)
        assert task_orm.description == "Test description"
        assert task_orm.priority == Priority.HIGH
        assert task_orm.labels == ["test", "backend"]
        assert task_orm.estimated_time == 3.5
        assert task_orm.created_at == created_at
        assert task_orm.last_modified == last_modified
        assert task_orm.deleted_at == deleted_at
    
    def test_create_task_orm_minimal_data(self):
        """Test _create_task_orm_from_import_data with minimal required data."""
        task_data = TaskImportData(
            title="Minimal Task",
            status="To Do"
        )
        
        task_orm = _create_task_orm_from_import_data(task_data)
        
        assert task_orm.title == "Minimal Task"
        assert task_orm.status == Status.TODO
        assert task_orm.assignee is None
        assert task_orm.due_date is None
        assert task_orm.description is None
        assert task_orm.priority is None
        assert task_orm.labels is None
        assert task_orm.estimated_time is None
        assert task_orm.deleted_at is None
        # ID, created_at, last_modified should be None if not provided (will be auto-generated)
    
    def test_update_task_orm_from_import_data(self):
        """Test _update_task_orm_from_import_data updates existing task correctly."""
        # Create existing task
        existing_task = Task(
            title="Old Title",
            status=Status.TODO,
            assignee="Old Assignee",
            priority=Priority.LOW,
            labels=["old"]
        )
        original_id = existing_task.id
        
        # Update data
        update_data = TaskImportData(
            title="New Title",
            status="Done",
            assignee="New Assignee",
            due_date=date(2024, 12, 31),
            description="New description",
            priority="High",
            labels=["new", "updated"],
            estimated_time=5.0,
            last_modified=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        
        _update_task_orm_from_import_data(existing_task, update_data)
        
        # Verify updates (ID should be preserved)
        assert existing_task.id == original_id  # ID preserved
        assert existing_task.title == "New Title"
        assert existing_task.status == Status.DONE
        assert existing_task.assignee == "New Assignee"
        assert existing_task.due_date == date(2024, 12, 31)
        assert existing_task.description == "New description"
        assert existing_task.priority == Priority.HIGH
        assert existing_task.labels == ["new", "updated"]
        assert existing_task.estimated_time == 5.0
        assert existing_task.last_modified == datetime(2024, 1, 15, tzinfo=timezone.utc)
    
    def test_ensure_utc_datetime_naive(self):
        """Test _ensure_utc_datetime handles naive datetime correctly."""
        naive_dt = datetime(2024, 1, 15, 10, 30, 45)
        result = _ensure_utc_datetime(naive_dt)
        
        assert result.tzinfo == timezone.utc
        assert result == datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
    
    def test_ensure_utc_datetime_aware(self):
        """Test _ensure_utc_datetime converts timezone-aware datetime to UTC."""
        # Create datetime in different timezone (EST = UTC-5)
        import pytz
        est = pytz.timezone('US/Eastern')
        est_dt = est.localize(datetime(2024, 1, 15, 10, 30, 45))
        
        result = _ensure_utc_datetime(est_dt)
        
        assert result.tzinfo == timezone.utc
        # 10:30 EST = 15:30 UTC
        expected_utc = datetime(2024, 1, 15, 15, 30, 45, tzinfo=timezone.utc)
        assert result == expected_utc
    
    def test_ensure_utc_datetime_already_utc(self):
        """Test _ensure_utc_datetime with already UTC datetime."""
        utc_dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _ensure_utc_datetime(utc_dt)
        
        assert result == utc_dt
        assert result.tzinfo == timezone.utc