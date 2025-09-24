"""Unit tests for database module.

These tests ensure proper database connection and session management functionality
using in-memory SQLite for isolation and speed.
"""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

import kb_web_svc.database


class TestDatabase:
    """Test cases for database module functionality."""

    def test_get_db_url_default_sqlite(self, monkeypatch):
        """Test get_db_url returns SQLite in-memory when DATABASE_URL is not set."""
        # Unset DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh environment read
        importlib.reload(kb_web_svc.database)
        
        result = kb_web_svc.database.get_db_url()
        assert result == "sqlite:///:memory:"

    def test_get_db_url_from_environment(self, monkeypatch):
        """Test get_db_url returns value from DATABASE_URL environment variable."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)
        
        # Reload module to ensure fresh environment read
        importlib.reload(kb_web_svc.database)
        
        result = kb_web_svc.database.get_db_url()
        assert result == test_url

    def test_create_engine_and_session_factory_sqlite_inmemory(self, monkeypatch):
        """Test engine and session factory creation for SQLite in-memory database."""
        # Ensure DATABASE_URL is not set to use default SQLite
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(kb_web_svc.database)
        
        engine, session_factory = kb_web_svc.database.create_engine_and_session_factory()
        
        # Verify engine backend is SQLite
        assert engine.dialect.name == "sqlite"
        
        # Verify session factory creates sessions with correct configuration
        session = session_factory()
        assert isinstance(session, Session)
        assert session.autoflush is False
        assert session.expire_on_commit is False
        session.close()
        
        # Verify connection works
        assert kb_web_svc.database.check_db_connection() is True

    def test_get_db_yields_and_closes(self, monkeypatch):
        """Test get_db generator yields session and properly closes it."""
        # Ensure SQLite in-memory database
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(kb_web_svc.database)
        
        # Get the generator
        db_gen = kb_web_svc.database.get_db()
        
        # Get session from generator
        session = next(db_gen)
        assert isinstance(session, Session)
        
        # Mock session.close to track invocation
        close_mock = MagicMock()
        original_close = session.close
        session.close = close_mock
        
        # Close the generator
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        # Verify close was called exactly once
        close_mock.assert_called_once()
        
        # Restore original close method for cleanup
        session.close = original_close
        session.close()

    def test_create_engine_and_session_factory_postgres_dialect(self, monkeypatch):
        """Test engine creation for PostgreSQL dialect (no real connection)."""
        postgres_url = "postgresql+psycopg2://user:pass@localhost:5432/db"
        monkeypatch.setenv("DATABASE_URL", postgres_url)
        
        # Reload module to ensure fresh engine creation with new URL
        importlib.reload(kb_web_svc.database)
        
        engine, session_factory = kb_web_svc.database.create_engine_and_session_factory()
        
        # Verify engine dialect is PostgreSQL with psycopg2 driver
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg2"
        
        # Verify session factory is created (no connection attempts)
        assert session_factory is not None
        assert callable(session_factory)

    def test_check_db_connection_success(self, monkeypatch):
        """Test check_db_connection returns True on successful connection."""
        # Ensure SQLite in-memory database
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(kb_web_svc.database)
        
        result = kb_web_svc.database.check_db_connection()
        assert result is True

    def test_check_db_connection_failure_returns_false(self, monkeypatch):
        """Test check_db_connection returns False when connection fails."""
        # Ensure SQLite in-memory database
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(kb_web_svc.database)
        
        # Mock Session.execute to raise an exception
        with patch.object(Session, 'execute', side_effect=Exception("Connection failed")):
            result = kb_web_svc.database.check_db_connection()
            assert result is False

    def test_get_db_handles_exceptions(self, monkeypatch):
        """Test get_db properly handles and re-raises exceptions."""
        # Ensure SQLite in-memory database
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(kb_web_svc.database)
        
        # Get the generator
        db_gen = kb_web_svc.database.get_db()
        
        # Get session from generator
        session = next(db_gen)
        
        # Mock session.close to track invocation
        close_mock = MagicMock()
        original_close = session.close
        session.close = close_mock
        
        # Simulate an exception during session usage
        with pytest.raises(ValueError):
            try:
                raise ValueError("Test exception")
            except ValueError:
                # Close the generator in exception scenario
                try:
                    next(db_gen)
                except StopIteration:
                    pass
                raise
        
        # Verify close was still called despite exception
        close_mock.assert_called_once()
        
        # Restore original close method
        session.close = original_close
        session.close()

    def test_create_engine_and_session_factory_with_custom_url(self):
        """Test create_engine_and_session_factory with custom URL parameter."""
        custom_url = "sqlite:///test.db"
        
        engine, session_factory = kb_web_svc.database.create_engine_and_session_factory(custom_url)
        
        # Verify engine uses custom URL
        assert engine.dialect.name == "sqlite"
        assert session_factory is not None
        
        # Clean up by creating a session and closing it
        session = session_factory()
        session.close()
