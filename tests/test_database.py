import pytest
import os
import importlib
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from kb_web_svc import database


class TestDatabase:
    def setup_method(self):
        """Reset database state before each test."""
        database._reset_db_state()
    
    def test_get_db_url_default_sqlite(self, monkeypatch):
        """Test get_db_url defaults to sqlite:///:memory: when DATABASE_URL is not set."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        result = database.get_db_url()
        assert result == "sqlite:///:memory:"
    
    def test_get_db_url_from_environment(self, monkeypatch):
        """Test get_db_url returns DATABASE_URL from environment when set."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)
        
        result = database.get_db_url()
        assert result == test_url
    
    def test_create_engine_and_session_factory_sqlite_inmemory(self, monkeypatch):
        """Test engine and session factory creation for SQLite in-memory database."""
        # Ensure DATABASE_URL is not set to use default SQLite
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        # Reload module to ensure fresh engine creation
        importlib.reload(database)
        
        engine, session_factory = database.create_engine_and_session_factory()
        
        # Verify engine backend is SQLite
        assert engine.dialect.name == "sqlite"
        
        # Verify session factory creates sessions with correct configuration
        session = session_factory()
        assert isinstance(session, Session)
        assert session.autoflush is False
        
        session.close()
    
    def test_get_db_yields_and_closes(self):
        """Test that get_db yields a session and properly closes it."""
        # Use get_db generator properly
        db_gen = database.get_db()
        session = next(db_gen)
        
        # Test session functionality
        result = session.execute(text("SELECT 1")).scalar_one()
        assert result == 1
        
        # Close generator to trigger cleanup
        db_gen.close()
        
        # Verify session was properly managed - check it's a valid Session object
        assert isinstance(session, Session)
    
    def test_create_engine_and_session_factory_postgres_dialect(self):
        """Test engine creation for PostgreSQL dialect without actual connection."""
        pytest.importorskip("psycopg2")
        
        postgres_url = "postgresql+psycopg2://user:pass@localhost:5432/db"
        engine, session_factory = database.create_engine_and_session_factory(db_url=postgres_url)
        
        # Verify PostgreSQL dialect
        assert engine.dialect.name == "postgresql"
        
        # Verify connection pool configuration
        assert isinstance(engine.pool, QueuePool)
        assert engine.pool.size() == 10
        assert engine.pool._max_overflow == 20
        assert engine.pool._timeout == 30
        assert engine.pool._pre_ping is True
        
        # Verify session factory is created
        assert session_factory is not None
    
    def test_check_db_connection_success(self, monkeypatch):
        """Test check_db_connection returns True for valid connection."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        result = database.check_db_connection()
        assert result is True
    
    def test_check_db_connection_failure_returns_false(self, monkeypatch):
        """Test check_db_connection returns False for invalid database URL."""
        monkeypatch.setenv("DATABASE_URL", "invaliddb://user:pass@localhost/db")
        
        result = database.check_db_connection()
        assert result is False
    
    def test_get_db_handles_exceptions(self):
        """Test that get_db properly handles exceptions and cleanup."""
        exception_occurred = False
        
        try:
            db_gen = database.get_db()
            session = next(db_gen)
            
            # Force an exception by executing invalid SQL
            session.execute(text("INVALID SQL SYNTAX"))
        except Exception:
            exception_occurred = True
            db_gen.close()
        
        # Verify exception was properly handled
        assert exception_occurred is True
    
    def test_create_engine_and_session_factory_with_custom_url(self):
        """Test create_engine_and_session_factory with custom URL parameter."""
        custom_url = "sqlite:///test.db"
        engine, session_factory = database.create_engine_and_session_factory(db_url=custom_url)
        
        # Verify engine uses custom URL
        assert engine.dialect.name == "sqlite"
        assert session_factory is not None
        
        # Test session creation
        session = session_factory()
        result = session.execute(text("SELECT 1")).scalar_one()
        assert result == 1
        session.close()
    
    def test_get_db_context_manager_style(self):
        """Test using get_db generator properly for session management."""
        db_gen = database.get_db()
        session = next(db_gen)
        
        try:
            result = session.execute(text("SELECT 1")).scalar_one()
            assert result == 1
            assert isinstance(session, Session)
        finally:
            db_gen.close()
    
    def test_session_factory_configuration(self):
        """Test that session factory creates sessions with correct configuration."""
        engine, session_factory = database.create_engine_and_session_factory()
        
        session = session_factory()
        
        # Verify session configuration
        assert session.autoflush is False
        # Verify session is bound to engine
        assert session.bind is engine
        
        session.close()
