"""Authentication service."""

import jwt
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from corefoundry.app.db.auth_models import AuthUser
from corefoundry.configs.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for user authentication."""

    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)

    def create_user(self, email: str, username: str, password: str) -> AuthUser:
        """Create a new user."""
        # Check if user already exists
        existing_email = self.db.query(AuthUser).filter(AuthUser.email == email).first()
        if existing_email:
            raise ValueError("Email already registered")

        existing_username = self.db.query(AuthUser).filter(AuthUser.username == username).first()
        if existing_username:
            raise ValueError("Username already taken")

        hashed_password = self.get_password_hash(password)
        user = AuthUser(
            email=email,
            username=username,
            hashed_password=hashed_password,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[AuthUser]:
        """Authenticate a user by email and password."""
        user = self.db.query(AuthUser).filter(AuthUser.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    def get_user_by_id(self, user_id: int) -> Optional[AuthUser]:
        """Get user by ID."""
        return self.db.query(AuthUser).filter(AuthUser.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Get user by email."""
        return self.db.query(AuthUser).filter(AuthUser.email == email).first()

    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[int]:
        """Decode JWT access token and return user_id."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return int(user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
