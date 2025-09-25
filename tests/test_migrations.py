"""Test suite for Alembic migrations to verify upgrade and downgrade functionality.

This module tests that Alembic migrations can be applied and rolled back successfully,
and that the database schema is correct after application.
"""

import os
import pytest
import uuid
from datetime import datetime, timezone

import alembic.command
import alembic.config
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, inspect, select, text
from sqlalchemy.engine import Inspector


@pytest.fixture
def db_url(tmp_path):
    """Create a temporary SQLite database file URL for each test.
    
    Args:
        tmp_path: pytest tmp_path fixture providing temporary directory.
        
    Returns:
        SQLite file URL string for the temporary database.
    """
    db_file = tmp_path / "alembic_test.sqlite"
    return f"sqlite:///{db_file}"


@pytest.fixture
def alembic_cfg(db_url, monkeypatch):
    """Create Alembic configuration with temporary database URL.
    
    Args:
        db_url: SQLite database URL from db_url fixture.
        monkeypatch: pytest monkeypatch fixture for environment variables.
        
    Returns:
        Alembic Config object configured for testing.
    """
    # Set DATABASE_URL environment variable so env.py picks it up
    monkeypatch.setenv("DATABASE_URL", db_url)
    
    # Return Alembic configuration
    return alembic.config.Config("alembic.ini")


def test_upgrade_creates_tasks_table_and_schema(alembic_cfg, db_url):
    """Test that alembic upgrade head creates the tasks table with correct schema.
    
    This test verifies:
    1. Migration runs successfully
    2. Tasks table is created
    3. All expected columns exist with correct properties
    4. Indexes are created
    5. Basic CRUD operations work
    
    Args:
        alembic_cfg: Alembic configuration fixture.
        db_url: Database URL fixture.
    """
    # Run alembic upgrade to head
    alembic.command.upgrade(alembic_cfg, "head")
    
    # Create engine and inspector to verify schema
    engine = create_engine(db_url)
    
    try:
        inspector: Inspector = inspect(engine)
        
        # Verify tasks table exists
        table_names = inspector.get_table_names()
        assert 'tasks' in table_names, f"Tasks table not found. Available tables: {table_names}"
        
        # Get table columns
        columns = inspector.get_columns('tasks')
        column_names = [col['name'] for col in columns]
        column_dict = {col['name']: col for col in columns}
        
        # Verify all expected columns exist
        expected_columns = {
            'id', 'title', 'assignee', 'due_date', 'description', 
            'priority', 'status', 'labels', 'estimated_time', 
            'created_at', 'last_modified'
        }
        actual_columns = set(column_names)
        assert expected_columns.issubset(actual_columns), (
            f"Missing columns: {expected_columns - actual_columns}. "
            f"Actual columns: {actual_columns}"
        )
        
        # Verify nullable constraints for non-null columns
        non_null_columns = {'id', 'title', 'status', 'created_at', 'last_modified'}
        for col_name in non_null_columns:
            assert not column_dict[col_name]['nullable'], (
                f"Column '{col_name}' should be non-nullable"
            )
        
        # Verify primary key
        primary_key = inspector.get_pk_constraint('tasks')
        assert 'id' in primary_key['constrained_columns'], (
            f"Primary key should include 'id'. Actual: {primary_key}"
        )
        
        # Verify indexes exist
        indexes = inspector.get_indexes('tasks')
        index_names = [idx['name'] for idx in indexes]
        expected_indexes = {'idx_task_status', 'idx_task_priority', 'idx_task_due_date'}
        actual_indexes = set(index_names)
        assert expected_indexes.issubset(actual_indexes), (
            f"Missing indexes: {expected_indexes - actual_indexes}. "
            f"Actual indexes: {actual_indexes}"
        )
        
        # Verify index columns
        index_dict = {idx['name']: idx for idx in indexes}
        assert 'status' in index_dict['idx_task_status']['column_names'], (
            "idx_task_status should index 'status' column"
        )
        assert 'priority' in index_dict['idx_task_priority']['column_names'], (
            "idx_task_priority should index 'priority' column"
        )
        assert 'due_date' in index_dict['idx_task_due_date']['column_names'], (
            "idx_task_due_date should index 'due_date' column"
        )
        
        # CRUD smoke test - use raw SQL to avoid SQLAlchemy type conversion issues
        now_utc = datetime.now(timezone.utc)
        test_id = str(uuid.uuid4())
        
        with engine.connect() as conn:
            # Insert test data using raw SQL to avoid type conversion issues
            insert_sql = text("""
                INSERT INTO tasks (id, title, status, created_at, last_modified) 
                VALUES (:id, :title, :status, :created_at, :last_modified)
            """)
            
            conn.execute(insert_sql, {
                'id': test_id,
                'title': 'Test Task',
                'status': 'To Do',
                'created_at': now_utc,
                'last_modified': now_utc
            })
            conn.commit()
            
            # Select it back to verify CRUD works
            select_sql = text("""
                SELECT id, title, status 
                FROM tasks 
                WHERE id = :id
            """)
            
            result = conn.execute(select_sql, {'id': test_id}).fetchone()
            
            assert result is not None, "Failed to retrieve inserted task"
            assert result[0] == test_id, f"ID mismatch: expected {test_id}, got {result[0]}"
            assert result[1] == 'Test Task', f"Title mismatch: expected 'Test Task', got {result[1]}"
            assert result[2] == 'To Do', f"Status mismatch: expected 'To Do', got {result[2]}"
            
    finally:
        # Clean up engine
        engine.dispose()


def test_downgrade_removes_tasks_table(alembic_cfg, db_url):
    """Test that alembic downgrade base removes the tasks table.
    
    This test verifies:
    1. Upgrade creates the table
    2. Downgrade removes the table
    
    Args:
        alembic_cfg: Alembic configuration fixture.
        db_url: Database URL fixture.
    """
    # First run upgrade to create the table
    alembic.command.upgrade(alembic_cfg, "head")
    
    # Verify table exists
    engine = create_engine(db_url)
    try:
        inspector: Inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert 'tasks' in table_names, "Tasks table should exist after upgrade"
    finally:
        engine.dispose()
    
    # Now run downgrade to base
    alembic.command.downgrade(alembic_cfg, "base")
    
    # Verify table no longer exists
    engine = create_engine(db_url)
    try:
        inspector: Inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert 'tasks' not in table_names, (
            f"Tasks table should not exist after downgrade. Available tables: {table_names}"
        )
    finally:
        engine.dispose()
