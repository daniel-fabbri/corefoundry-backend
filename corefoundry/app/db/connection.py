"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from corefoundry.configs.settings import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create base class for models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_db():
    """
    Get database session.
    
    Yields:
        Session: Database session
        
    Usage:
        from corefoundry.app.db.connection import get_db
        
        def my_function(db: Session = Depends(get_db)):
            # Use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    
    Creates all tables defined in models.
    """
    from corefoundry.app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
