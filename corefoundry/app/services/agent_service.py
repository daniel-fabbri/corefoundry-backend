"""Agent service for managing agents and their interactions."""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from corefoundry.app.db.models import Agent, Message
from corefoundry.app.services.ollama_service import ollama_service
from corefoundry.app.services.memory_service import MemoryService
from corefoundry.app.services.knowledge_service import KnowledgeService
from langchain_community.chat_models import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain_postgres import PostgresChatMessageHistory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from corefoundry.configs.settings import settings


class AgentService:
    """Service for managing agents."""
    
    def __init__(self, db: Session):
        """
        Initialize agent service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.memory_service = MemoryService(db)
        self.knowledge_service = KnowledgeService(db)
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        Create a new agent.
        
        Args:
            name: Agent name
            description: Agent description
            model_name: Ollama model name
            config: Optional configuration
            
        Returns:
            Created Agent object
        """
        agent = Agent(
            name=name,
            description=description,
            model_name=model_name or settings.OLLAMA_MODEL,
            config=config or {}
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent
    
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent object or None if not found
        """
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def list_agents(self, limit: int = 100) -> List[Agent]:
        """
        List all agents.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of Agent objects
        """
        return self.db.query(Agent).order_by(
            Agent.created_at.desc()
        ).limit(limit).all()
    
    def delete_agent(self, agent_id: int) -> bool:
        """
        Delete an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if deleted, False if not found
        """
        agent = self.get_agent(agent_id)
        if agent:
            self.db.delete(agent)
            self.db.commit()
            return True
        return False
    
    def save_message(
        self,
        agent_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Save a message to the database.
        
        Args:
            agent_id: Agent ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created Message object
        """
        message = Message(
            agent_id=agent_id,
            role=role,
            content=content,
            message_metadata=metadata
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_conversation_history(
        self,
        agent_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation history for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of messages
            
        Returns:
            List of Message objects
        """
        return self.db.query(Message).filter(
            Message.agent_id == agent_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
    
    def chat(
        self,
        agent_id: int,
        user_input: str,
        use_knowledge: bool = False
    ) -> Dict[str, Any]:
        """
        Chat with an agent.
        
        Args:
            agent_id: Agent ID
            user_input: User message
            use_knowledge: Whether to use knowledge base for context
            
        Returns:
            Dictionary with 'response' and 'metadata'
            
        Raises:
            ValueError: If agent not found
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Save user message
        self.save_message(agent_id, "user", user_input)
        
        # Get conversation history
        history = self.get_conversation_history(agent_id, limit=10)
        
        # Build messages for Ollama
        messages = []
        
        # Add system message if configured
        if agent.config and agent.config.get("system_prompt"):
            messages.append({
                "role": "system",
                "content": agent.config["system_prompt"]
            })
        
        # Add knowledge context if requested
        if use_knowledge:
            relevant_chunks = self.knowledge_service.search_chunks(user_input, limit=3)
            if relevant_chunks:
                context = "\n\n".join([chunk.content for chunk in relevant_chunks])
                messages.append({
                    "role": "system",
                    "content": f"Relevant context:\n{context}"
                })
        
        # Add conversation history (reverse to get chronological order)
        for msg in reversed(history[1:]):  # Skip the user message we just saved
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Call Ollama
        try:
            response = ollama_service.chat(
                messages=messages,
                model=agent.model_name,
                temperature=agent.config.get("temperature", 0.7) if agent.config else 0.7
            )
            
            assistant_message = response.get("message", {}).get("content", "")
            
            # Save assistant message
            self.save_message(agent_id, "assistant", assistant_message)
            
            return {
                "response": assistant_message,
                "metadata": {
                    "model": agent.model_name,
                    "agent_id": agent_id,
                    "agent_name": agent.name
                }
            }
        except Exception as e:
            error_message = f"Error communicating with Ollama: {str(e)}"
            return {
                "response": error_message,
                "metadata": {
                    "error": True,
                    "agent_id": agent_id
                }
            }
