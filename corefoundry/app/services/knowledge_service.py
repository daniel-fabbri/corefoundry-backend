"""Knowledge service for managing knowledge base."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from corefoundry.app.db.models import KnowledgeChunk
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import re


# Stop words em português (palavras comuns que não agregam significado na busca)
STOP_WORDS = {
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
    'um', 'uma', 'uns', 'umas', 'por', 'para', 'com', 'sem', 'sob', 'sobre',
    'que', 'qual', 'quais', 'quando', 'onde', 'como', 'é', 'são', 'era', 'eram',
    'foi', 'foram', 'ser', 'estar', 'ter', 'haver', 'fazer', 'ir', 'vir', 'ver',
    'e', 'ou', 'mas', 'se', 'não', 'também', 'só', 'já', 'mais', 'muito', 'esse',
    'essa', 'este', 'esta', 'isso', 'isto', 'aquele', 'aquela', 'aquilo', 'me', 'te',
    'lhe', 'nos', 'vos', 'lhes', 'meu', 'teu', 'seu', 'nosso', 'vosso', 'minha',
    'tua', 'sua', 'nossa', 'vossa', 'dele', 'dela', 'deles', 'delas'
}


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
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract relevant keywords from query by removing stop words.
        
        Args:
            query: Search query
            
        Returns:
            List of keywords
        """
        # Convert to lowercase and remove punctuation
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into words
        words = clean_query.split()
        
        # Remove stop words and short words (< 3 chars)
        keywords = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
        
        return keywords
    
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
        Search for relevant knowledge chunks using keyword extraction.
        
        Extracts keywords from the query and searches for chunks containing
        any of those keywords. This improves recall compared to exact phrase matching.
        
        Args:
            query: Search query
            agent_id: Optional agent ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of KnowledgeChunk objects
        """
        logger = logging.getLogger("corefoundry.knowledge.search")
        logger.info("Searching chunks: query='%s' agent_id=%s limit=%d", query, agent_id, limit)
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        logger.info("Extracted keywords: %s", keywords)
        
        # Build query with OR conditions for each keyword
        query_obj = self.db.query(KnowledgeChunk)
        
        if keywords:
            # Create OR conditions for each keyword
            keyword_filters = [
                KnowledgeChunk.content.ilike(f"%{keyword}%") 
                for keyword in keywords
            ]
            query_obj = query_obj.filter(or_(*keyword_filters))
        else:
            # Fallback to original query if no keywords extracted
            logger.warning("No keywords extracted from query, using original: '%s'", query)
            query_obj = query_obj.filter(KnowledgeChunk.content.ilike(f"%{query}%"))
        
        if agent_id is not None:
            query_obj = query_obj.filter(KnowledgeChunk.agent_id == agent_id)
            logger.info("Filtering by agent_id=%s", agent_id)
        
        results = query_obj.limit(limit).all()
        logger.info("Search returned %d chunks", len(results))
        
        if len(results) == 0:
            # Log diagnostic info
            total_chunks = self.db.query(KnowledgeChunk).count()
            if agent_id is not None:
                agent_chunks = self.db.query(KnowledgeChunk).filter(KnowledgeChunk.agent_id == agent_id).count()
                logger.warning("No matches found! Total chunks in DB: %d, Chunks for agent_id=%s: %d", 
                             total_chunks, agent_id, agent_chunks)
                # Log sample chunk content for debugging
                if agent_chunks > 0:
                    sample = self.db.query(KnowledgeChunk).filter(
                        KnowledgeChunk.agent_id == agent_id
                    ).first()
                    logger.warning("Sample chunk content: '%s'", sample.content[:200])
            else:
                logger.warning("No matches found! Total chunks in DB: %d", total_chunks)
        
        return results
    
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
