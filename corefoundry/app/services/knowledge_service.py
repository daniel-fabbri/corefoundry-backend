"""Knowledge service for managing knowledge base."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from corefoundry.app.db.models import KnowledgeChunk
from langchain.text_splitter import RecursiveCharacterTextSplitter


class KnowledgeService:
    """Service for managing knowledge base."""
    
    def __init__(self, db: Session):
        """
        Initialize knowledge service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def upload_text(
        self,
        text: str,
        agent_id: Optional[int] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeChunk]:
        """
        Upload text to knowledge base, splitting it into chunks.
        
        Args:
            text: Text to upload
            agent_id: Optional agent ID to associate chunks with
            source: Source of the text (e.g., filename, URL)
            metadata: Optional metadata
            
        Returns:
            List of created KnowledgeChunk objects
        """
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create knowledge chunks
        knowledge_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            
            knowledge_chunk = KnowledgeChunk(
                agent_id=agent_id,
                content=chunk,
                source=source,
                chunk_metadata=chunk_metadata
            )
            self.db.add(knowledge_chunk)
            knowledge_chunks.append(knowledge_chunk)
        
        self.db.commit()
        
        # Refresh all chunks
        for chunk in knowledge_chunks:
            self.db.refresh(chunk)
        
        return knowledge_chunks
    
    def search_chunks(
        self,
        query: str,
        agent_id: Optional[int] = None,
        limit: int = 5
    ) -> List[KnowledgeChunk]:
        """
        Search for relevant knowledge chunks.
        
        For now, this is a simple text search. In the future, this could use
        vector embeddings for semantic search.
        
        Args:
            query: Search query
            agent_id: Optional agent ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of KnowledgeChunk objects
        """
        # Simple text search using SQL LIKE
        # In production, you'd want to use vector embeddings
        query_obj = self.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.content.ilike(f"%{query}%")
        )
        
        if agent_id is not None:
            query_obj = query_obj.filter(KnowledgeChunk.agent_id == agent_id)
        
        return query_obj.limit(limit).all()
    
    def get_chunk(self, chunk_id: int) -> Optional[KnowledgeChunk]:
        """
        Get a specific knowledge chunk.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            KnowledgeChunk object or None if not found
        """
        return self.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.id == chunk_id
        ).first()
    
    def get_all_chunks(
        self,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeChunk]:
        """
        Get all knowledge chunks, optionally filtered by source.
        
        Args:
            source: Optional source filter
            limit: Maximum number of results
            
        Returns:
            List of KnowledgeChunk objects
        """
        query = self.db.query(KnowledgeChunk)
        
        if source:
            query = query.filter(KnowledgeChunk.source == source)
        
        return query.order_by(
            KnowledgeChunk.created_at.desc()
        ).limit(limit).all()
    
    def delete_chunk(self, chunk_id: int) -> bool:
        """
        Delete a knowledge chunk.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            True if deleted, False if not found
        """
        chunk = self.get_chunk(chunk_id)
        if chunk:
            self.db.delete(chunk)
            self.db.commit()
            return True
        return False
    
    def delete_by_source(self, agent_id: int, source: str) -> int:
        """
        Delete all chunks from a specific source for a specific agent.
        
        Args:
            agent_id: Agent ID
            source: Source to delete
            
        Returns:
            Number of chunks deleted
        """
        count = self.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.agent_id == agent_id,
            KnowledgeChunk.source == source
        ).delete()
        self.db.commit()
        return count
    
    def get_chunks_by_agent(self, agent_id: int, limit: int = 100) -> List[KnowledgeChunk]:
        """
        Get all knowledge chunks for a specific agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of results
            
        Returns:
            List of KnowledgeChunk objects
        """
        return self.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.agent_id == agent_id
        ).order_by(
            KnowledgeChunk.created_at.desc()
        ).limit(limit).all()
