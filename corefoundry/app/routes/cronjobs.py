"""Cronjob routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session
from datetime import datetime
from corefoundry.app.db.connection import get_db
from corefoundry.app.db.models import Cronjob, CronjobLog
from corefoundry.app.db.auth_models import AuthUser
from corefoundry.app.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cronjobs", tags=["cronjobs"])


# Request/Response models
class CreateCronjobRequest(BaseModel):
    """Request model for creating a cronjob."""
    name: str = Field(..., min_length=1, max_length=255, description="Cronjob name")
    description: Optional[str] = Field(None, description="Optional description")
    url: str = Field(..., description="URL to request")
    method: str = Field("GET", pattern="^(GET|POST|PUT|PATCH|DELETE)$", description="HTTP method")
    headers: Optional[dict] = Field(None, description="Optional HTTP headers")
    body: Optional[dict] = Field(None, description="Optional request body (for POST/PUT/PATCH)")
    interval_minutes: int = Field(1, ge=1, le=1440, description="Interval in minutes (1-1440)")
    is_active: bool = Field(True, description="Whether the cronjob is active")


class UpdateCronjobRequest(BaseModel):
    """Request model for updating a cronjob."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    headers: Optional[dict] = None
    body: Optional[dict] = None
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    is_active: Optional[bool] = None


class CronjobResponse(BaseModel):
    """Response model for cronjob."""
    model_config = {"from_attributes": True}
    
    id: int
    user_id: int
    name: str
    description: Optional[str]
    url: str
    method: str
    headers: Optional[dict]
    body: Optional[dict]
    interval_minutes: int
    is_active: bool
    last_run_at: Optional[datetime]
    last_status_code: Optional[int]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class CronjobLogResponse(BaseModel):
    """Response model for cronjob log."""
    model_config = {"from_attributes": True}
    
    id: int
    cronjob_id: int
    executed_at: datetime
    status_code: Optional[int]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    response_body: Optional[str]


# Routes
@router.get("", response_model=List[CronjobResponse])
def list_cronjobs(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """List all cronjobs for the current user."""
    try:
        cronjobs = db.query(Cronjob).filter(
            Cronjob.user_id == current_user.id
        ).order_by(Cronjob.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert is_active from int to bool for response
        for cronjob in cronjobs:
            cronjob.is_active = bool(cronjob.is_active)
        
        return cronjobs
    except Exception as e:
        logger.error(f"Error listing cronjobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list cronjobs")


@router.post("", response_model=CronjobResponse, status_code=201)
def create_cronjob(
    request: CreateCronjobRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Create a new cronjob."""
    try:
        cronjob = Cronjob(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            url=request.url,
            method=request.method.upper(),
            headers=request.headers,
            body=request.body,
            interval_minutes=request.interval_minutes,
            is_active=1 if request.is_active else 0
        )
        
        db.add(cronjob)
        db.commit()
        db.refresh(cronjob)
        
        # Convert is_active to bool for response
        cronjob.is_active = bool(cronjob.is_active)
        
        logger.info(f"Created cronjob {cronjob.id} for user {current_user.id}")
        return cronjob
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating cronjob: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create cronjob")


@router.get("/{cronjob_id}", response_model=CronjobResponse)
def get_cronjob(
    cronjob_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get a specific cronjob by ID."""
    cronjob = db.query(Cronjob).filter(
        Cronjob.id == cronjob_id,
        Cronjob.user_id == current_user.id
    ).first()
    
    if not cronjob:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    
    # Convert is_active to bool for response
    cronjob.is_active = bool(cronjob.is_active)
    
    return cronjob


@router.put("/{cronjob_id}", response_model=CronjobResponse)
def update_cronjob(
    cronjob_id: int,
    request: UpdateCronjobRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Update a cronjob."""
    cronjob = db.query(Cronjob).filter(
        Cronjob.id == cronjob_id,
        Cronjob.user_id == current_user.id
    ).first()
    
    if not cronjob:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    
    try:
        # Update only provided fields
        update_data = request.model_dump(exclude_unset=True)
        
        # Convert is_active to int for database
        if "is_active" in update_data:
            update_data["is_active"] = 1 if update_data["is_active"] else 0
        
        # Convert method to uppercase
        if "method" in update_data:
            update_data["method"] = update_data["method"].upper()
        
        for key, value in update_data.items():
            setattr(cronjob, key, value)
        
        db.commit()
        db.refresh(cronjob)
        
        # Convert is_active to bool for response
        cronjob.is_active = bool(cronjob.is_active)
        
        logger.info(f"Updated cronjob {cronjob_id}")
        return cronjob
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating cronjob: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cronjob")


@router.delete("/{cronjob_id}", status_code=204)
def delete_cronjob(
    cronjob_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Delete a cronjob."""
    cronjob = db.query(Cronjob).filter(
        Cronjob.id == cronjob_id,
        Cronjob.user_id == current_user.id
    ).first()
    
    if not cronjob:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    
    try:
        db.delete(cronjob)
        db.commit()
        logger.info(f"Deleted cronjob {cronjob_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting cronjob: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete cronjob")


@router.get("/{cronjob_id}/logs", response_model=List[CronjobLogResponse])
def get_cronjob_logs(
    cronjob_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get execution logs for a cronjob."""
    # Verify cronjob exists and belongs to user
    cronjob = db.query(Cronjob).filter(
        Cronjob.id == cronjob_id,
        Cronjob.user_id == current_user.id
    ).first()
    
    if not cronjob:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    
    try:
        logs = db.query(CronjobLog).filter(
            CronjobLog.cronjob_id == cronjob_id
        ).order_by(CronjobLog.executed_at.desc()).offset(skip).limit(limit).all()
        
        return logs
        
    except Exception as e:
        logger.error(f"Error getting cronjob logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cronjob logs")


@router.post("/{cronjob_id}/toggle", response_model=CronjobResponse)
def toggle_cronjob(
    cronjob_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Toggle a cronjob's active status."""
    cronjob = db.query(Cronjob).filter(
        Cronjob.id == cronjob_id,
        Cronjob.user_id == current_user.id
    ).first()
    
    if not cronjob:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    
    try:
        cronjob.is_active = 0 if cronjob.is_active else 1
        db.commit()
        db.refresh(cronjob)
        
        # Convert is_active to bool for response
        cronjob.is_active = bool(cronjob.is_active)
        
        logger.info(f"Toggled cronjob {cronjob_id} to {'active' if cronjob.is_active else 'inactive'}")
        return cronjob
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling cronjob: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to toggle cronjob")
