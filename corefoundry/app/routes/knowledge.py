"""Knowledge base routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import get_db
from corefoundry.app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# Request/Response models
class UploadKnowledgeRequest(BaseModel):
    """Request model for uploading knowledge."""
    text: str
    source: Optional[str] = None
    metadata: Optional[dict] = None


class KnowledgeChunkResponse(BaseModel):
    """Response model for knowledge chunk."""
    id: int
    content: str
    source: Optional[str]
    metadata: Optional[dict]
    created_at: str
    
    class Config:
        from_attributes = True


class SearchKnowledgeRequest(BaseModel):
    """Request model for searching knowledge."""
    query: str
    limit: int = 5


# Routes
@router.post("/upload")
async def upload_knowledge(
    request: UploadKnowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    Upload text to the knowledge base.
    
    The text will be split into chunks and stored in the database.
    
    Args:
        request: Upload request
        db: Database session
        
    Returns:
        Information about created chunks
    """
    service = KnowledgeService(db)
    
    chunks = service.upload_text(
        text=request.text,
        source=request.source,
        metadata=request.metadata
    )
    
    return {
        "message": "Knowledge uploaded successfully",
        "chunks_created": len(chunks),
        "chunk_ids": [chunk.id for chunk in chunks]
    }


@router.post("/search", response_model=list[KnowledgeChunkResponse])
async def search_knowledge(
    request: SearchKnowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    Search the knowledge base.
    
    Args:
        request: Search request
        db: Database session
        
    Returns:
        List of relevant knowledge chunks
    """
    service = KnowledgeService(db)
    
    chunks = service.search_chunks(
        query=request.query,
        limit=request.limit
    )
    
    return [
        KnowledgeChunkResponse(
            id=chunk.id,
            content=chunk.content,
            source=chunk.source,
            metadata=chunk.metadata,
            created_at=chunk.created_at.isoformat()
        )
        for chunk in chunks
    ]


@router.get("/chunks", response_model=list[KnowledgeChunkResponse])
async def get_chunks(
    source: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all knowledge chunks, optionally filtered by source.
    
    Args:
        source: Optional source filter
        limit: Maximum number of chunks
        db: Database session
        
    Returns:
        List of knowledge chunks
    """
    service = KnowledgeService(db)
    
    chunks = service.get_all_chunks(source=source, limit=limit)
    
    return [
        KnowledgeChunkResponse(
            id=chunk.id,
            content=chunk.content,
            source=chunk.source,
            metadata=chunk.metadata,
            created_at=chunk.created_at.isoformat()
        )
        for chunk in chunks
    ]


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: int, db: Session = Depends(get_db)):
    """
    Delete a knowledge chunk.
    
    Args:
        chunk_id: Chunk ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If chunk not found
    """
    service = KnowledgeService(db)
    
    if not service.delete_chunk(chunk_id):
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return {"message": "Chunk deleted successfully"}


@router.delete("/source/{source}")
async def delete_by_source(source: str, db: Session = Depends(get_db)):
    """
    Delete all chunks from a specific source.
    
    Args:
        source: Source to delete
        db: Database session
        
    Returns:
        Information about deletion
    """
    service = KnowledgeService(db)
    
    count = service.delete_by_source(source)
    
    return {
        "message": f"Deleted {count} chunks from source '{source}'",
        "chunks_deleted": count
    }
