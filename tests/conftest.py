"""Pytest configuration and fixtures for testing.

This module provides shared fixtures for database testing using in-memory SQLite
for fast and isolated test execution.
"""

import importlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from kb_web_svc.models.base import Base
from kb_web_svc.api.app import app
from kb_web_svc.database import get_db
import kb_web_svc.database


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine for testing.
    
    Yields:
        SQLAlchemy Engine instance configured for in-memory SQLite.
    """
    # Create in-memory SQLite engine with StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for testing.
    
    Args:
        db_engine: SQLAlchemy engine fixture.
        
    Yields:
        SQLAlchemy Session instance for database operations.
    """
    # Create sessionmaker
    SessionLocal = sessionmaker(
        bind=db_engine,
        autoflush=False,
        expire_on_commit=False
    )
    
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI test client with database dependency override.
    
    Args:
        db_session: Database session fixture for dependency injection.
        
    Yields:
        TestClient instance configured with test database session.
    """
    # Override the get_db dependency to use our test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture
    
    # Apply dependency override
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def clean_db_state():
    """Clean database state before and after each test.
    
    This fixture ensures that the module-level database state
    is reset for each test to prevent interference.
    """
    # Reset state before test
    kb_web_svc.database._reset_db_state()
    
    yield
    
    # Reset state after test
    kb_web_svc.database._reset_db_state()
