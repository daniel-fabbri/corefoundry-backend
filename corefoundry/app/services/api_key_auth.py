"""Dependency for API Key authentication."""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import get_db
from corefoundry.app.db.auth_models import AuthUser
from corefoundry.app.services import api_key_service


async def get_api_key_user(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[AuthUser]:
    """
    Dependency to authenticate user via API Key.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: AuthUser = Depends(get_api_key_user)):
            ...
    
    The API key should be sent in the X-API-Key header:
        X-API-Key: cfk_your_api_key_here
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Please provide X-API-Key header.",
        )
    
    user = api_key_service.verify_api_key(db, x_api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_api_key_user_optional(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[AuthUser]:
    """
    Optional API key authentication - returns None if no key provided.
    Useful for endpoints that work both with and without authentication.
    """
    if not x_api_key:
        return None
    
    user = api_key_service.verify_api_key(db, x_api_key)
    
    if user and not user.is_active:
        return None
    
    return user
