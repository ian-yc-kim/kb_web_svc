"""Unit tests for task retrieval functions in the task service layer.

These tests verify the get_task_by_id and list_tasks functions functionality
including filtering, pagination, sorting, and error handling.
"""

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

import pytest
from sqlalchemy.orm import Session

from kb_web_svc.models.task import Task, Priority, Status
from kb_web_svc.schemas.task import TaskCreate, TaskFilterParams
from kb_web_svc.services.task_service import (
    create_task,
    get_task_by_id,
    list_tasks
)


class TestGetTaskById:
    """Test cases for the get_task_by_id service function."""

    def test_get_task_by_id_success(self, db_session: Session):
        """Test successful task retrieval by ID."""
        # Create a test task first
        task_data = TaskCreate(
            title="Test Task",
            assignee="John Doe",
            priority="High",
            status="In Progress"
        )
        created_task = create_task(task_data, db_session)
        task_id = uuid.UUID(created_task['id'])
        
        # Retrieve the task by ID
        result = get_task_by_id(db_session, task_id)
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result['id'] == created_task['id']
        assert result['title'] == "Test Task"
        assert result['assignee'] == "John Doe"
        assert result['priority'] == "High"
        assert result['status'] == "In Progress"

    def test_get_task_by_id_not_found(self, db_session: Session):
        """Test retrieval of non-existent task returns None."""
        # Generate a random UUID that doesn't exist
        non_existent_id = uuid.uuid4()
        
        # Try to retrieve non-existent task
        result = get_task_by_id(db_session, non_existent_id)
        
        # Verify None is returned
        assert result is None

    def test_get_task_by_id_database_error(self, db_session: Session, monkeypatch):
        """Test that database errors are properly logged and re-raised."""
        task_id = uuid.uuid4()
        
        # Mock db.get to raise an exception
        def mock_get(model_class, primary_key):
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'get', mock_get)
        
        # Try to retrieve task - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            get_task_by_id(db_session, task_id)


