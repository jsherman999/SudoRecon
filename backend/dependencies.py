"""Dependency injection for FastAPI."""

from typing import Generator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.session import get_db

settings = get_settings()

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(api_key: str = Security(api_key_header)) -> str:
    """Validate API key and return user."""
    # For phase 1, simple validation
    # TODO: Implement proper user authentication in later phase
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    # For now, return a placeholder user
    return "api_user"


def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """Require admin role."""
    # TODO: Implement proper role checking
    return current_user
