"""Tests for the SQLAlchemy Base model.

This module contains tests to verify that the Base declarative class
is properly configured and importable.
"""

import pytest
from sqlalchemy.orm import DeclarativeBase

from kb_web_svc.models import Base


class TestBase:
    """Test cases for the SQLAlchemy Base model."""
    
    def test_base_import(self):
        """Test that Base can be imported from kb_web_svc.models."""
        # This test passes if the import in the module level succeeds
        assert Base is not None
    
    def test_base_is_declarative_base(self):
        """Test that Base is an instance of DeclarativeBase."""
        # In SQLAlchemy 2.x, we check if it's a subclass of DeclarativeBase
        assert issubclass(Base, DeclarativeBase)
    
    def test_base_has_metadata(self):
        """Test that Base has metadata attribute."""
        assert hasattr(Base, 'metadata')
        assert Base.metadata is not None
    
    def test_base_has_registry(self):
        """Test that Base has registry attribute (SQLAlchemy 2.x feature)."""
        assert hasattr(Base, 'registry')
        assert Base.registry is not None
