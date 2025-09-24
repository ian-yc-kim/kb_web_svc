"""Core database connection and session management using SQLAlchemy.

This module provides database connectivity for both PostgreSQL and SQLite,
with connection pooling and proper session management.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Import config to ensure dotenv is loaded
from . import config

logger = logging.getLogger(__name__)

# Module-level engine and session factory - initialized lazily
ENGINE: Engine | None = None
SESSION_FACTORY: sessionmaker | None = None


def get_db_url() -> str:
    """Get database URL from environment variables.
    
    Returns:
        Database URL string. Defaults to SQLite in-memory if DATABASE_URL is not set.
    """
    return os.getenv("DATABASE_URL", "sqlite:///:memory:")


def create_engine_and_session_factory(db_url: str | None = None) -> Tuple[Engine, sessionmaker]:
    """Create SQLAlchemy engine and session factory.
    
    Args:
        db_url: Database URL. If None, uses get_db_url().
        
    Returns:
        Tuple of (engine, sessionmaker)
        
    Raises:
        Exception: If engine creation fails.
    """
    if db_url is None:
        db_url = get_db_url()
    
    try:
        if db_url.startswith("postgresql"):
            # PostgreSQL configuration with connection pooling
            engine = create_engine(
                db_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_pre_ping=True
            )
        else:
            # SQLite configuration
            connect_args = {"check_same_thread": False}
            if db_url == "sqlite:///:memory:":
                # Use StaticPool for in-memory SQLite to maintain single connection
                engine = create_engine(
                    db_url,
                    connect_args=connect_args,
                    poolclass=StaticPool
                )
            else:
                engine = create_engine(db_url, connect_args=connect_args)
        
        # Create sessionmaker with SQLAlchemy 2.0 compatible parameters
        # Remove deprecated autocommit=False, add expire_on_commit=False
        SessionLocal = sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False
        )
        
        return engine, SessionLocal
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        raise


def _ensure_initialized() -> None:
    """Ensure the module-level ENGINE and SESSION_FACTORY are initialized.
    
    This function is called lazily to initialize database connections
    using the current environment configuration.
    """
    global ENGINE, SESSION_FACTORY
    
    if SESSION_FACTORY is None:
        ENGINE, SESSION_FACTORY = create_engine_and_session_factory()


def _reset_db_state() -> None:
    """Reset the module-level database state.
    
    This function safely disposes the current engine and resets
    ENGINE and SESSION_FACTORY to None, forcing re-initialization
    on the next database access. Primarily used for testing.
    """
    global ENGINE, SESSION_FACTORY
    
    if ENGINE is not None:
        try:
            ENGINE.dispose()
        except Exception as e:
            logger.error(f"Error disposing database engine: {e}", exc_info=True)
    
    ENGINE = None
    SESSION_FACTORY = None


def get_db() -> Generator[Session, None, None]:
    """Get database session generator.
    
    Yields:
        SQLAlchemy Session instance.
        
    Ensures proper cleanup of the session even if errors occur.
    """
    _ensure_initialized()
    
    db = SESSION_FACTORY()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check database connectivity.
    
    Returns:
        True if connection successful, False otherwise.
    """
    db_gen = None
    try:
        db_gen = get_db()
        db = next(db_gen)
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}", exc_info=True)
        return False
    finally:
        # Ensure generator cleanup even if exceptions occur
        if db_gen is not None:
            try:
                next(db_gen)
            except StopIteration:
                pass  # Generator properly closed
            except Exception as cleanup_error:
                logger.error(f"Error during database cleanup: {cleanup_error}", exc_info=True)
