"""Base SQLAlchemy model for the kb_web_svc application.

This module defines the DeclarativeBase that all ORM models should inherit from.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.
    
    All database models in the application should inherit from this class.
    This provides the foundation for SQLAlchemy's declarative mapping.
    """
    pass
