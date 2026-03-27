"""API Key service for managing user API keys."""

import secrets
import hashlib
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from corefoundry.app.db.auth_models import APIKey, AuthUser


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.
    
    Returns:
        Tuple of (full_key, key_hash, prefix)
        - full_key: The complete key to show user (only once)
        - key_hash: SHA256 hash to store in database
        - prefix: First 12 chars for display (e.g., "cfk_abc123...")
    """
    # Generate secure random token
    token = secrets.token_urlsafe(32)
    full_key = f"cfk_{token}"
    
    # Create SHA256 hash for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    # Create prefix for display
    prefix = full_key[:12] + "..."
    
    return full_key, key_hash, prefix


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(
    db: Session,
    user_id: int,
    name: str,
    expires_at: Optional[datetime] = None
) -> Tuple[APIKey, str]:
    """
    Create a new API key for a user.
    
    Args:
        db: Database session
        user_id: User ID
        name: Descriptive name for the key
        expires_at: Optional expiration date
    
    Returns:
        Tuple of (APIKey model, full_key_string)
    """
    full_key, key_hash, prefix = generate_api_key()
    
    api_key = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        name=name,
        prefix=prefix,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return api_key, full_key


def list_user_api_keys(db: Session, user_id: int) -> List[APIKey]:
    """List all API keys for a user."""
    return db.query(APIKey).filter(
        APIKey.user_id == user_id
    ).order_by(APIKey.created_at.desc()).all()


def revoke_api_key(db: Session, key_id: int, user_id: int) -> bool:
    """
    Revoke (deactivate) an API key.
    
    Args:
        db: Database session
        key_id: API key ID
        user_id: User ID (for authorization check)
    
    Returns:
        True if revoked, False if not found or not authorized
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not api_key:
        return False
    
    api_key.is_active = False
    db.commit()
    return True


def delete_api_key(db: Session, key_id: int, user_id: int) -> bool:
    """
    Permanently delete an API key.
    
    Args:
        db: Database session
        key_id: API key ID
        user_id: User ID (for authorization check)
    
    Returns:
        True if deleted, False if not found or not authorized
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not api_key:
        return False
    
    db.delete(api_key)
    db.commit()
    return True


def verify_api_key(db: Session, api_key: str) -> Optional[AuthUser]:
    """
    Verify an API key and return the associated user.
    
    Args:
        db: Database session
        api_key: The API key to verify
    
    Returns:
        AuthUser if valid, None if invalid
    """
    key_hash = hash_api_key(api_key)
    
    api_key_record = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not api_key_record:
        return None
    
    # Check expiration
    if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
        return None
    
    # Update last_used_at
    api_key_record.last_used_at = datetime.utcnow()
    db.commit()
    
    # Return the user
    return api_key_record.user
