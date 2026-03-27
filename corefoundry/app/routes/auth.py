"""Authentication routes."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import get_db
from corefoundry.app.services.auth_service import AuthService
from corefoundry.app.services import api_key_service
from corefoundry.app.db.auth_models import AuthUser


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    username: str
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password."""
        if not v or len(v) < 3:
            raise ValueError('Password must be at least 3 characters')
        # Truncate to 72 bytes for bcrypt
        if len(v.encode('utf-8')) > 72:
            v = v.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return v


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response model for authentication."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Response model for user info."""
    id: int
    email: str
    username: str
    created_at: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthUser:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    auth_service = AuthService(db)
    user_id = auth_service.decode_access_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    auth_service = AuthService(db)
    
    # Debug: log password length
    print(f"[DEBUG] Register - Password length: {len(request.password)} chars, {len(request.password.encode('utf-8'))} bytes")
    
    try:
        user = auth_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    access_token = auth_service.create_access_token(user.id)
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at.isoformat()
        }
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login a user."""
    auth_service = AuthService(db)
    
    user = auth_service.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(user.id)
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at.isoformat()
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at.isoformat()
    )


# ============================================================================
# API Key Management
# ============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request model for creating API key."""
    name: str
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """Response model for API key."""
    id: int
    name: str
    prefix: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool
    created_at: str
    key: Optional[str] = None  # Only populated on creation


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for the current user."""
    try:
        api_key_obj, full_key = api_key_service.create_api_key(
            db=db,
            user_id=current_user.id,
            name=request.name,
            expires_at=request.expires_at
        )
        
        return APIKeyResponse(
            id=api_key_obj.id,
            name=api_key_obj.name,
            prefix=api_key_obj.prefix,
            last_used_at=api_key_obj.last_used_at.isoformat() if api_key_obj.last_used_at else None,
            expires_at=api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None,
            is_active=api_key_obj.is_active,
            created_at=api_key_obj.created_at.isoformat(),
            key=full_key  # Only shown once!
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}")


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the current user."""
    keys = api_key_service.list_user_api_keys(db, current_user.id)
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            prefix=key.prefix,
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            is_active=key.is_active,
            created_at=key.created_at.isoformat(),
            key=None  # Never return the full key after creation
        )
        for key in keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an API key."""
    success = api_key_service.delete_api_key(db, key_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key deleted successfully"}


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    auth_service = AuthService(db)
    
    # Verify current password if changing password
    if request.new_password:
        if not request.current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password required to change password"
            )
        
        if not auth_service.verify_password(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Incorrect current password"
            )
        
        # Update password
        current_user.hashed_password = auth_service.hash_password(request.new_password)
    
    # Update email if provided
    if request.email and request.email != current_user.email:
        # Check if email already exists
        existing_user = db.query(AuthUser).filter(
            AuthUser.email == request.email,
            AuthUser.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = request.email
    
    # Update username if provided
    if request.username and request.username != current_user.username:
        # Check if username already exists
        existing_user = db.query(AuthUser).filter(
            AuthUser.username == request.username,
            AuthUser.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already in use")
        current_user.username = request.username
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at.isoformat()
    )