class TestListTasks:
    """Test cases for the list_tasks service function."""

    @pytest.fixture
    def sample_tasks(self, db_session: Session) -> List[Dict[str, Any]]:
        """Create sample tasks for testing."""
        tasks_data = [
            TaskCreate(
                title="High Priority Task",
                assignee="John Doe",
                priority="High",
                status="To Do",
                due_date=date.today() + timedelta(days=7),
                description="Important task"
            ),
            TaskCreate(
                title="Medium Priority Task",
                assignee="Jane Smith",
                priority="Medium",
                status="In Progress",
                due_date=date.today() + timedelta(days=14),
                description="Regular task"
            ),
            TaskCreate(
                title="Low Priority Task",
                assignee="John Doe",
                priority="Low",
                status="Done",
                due_date=date.today() + timedelta(days=21),
                description="Minor task"
            ),
            TaskCreate(
                title="Critical Priority Task",
                assignee="Alice Johnson",
                priority="Critical",
                status="To Do",
                due_date=date.today() + timedelta(days=1),
                description="Urgent critical task"
            ),
            TaskCreate(
                title="No Priority Task",
                assignee="Bob Wilson",
                status="In Progress",
                due_date=date.today() + timedelta(days=30)
            )
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            created_task = create_task(task_data, db_session)
            created_tasks.append(created_task)
        
        return created_tasks

    def test_list_tasks_no_filters(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test listing all tasks with no filters."""
        filters = TaskFilterParams()
        
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Verify results
        assert isinstance(result_tasks, list)
        assert isinstance(total_count, int)
        assert len(result_tasks) == 5
        assert total_count == 5
        
        # Verify all tasks are returned as dictionaries
        for task in result_tasks:
            assert isinstance(task, dict)
            assert 'id' in task
            assert 'title' in task

    def test_list_tasks_status_filter(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering tasks by status."""
        filters = TaskFilterParams(status="To Do")
        
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Verify only "To Do" tasks are returned
        assert len(result_tasks) == 2
        assert total_count == 2
        
        for task in result_tasks:
            assert task['status'] == "To Do"

    def test_list_tasks_priority_filter(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering tasks by priority."""
        filters = TaskFilterParams(priority="High")
        
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Verify only "High" priority tasks are returned
        assert len(result_tasks) == 1
        assert total_count == 1
        assert result_tasks[0]['priority'] == "High"
        assert result_tasks[0]['title'] == "High Priority Task"

    def test_list_tasks_assignee_filter(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering tasks by assignee (case-insensitive partial match)."""
        # Test exact match
        filters = TaskFilterParams(assignee="John Doe")
        result_tasks, total_count = list_tasks(db_session, filters)
        assert len(result_tasks) == 2
        assert total_count == 2
        
        # Test case-insensitive match
        filters = TaskFilterParams(assignee="john doe")
        result_tasks, total_count = list_tasks(db_session, filters)
        assert len(result_tasks) == 2
        assert total_count == 2
        
        # Test partial match
        filters = TaskFilterParams(assignee="John")
        result_tasks, total_count = list_tasks(db_session, filters)
        assert len(result_tasks) == 3  # John Doe + Alice Johnson
        assert total_count == 3

    def test_list_tasks_due_date_range_filter(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering tasks by due date range."""
        today = date.today()
        
        # Test due_date_start filter
        filters = TaskFilterParams(due_date_start=today + timedelta(days=10))
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should return tasks due on or after day 10
        assert len(result_tasks) == 3  # Medium (day 14), Low (day 21), No Priority (day 30)
        assert total_count == 3
        
        # Test due_date_end filter
        filters = TaskFilterParams(due_date_end=today + timedelta(days=10))
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should return tasks due on or before day 10
        assert len(result_tasks) == 2  # High (day 7), Critical (day 1)
        assert total_count == 2
        
        # Test both start and end filters
        filters = TaskFilterParams(
            due_date_start=today + timedelta(days=5),
            due_date_end=today + timedelta(days=20)
        )
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should return tasks due between day 5 and day 20
        assert len(result_tasks) == 2  # High (day 7), Medium (day 14)
        assert total_count == 2

    def test_list_tasks_search_term_filter(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering tasks by search term in title and description."""
        # Test search in title
        filters = TaskFilterParams(search_term="Priority")
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should find all tasks with "Priority" in title
        assert len(result_tasks) == 5  # All tasks have "Priority" in title
        assert total_count == 5
        
        # Test search in description
        filters = TaskFilterParams(search_term="Important")
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should find task with "Important" in description
        assert len(result_tasks) == 1
        assert total_count == 1
        assert result_tasks[0]['title'] == "High Priority Task"
        
        # Test case-insensitive search
        filters = TaskFilterParams(search_term="critical")
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should find Critical Priority Task
        assert len(result_tasks) == 1
        assert total_count == 1
        assert result_tasks[0]['title'] == "Critical Priority Task"

    def test_list_tasks_pagination(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test pagination with limit and offset."""
        # Test first page
        filters = TaskFilterParams(limit=2, offset=0)
        result_tasks, total_count = list_tasks(db_session, filters)
        
        assert len(result_tasks) == 2
        assert total_count == 5  # Total count should remain 5
        
        # Test second page
        filters = TaskFilterParams(limit=2, offset=2)
        result_tasks_page2, total_count_page2 = list_tasks(db_session, filters)
        
        assert len(result_tasks_page2) == 2
        assert total_count_page2 == 5  # Total count should remain 5
        
        # Verify different tasks are returned
        page1_ids = {task['id'] for task in result_tasks}
        page2_ids = {task['id'] for task in result_tasks_page2}
        assert len(page1_ids.intersection(page2_ids)) == 0  # No overlap
        
        # Test last page
        filters = TaskFilterParams(limit=2, offset=4)
        result_tasks_page3, total_count_page3 = list_tasks(db_session, filters)
        
        assert len(result_tasks_page3) == 1  # Only 1 task left
        assert total_count_page3 == 5

    def test_list_tasks_sorting_created_at(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test sorting by created_at field."""
        # Test descending order (default)
        filters = TaskFilterParams(sort_by="created_at", sort_order="desc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        # Verify tasks are sorted by created_at in descending order
        created_timestamps = [task['created_at'] for task in result_tasks]
        assert created_timestamps == sorted(created_timestamps, reverse=True)
        
        # Test ascending order
        filters = TaskFilterParams(sort_by="created_at", sort_order="asc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        # Verify tasks are sorted by created_at in ascending order
        created_timestamps = [task['created_at'] for task in result_tasks]
        assert created_timestamps == sorted(created_timestamps)

    def test_list_tasks_sorting_due_date(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test sorting by due_date field."""
        # Test ascending order
        filters = TaskFilterParams(sort_by="due_date", sort_order="asc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        # Verify tasks are sorted by due_date in ascending order
        due_dates = [task['due_date'] for task in result_tasks if task['due_date'] is not None]
        assert due_dates == sorted(due_dates)
        
        # Test descending order
        filters = TaskFilterParams(sort_by="due_date", sort_order="desc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        # Verify tasks are sorted by due_date in descending order
        due_dates = [task['due_date'] for task in result_tasks if task['due_date'] is not None]
        assert due_dates == sorted(due_dates, reverse=True)

    def test_list_tasks_sorting_priority(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test sorting by priority field using logical order."""
        # Test descending order (Critical > High > Medium > Low > None)
        filters = TaskFilterParams(sort_by="priority", sort_order="desc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        # Verify priority order
        priorities = [task['priority'] for task in result_tasks]
        expected_order = ["Critical", "High", "Medium", "Low", None]
        assert priorities == expected_order
        
        # Test ascending order (None < Low < Medium < High < Critical)
        filters = TaskFilterParams(sort_by="priority", sort_order="asc")
        result_tasks, _ = list_tasks(db_session, filters)
        
        priorities = [task['priority'] for task in result_tasks]
        expected_order = [None, "Low", "Medium", "High", "Critical"]
        assert priorities == expected_order

    def test_list_tasks_invalid_sort_by_error(self, db_session: Session):
        """Test that invalid sort_by parameter raises ValueError."""
        filters = TaskFilterParams(sort_by="invalid_field")
        
        with pytest.raises(ValueError) as exc_info:
            list_tasks(db_session, filters)
        
        error_msg = str(exc_info.value)
        assert "Invalid sort_by 'invalid_field'" in error_msg
        assert "Must be one of:" in error_msg
        assert "created_at" in error_msg
        assert "due_date" in error_msg
        assert "priority" in error_msg

    def test_list_tasks_invalid_sort_order_error(self, db_session: Session):
        """Test that invalid sort_order parameter raises ValueError."""
        filters = TaskFilterParams(sort_by="created_at", sort_order="invalid_order")
        
        with pytest.raises(ValueError) as exc_info:
            list_tasks(db_session, filters)
        
        error_msg = str(exc_info.value)
        assert "Invalid sort_order 'invalid_order'" in error_msg
        assert "Must be one of:" in error_msg
        assert "asc" in error_msg
        assert "desc" in error_msg

    def test_list_tasks_combined_filters(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test combining multiple filters."""
        # Filter by assignee containing "John" and status "To Do"
        filters = TaskFilterParams(
            assignee="John",
            status="To Do"
        )
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should find only tasks assigned to John Doe with status "To Do"
        # But Alice Johnson also matches "John" search and has "To Do" status
        assert len(result_tasks) == 2  # John Doe and Alice Johnson "To Do" tasks
        assert total_count == 2
        
        for task in result_tasks:
            assert task['status'] == "To Do"
            assert "John" in task['assignee']

    def test_list_tasks_no_results(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test filtering with criteria that return no results."""
        filters = TaskFilterParams(
            status="To Do",
            priority="Low"  # No "To Do" tasks with "Low" priority
        )
        
        result_tasks, total_count = list_tasks(db_session, filters)
        
        assert len(result_tasks) == 0
        assert total_count == 0

    def test_list_tasks_database_error(self, db_session: Session, monkeypatch):
        """Test that database errors are properly logged and re-raised."""
        filters = TaskFilterParams()
        
        # Mock db.execute to raise an exception
        def mock_execute(stmt):
            raise Exception("Simulated database error")
        
        monkeypatch.setattr(db_session, 'execute', mock_execute)
        
        # Try to list tasks - should raise the mocked exception
        with pytest.raises(Exception, match="Simulated database error"):
            list_tasks(db_session, filters)

    def test_list_tasks_empty_database(self, db_session: Session):
        """Test listing tasks when database is empty."""
        filters = TaskFilterParams()
        
        result_tasks, total_count = list_tasks(db_session, filters)
        
        assert len(result_tasks) == 0
        assert total_count == 0

    def test_list_tasks_filter_params_normalization(self, db_session: Session, sample_tasks: List[Dict[str, Any]]):
        """Test that TaskFilterParams properly normalizes input values."""
        # Test that empty strings become None
        filters = TaskFilterParams(
            status="  ",  # Whitespace only
            assignee="",   # Empty string
            search_term="  search  "  # Whitespace around text
        )
        
        # These should be normalized by the schema
        assert filters.status is None
        assert filters.assignee is None
        assert filters.search_term == "search"
        
        # Test search with normalized term
        result_tasks, total_count = list_tasks(db_session, filters)
        
        # Should return 0 results since no task has "search" in title/description
        assert len(result_tasks) == 0
        assert total_count == 0
