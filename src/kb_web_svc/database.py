import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError

# Import config to ensure dotenv is loaded
from . import config

logger = logging.getLogger(__name__)

# Module-level cache for engine and session factory
_ENGINE = None
_SESSION_FACTORY = None
_CURRENT_DB_URL = None


def get_db_url() -> str:
    """Get database URL from environment variables.
    
    Returns:
        Database URL string. Defaults to sqlite:///:memory: if DATABASE_URL is not set.
    """
    return os.getenv("DATABASE_URL", "sqlite:///:memory:")


def create_engine_and_session_factory(db_url: str | None = None) -> tuple[Engine, sessionmaker[Session]]:
    """Create and return SQLAlchemy Engine and sessionmaker.
    
    Args:
        db_url: Database URL. If None, uses get_db_url().
        
    Returns:
        Tuple of (Engine, sessionmaker)
        
    Raises:
        SQLAlchemyError: If engine creation fails.
    """
    global _ENGINE, _SESSION_FACTORY, _CURRENT_DB_URL
    
    effective_url = db_url or get_db_url()
    
    # Return cached instances if URL hasn't changed
    if _ENGINE is not None and _SESSION_FACTORY is not None and _CURRENT_DB_URL == effective_url:
        return _ENGINE, _SESSION_FACTORY
    
    try:
        url_obj = make_url(effective_url)
        
        # Configure engine based on database type
        if url_obj.drivername.startswith("postgresql"):
            # PostgreSQL configuration with connection pooling
            engine = create_engine(
                effective_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_pre_ping=True
            )
        elif url_obj.drivername.startswith("sqlite"):
            # SQLite configuration
            engine = create_engine(
                effective_url,
                connect_args={"check_same_thread": False}
            )
        else:
            # Default configuration for other databases
            engine = create_engine(effective_url)
        
        # Create sessionmaker with required configuration
        # autocommit is not used in SQLAlchemy 2.x; default explicit commit semantics
        session_factory = sessionmaker(bind=engine, autoflush=False)
        
        # Cache for reuse
        _ENGINE = engine
        _SESSION_FACTORY = session_factory
        _CURRENT_DB_URL = effective_url
        
        return engine, session_factory
        
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def get_db() -> Generator[Session, None, None]:
    """Provide a database session with proper lifecycle management.
    
    Yields:
        SQLAlchemy Session instance.
        
    The session is automatically closed after use, even if errors occur.
    """
    engine, session_factory = create_engine_and_session_factory()
    session = session_factory()
    
    try:
        yield session
    except Exception as e:
        logger.error(e, exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Check database connectivity.
    
    Returns:
        True if connection successful, False otherwise.
    """
    try:
        with next(get_db()) as session:
            result = session.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception as e:
        logger.error(e, exc_info=True)
        return False


def _reset_db_state() -> None:
    """Reset cached database state. Used for testing purposes."""
    global _ENGINE, _SESSION_FACTORY, _CURRENT_DB_URL
    _ENGINE = None
    _SESSION_FACTORY = None
    _CURRENT_DB_URL = None
