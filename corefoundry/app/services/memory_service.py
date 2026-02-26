"""Memory service for managing agent memory."""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from corefoundry.app.db.models import Memory


class MemoryService:
    """Service for managing agent memory."""
    
    def __init__(self, db: Session):
        """
        Initialize memory service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def save_memory(
        self,
        agent_id: int,
        key: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """
        Save a memory entry for an agent.
        
        Args:
            agent_id: Agent ID
            key: Memory key
            value: Memory value
            metadata: Optional metadata
            
        Returns:
            Created Memory object
        """
        # Check if memory with this key already exists
        existing = self.db.query(Memory).filter(
            Memory.agent_id == agent_id,
            Memory.key == key
        ).first()
        
        if existing:
            # Update existing memory
            existing.value = value
            if metadata:
                existing.memory_metadata = metadata
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new memory
        memory = Memory(
            agent_id=agent_id,
            key=key,
            value=value,
            memory_metadata=metadata
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def get_memory(self, agent_id: int, key: str) -> Optional[Memory]:
        """
        Get a specific memory entry.
        
        Args:
            agent_id: Agent ID
            key: Memory key
            
        Returns:
            Memory object or None if not found
        """
        return self.db.query(Memory).filter(
            Memory.agent_id == agent_id,
            Memory.key == key
        ).first()
    
    def get_all_memories(self, agent_id: int) -> List[Memory]:
        """
        Get all memory entries for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of Memory objects
        """
        return self.db.query(Memory).filter(
            Memory.agent_id == agent_id
        ).order_by(Memory.created_at.desc()).all()
    
    def delete_memory(self, agent_id: int, key: str) -> bool:
        """
        Delete a memory entry.
        
        Args:
            agent_id: Agent ID
            key: Memory key
            
        Returns:
            True if deleted, False if not found
        """
        memory = self.get_memory(agent_id, key)
        if memory:
            self.db.delete(memory)
            self.db.commit()
            return True
        return False
    
    def clear_all_memories(self, agent_id: int) -> int:
        """
        Clear all memories for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Number of memories deleted
        """
        count = self.db.query(Memory).filter(
            Memory.agent_id == agent_id
        ).delete()
        self.db.commit()
        return count
