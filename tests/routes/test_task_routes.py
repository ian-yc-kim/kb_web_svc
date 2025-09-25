"""Tests for task-related API routes.

This module contains comprehensive tests for all task management API endpoints
including creation, retrieval, updating, and deletion operations.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.task import TaskCreate
from kb_web_svc.services.task_service import create_task


class TestDeleteTaskEndpoint:
    """Test cases for the DELETE /api/tasks/{task_id} endpoint."""

    def test_successful_soft_deletion_of_existing_task(self, client: TestClient, db_session: Session):
        """Test successful soft deletion of an existing task."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task to be soft deleted",
            assignee="John Doe",
            priority="High",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Perform DELETE request with soft_delete=True (default)
        response = client.delete(f"/api/tasks/{task_id}")
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Task soft-deleted successfully"
        assert response_data["task_id"] == task_id
        
        # Verify task still exists in database but is soft-deleted
        db_task = db_session.get(Task, uuid.UUID(task_id))
        assert db_task is not None  # Task still exists
        assert db_task.deleted_at is not None  # But is soft-deleted
        assert db_task.title == "Task to be soft deleted"  # Other fields preserved
        assert db_task.assignee == "John Doe"
        assert db_task.priority == Priority.HIGH
        assert db_task.status == Status.IN_PROGRESS

    def test_successful_hard_deletion_of_existing_task(self, client: TestClient, db_session: Session):
        """Test successful hard deletion of an existing task."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Task to be hard deleted",
            assignee="Jane Smith",
            priority="Low",
            status="Done"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Verify task exists before deletion
        db_task_before = db_session.get(Task, uuid.UUID(task_id))
        assert db_task_before is not None
        
        # Perform DELETE request with soft_delete=False
        response = client.delete(f"/api/tasks/{task_id}?soft_delete=false")
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Task hard-deleted successfully"
        assert response_data["task_id"] == task_id
        
        # Verify task is completely removed from database
        db_task_after = db_session.get(Task, uuid.UUID(task_id))
        assert db_task_after is None  # Task no longer exists

    def test_delete_nonexistent_task_returns_404(self, client: TestClient):
        """Test attempting to delete a non-existent task, expecting a 404 response."""
        # Generate a random UUID that doesn't exist in database
        nonexistent_task_id = str(uuid.uuid4())
        
        # Attempt to delete non-existent task
        response = client.delete(f"/api/tasks/{nonexistent_task_id}")
        
        # Verify 404 response
        assert response.status_code == 404
        response_data = response.json()
        assert "detail" in response_data
        assert f"Task with ID {nonexistent_task_id} not found" in response_data["detail"]

    def test_soft_delete_task_exists_in_db_with_deleted_at_set(self, client: TestClient, db_session: Session):
        """Test soft deleting a task and verifying it still exists in the DB with deleted_at set."""
        # Create a task to soft delete
        task_data = TaskCreate(
            title="Task for soft delete verification",
            assignee="Test User",
            priority="Medium",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        task_uuid = uuid.UUID(task_id)
        
        # Verify task exists and is not soft-deleted initially
        db_task_before = db_session.get(Task, task_uuid)
        assert db_task_before is not None
        assert db_task_before.deleted_at is None
        
        # Record time before deletion
        time_before_deletion = datetime.now(timezone.utc)
        
        # Perform soft delete
        response = client.delete(f"/api/tasks/{task_id}?soft_delete=true")
        
        # Record time after deletion
        time_after_deletion = datetime.now(timezone.utc)
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify task still exists in database
        db_task_after = db_session.get(Task, task_uuid)
        assert db_task_after is not None
        
        # Verify deleted_at is set and is recent
        assert db_task_after.deleted_at is not None
        
        # Handle timezone-naive datetime from SQLite
        deleted_at = db_task_after.deleted_at
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=timezone.utc)
        
        # Verify deleted_at timestamp is within reasonable range
        assert time_before_deletion <= deleted_at <= time_after_deletion
        
        # Verify other fields are preserved
        assert db_task_after.title == "Task for soft delete verification"
        assert db_task_after.assignee == "Test User"
        assert db_task_after.priority == Priority.MEDIUM
        assert db_task_after.status == Status.TODO

    def test_hard_delete_task_truly_removed_from_db(self, client: TestClient, db_session: Session):
        """Test hard deleting a task and verifying it's truly removed from the DB."""
        # Create multiple tasks to ensure we're only deleting the targeted one
        task_data_1 = TaskCreate(title="Task 1", status="To Do")
        task_data_2 = TaskCreate(title="Task to delete", status="In Progress")
        task_data_3 = TaskCreate(title="Task 3", status="Done")
        
        created_task_1 = create_task(task_data_1, db_session)
        created_task_2 = create_task(task_data_2, db_session)
        created_task_3 = create_task(task_data_3, db_session)
        
        task_id_1 = uuid.UUID(created_task_1['id'])
        task_id_2 = uuid.UUID(created_task_2['id'])
        task_id_3 = uuid.UUID(created_task_3['id'])
        
        # Verify all tasks exist initially
        assert db_session.get(Task, task_id_1) is not None
        assert db_session.get(Task, task_id_2) is not None
        assert db_session.get(Task, task_id_3) is not None
        
        # Count total tasks before deletion
        total_tasks_before = db_session.query(Task).count()
        assert total_tasks_before == 3
        
        # Perform hard delete on task 2
        response = client.delete(f"/api/tasks/{created_task_2['id']}?soft_delete=false")
        
        # Verify successful response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Task hard-deleted successfully"
        
        # Verify only the targeted task is removed
        assert db_session.get(Task, task_id_1) is not None  # Still exists
        assert db_session.get(Task, task_id_2) is None       # Deleted
        assert db_session.get(Task, task_id_3) is not None  # Still exists
        
        # Verify total count decreased by exactly 1
        total_tasks_after = db_session.query(Task).count()
        assert total_tasks_after == 2
        
        # Verify the deleted task cannot be found via any query
        query_result = db_session.query(Task).filter(Task.id == task_id_2).first()
        assert query_result is None
        
        # Verify remaining tasks are the correct ones
        remaining_tasks = db_session.query(Task).all()
        remaining_ids = [task.id for task in remaining_tasks]
        assert task_id_1 in remaining_ids
        assert task_id_2 not in remaining_ids
        assert task_id_3 in remaining_ids

    def test_invalid_task_id_format_returns_422(self, client: TestClient):
        """Test invalid task_id format, expecting a 422 response (Pydantic validation)."""
        # Test various invalid UUID formats
        # Note: Empty string is excluded as FastAPI routing treats it as a different route (404)
        invalid_task_ids = [
            "not-a-uuid",
            "123",
            "invalid-uuid-format",
            "123e4567-e89b-12d3-a456-42661417400g",  # Invalid character 'g'
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
        ]
        
        for invalid_id in invalid_task_ids:
            # Attempt to delete with invalid UUID
            response = client.delete(f"/api/tasks/{invalid_id}")
            
            # Verify 422 Unprocessable Entity response
            assert response.status_code == 422, f"Expected 422 for invalid ID '{invalid_id}', got {response.status_code}"
            
            # Verify response contains validation error details
            response_data = response.json()
            assert "detail" in response_data
            # FastAPI validation errors have a specific structure
            assert isinstance(response_data["detail"], list)
            assert len(response_data["detail"]) > 0
            
            # Check that the error is related to UUID validation
            error_detail = response_data["detail"][0]
            assert "type" in error_detail
            assert "uuid" in error_detail["type"] or "parsing" in error_detail["type"]

    def test_soft_delete_default_behavior(self, client: TestClient, db_session: Session):
        """Test that soft_delete defaults to True when not specified."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Default soft delete test",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Perform DELETE without specifying soft_delete parameter
        response = client.delete(f"/api/tasks/{task_id}")
        
        # Verify response indicates soft delete
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Task soft-deleted successfully"
        
        # Verify task still exists but is soft-deleted
        db_task = db_session.get(Task, uuid.UUID(task_id))
        assert db_task is not None  # Task still exists
        assert db_task.deleted_at is not None  # But is soft-deleted

    def test_explicit_soft_delete_true_parameter(self, client: TestClient, db_session: Session):
        """Test explicit soft_delete=true parameter."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Explicit soft delete test",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Perform DELETE with explicit soft_delete=true
        response = client.delete(f"/api/tasks/{task_id}?soft_delete=true")
        
        # Verify response indicates soft delete
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Task soft-deleted successfully"
        
        # Verify task still exists but is soft-deleted
        db_task = db_session.get(Task, uuid.UUID(task_id))
        assert db_task is not None  # Task still exists
        assert db_task.deleted_at is not None  # But is soft-deleted

    def test_response_schema_validation(self, client: TestClient, db_session: Session):
        """Test that response follows TaskDeleteResponse schema."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Schema validation test",
            status="Done"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Perform soft delete
        response = client.delete(f"/api/tasks/{task_id}")
        
        # Verify response structure matches TaskDeleteResponse schema
        assert response.status_code == 200
        response_data = response.json()
        
        # Check required fields
        assert "message" in response_data
        assert "task_id" in response_data
        
        # Check field types and values
        assert isinstance(response_data["message"], str)
        assert isinstance(response_data["task_id"], str)
        
        # Check field values
        assert response_data["message"] == "Task soft-deleted successfully"
        assert response_data["task_id"] == task_id
        
        # Verify task_id is a valid UUID string
        uuid.UUID(response_data["task_id"])  # Should not raise exception

    def test_delete_endpoint_handles_database_errors(self, client: TestClient, db_session: Session, monkeypatch):
        """Test that the endpoint properly handles database errors with 500 response."""
        # Create a task to delete
        task_data = TaskCreate(
            title="Database error test",
            status="To Do"
        )
        created_task = create_task(task_data, db_session)
        task_id = created_task['id']
        
        # Mock the delete_task function where it's imported in the route module
        import kb_web_svc.routes.task_routes
        
        def mock_delete_task(*args, **kwargs):
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(kb_web_svc.routes.task_routes, "delete_task", mock_delete_task)
        
        # Attempt to delete the task
        response = client.delete(f"/api/tasks/{task_id}")
        
        # Verify 500 Internal Server Error response
        assert response.status_code == 500
        response_data = response.json()
        assert "detail" in response_data
        assert response_data["detail"] == "Internal server error"
        
        # Verify the original task still exists unchanged (rollback occurred)
        db_task = db_session.get(Task, uuid.UUID(task_id))
        assert db_task is not None
        assert db_task.deleted_at is None  # Should not be soft-deleted
        assert db_task.title == "Database error test"

    def test_multiple_delete_operations_independence(self, client: TestClient, db_session: Session):
        """Test that multiple delete operations are independent of each other."""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task_data = TaskCreate(
                title=f"Task {i+1}",
                status="To Do"
            )
            created_task = create_task(task_data, db_session)
            tasks.append(created_task)
        
        # Soft delete first task
        response1 = client.delete(f"/api/tasks/{tasks[0]['id']}")
        assert response1.status_code == 200
        
        # Hard delete second task
        response2 = client.delete(f"/api/tasks/{tasks[1]['id']}?soft_delete=false")
        assert response2.status_code == 200
        
        # Verify first task is soft-deleted
        db_task1 = db_session.get(Task, uuid.UUID(tasks[0]['id']))
        assert db_task1 is not None
        assert db_task1.deleted_at is not None
        
        # Verify second task is hard-deleted
        db_task2 = db_session.get(Task, uuid.UUID(tasks[1]['id']))
        assert db_task2 is None
        
        # Verify third task is unaffected
        db_task3 = db_session.get(Task, uuid.UUID(tasks[2]['id']))
        assert db_task3 is not None
        assert db_task3.deleted_at is None
        
        # Try to delete already deleted tasks
        response1_again = client.delete(f"/api/tasks/{tasks[0]['id']}")
        assert response1_again.status_code == 200  # Can soft-delete already soft-deleted task
        
        response2_again = client.delete(f"/api/tasks/{tasks[1]['id']}")
        assert response2_again.status_code == 404  # Hard-deleted task returns 404
