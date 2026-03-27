"""Agent service for managing agents and their interactions."""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from corefoundry.app.db.models import Agent, Message, ChatUser, Thread
from corefoundry.app.db.auth_models import AuthUser
from corefoundry.app.services.ollama_service import ollama_service
from corefoundry.app.services.memory_service import MemoryService
from corefoundry.app.services.knowledge_service import KnowledgeService
from langchain_postgres import PostgresChatMessageHistory
from langchain.schema import HumanMessage, AIMessage
from corefoundry.configs.settings import settings
import logging


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
        user_id: int,
        name: str,
        description: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        Create a new agent.
        
        Args:
            user_id: User ID who owns the agent
            name: Agent name
            description: Agent description
            model_name: Ollama model name
            config: Optional configuration
            
        Returns:
            Created Agent object
        """
        agent = Agent(
            user_id=user_id,
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
    
    def list_agents(self, user_id: Optional[int] = None, limit: int = 100) -> List[Agent]:
        """
        List agents, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter agents by owner
            limit: Maximum number of agents to return
            
        Returns:
            List of Agent objects
        """
        query = self.db.query(Agent)
        
        if user_id is not None:
            query = query.filter(Agent.user_id == user_id)
        
        return query.order_by(
            Agent.created_at.desc()
        ).limit(limit).all()

    def list_chat_users(self) -> List[ChatUser]:
        """List all chat users."""
        users = self.db.query(ChatUser).order_by(ChatUser.name.asc()).all()
        if users:
            return users
        return [self.create_chat_user("Default User")]

    def create_chat_user(self, name: str) -> ChatUser:
        """Create a chat user if it does not already exist."""
        existing = self.db.query(ChatUser).filter(ChatUser.name == name).first()
        if existing:
            return existing

        user = ChatUser(name=name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_chat_user(self, user_id: int) -> Optional[ChatUser]:
        """Get chat user by ID."""
        return self.db.query(ChatUser).filter(ChatUser.id == user_id).first()

    def create_thread(
        self,
        agent_id: int,
        user_id: int,
        title: Optional[str] = None
    ) -> Thread:
        """Create a thread scoped to a user and agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Validate user exists in auth_users
        user = self.db.query(AuthUser).filter(AuthUser.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        thread = Thread(
            agent_id=agent_id,
            user_id=user_id,
            title=title or f"Thread {agent.name}"
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def list_threads(self, agent_id: int, user_id: int) -> List[Thread]:
        """List threads for a specific user-agent pair."""
        return self.db.query(Thread).filter(
            Thread.agent_id == agent_id,
            Thread.user_id == user_id
        ).order_by(Thread.updated_at.desc()).all()

    def get_thread(self, thread_id: int) -> Optional[Thread]:
        """Get thread by ID."""
        return self.db.query(Thread).filter(Thread.id == thread_id).first()

    def validate_thread_scope(self, agent_id: int, user_id: int, thread_id: int) -> Thread:
        """Validate that thread belongs to provided agent and user."""
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        if thread.agent_id != agent_id:
            raise ValueError("Thread does not belong to the selected agent")
        if thread.user_id != user_id:
            raise ValueError("Thread does not belong to the selected user")
        return thread
    
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
        thread_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Save a message to the database.
        
        Args:
            agent_id: Agent ID
            thread_id: Thread ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created Message object
        """
        message = Message(
            agent_id=agent_id,
            thread_id=thread_id,
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
        thread_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation history for an agent.
        
        Args:
            agent_id: Agent ID
            thread_id: Thread ID
            limit: Maximum number of messages
            
        Returns:
            List of Message objects
        """
        return self.db.query(Message).filter(
            Message.agent_id == agent_id,
            Message.thread_id == thread_id
        ).order_by(Message.created_at.desc()).limit(limit).all()

    def _sync_langchain_history(
        self,
        agent_id: int,
        user_id: int,
        thread_id: int,
        user_input: str,
        assistant_message: str
    ) -> None:
        """
        Keep a LangChain-compatible history keyed by thread.

        The session_id is scoped by agent/user/thread to guarantee memory isolation.
        """
        session_id = f"agent:{agent_id}:user:{user_id}:thread:{thread_id}"
        try:
            history = PostgresChatMessageHistory(
                table_name="langchain_chat_histories",
                session_id=session_id,
                connection=settings.DATABASE_URL,
            )
            history.add_messages([
                HumanMessage(content=user_input),
                AIMessage(content=assistant_message),
            ])
        except Exception:
            # Keep chat flow functional even if LangChain history table is not initialized.
            return
    
    async def _extract_and_save_memories(
        self,
        agent_id: int,
        user_input: str,
        assistant_message: str,
        model_name: str
    ) -> None:
        """
        Extract important information from conversation and save as memories.
        
        Args:
            agent_id: Agent ID
            user_input: User's message
            assistant_message: Assistant's response
            model_name: Model to use for extraction
        """
        logger = logging.getLogger("corefoundry.agent.memory")
        
        try:
            # Create a prompt to extract memorable information
            extraction_prompt = f"""Analyze the following conversation and extract important information that should be remembered.

User: {user_input}
Assistant: {assistant_message}

Extract information in the following format (only if relevant information exists):
- If the user mentions their name, preferences, projects, or personal information
- If important facts or decisions are discussed
- If specific details about tasks or goals are mentioned

Return ONLY a JSON object with key-value pairs of memorable information. Keys should be descriptive (e.g., "user_name", "preferred_language", "current_project").
If there's nothing important to remember, return an empty JSON object: {{}}

Example response:
{{"user_name": "João", "preferred_language": "Python", "current_project": "CoreFoundry"}}

JSON:"""

            # Call LLM to extract memories
            response = await ollama_service.chat(
                messages=[{"role": "user", "content": extraction_prompt}],
                model=model_name,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            content = response.get("message", {}).get("content", "").strip()
            
            # Try to parse JSON response
            import json
            try:
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                memories = json.loads(content)
                
                # Save each memory
                if memories and isinstance(memories, dict):
                    for key, value in memories.items():
                        if key and value:  # Only save non-empty keys/values
                            self.memory_service.save_memory(
                                agent_id=agent_id,
                                key=key,
                                value=str(value),
                                metadata={
                                    "auto_extracted": True,
                                    "source": "conversation"
                                }
                            )
                            logger.info(f"Auto-saved memory: {key} = {value}")
            
            except json.JSONDecodeError:
                logger.debug(f"Could not parse memories from LLM response: {content}")
                
        except Exception as e:
            # Don't break chat flow if memory extraction fails
            logger.warning(f"Failed to extract memories: {str(e)}")
    
    async def chat(
        self,
        agent_id: int,
        user_id: int,
        thread_id: int,
        user_input: str,
        use_knowledge: bool = False
    ) -> Dict[str, Any]:
        """
        Chat with an agent.
        
        Args:
            agent_id: Agent ID
            user_id: User ID
            thread_id: Thread ID
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

        self.validate_thread_scope(agent_id=agent_id, user_id=user_id, thread_id=thread_id)
        
        # Save user message
        self.save_message(agent_id, thread_id, "user", user_input)
        
        # Get conversation history
        history = self.get_conversation_history(agent_id, thread_id, limit=10)
        
        # Build messages for Ollama
        messages = []
        
        # Log request info
        logger = logging.getLogger("corefoundry.agent.chat")
        logger.info("=== CHAT REQUEST === agent_id=%s user_id=%s thread_id=%s use_knowledge=%s", 
                    agent_id, user_id, thread_id, use_knowledge)
        
        # Add system message if configured
        if agent.config and agent.config.get("system_prompt"):
            messages.append({
                "role": "system",
                "content": agent.config["system_prompt"]
            })
        
        # Add memories context (always include stored memories)
        memories = self.memory_service.get_all_memories(agent_id)
        if memories:
            memory_context = "Information I remember about you and our interactions:\n"
            for memory in memories:
                memory_context += f"- {memory.key}: {memory.value}\n"
            logger.info("Adding %d memories to context", len(memories))
            messages.append({
                "role": "system",
                "content": memory_context
            })
        
        # Add knowledge context if requested
        if use_knowledge:
            logger.info("Knowledge search: query='%s' agent_id=%s", user_input, agent_id)
            relevant_chunks = self.knowledge_service.search_chunks(
                query=user_input,
                agent_id=agent_id,
                limit=3
            )
            # Debug logging for knowledge usage
            logger.info("Found %d relevant chunks", len(relevant_chunks))
            if len(relevant_chunks) == 0:
                logger.warning("NO CHUNKS FOUND! Check: 1) chunks exist for agent_id=%s, 2) query matches content", agent_id)
            for idx, c in enumerate(relevant_chunks):
                # limit content length in logs
                preview = (c.content[:150] + "...") if len(c.content) > 150 else c.content
                logger.info("Chunk[%d]: id=%s source='%s' agent_id=%s preview='%s'", 
                           idx, getattr(c, 'id', None), getattr(c, 'source', None), 
                           getattr(c, 'agent_id', None), preview)
            if relevant_chunks:
                context = "\n\n".join([chunk.content for chunk in relevant_chunks])
                logger.info("Adding context to messages (%d chars total)", len(context))
                messages.append({
                    "role": "system",
                    "content": f"Relevant context from knowledge base:\n{context}"
                })
        else:
            logger.info("use_knowledge=False, skipping knowledge search")
        
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
            response = await ollama_service.chat(
                messages=messages,
                model=agent.model_name,
                temperature=agent.config.get("temperature", 0.7) if agent.config else 0.7
            )
            
            assistant_message = response.get("message", {}).get("content", "")
            
            # Save assistant message
            self.save_message(agent_id, thread_id, "assistant", assistant_message)
            self._sync_langchain_history(
                agent_id=agent_id,
                user_id=user_id,
                thread_id=thread_id,
                user_input=user_input,
                assistant_message=assistant_message,
            )
            
            # Extract and save memories (async, non-blocking)
            try:
                await self._extract_and_save_memories(
                    agent_id=agent_id,
                    user_input=user_input,
                    assistant_message=assistant_message,
                    model_name=agent.model_name
                )
            except Exception:
                # Don't break chat flow if memory extraction fails
                pass
            
            return {
                "response": assistant_message,
                "metadata": {
                    "model": agent.model_name,
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "thread_id": thread_id,
                    "user_id": user_id,
                }
            }
        except Exception as e:
            error_message = f"Error communicating with Ollama: {str(e)}"
            return {
                "response": error_message,
                "metadata": {
                    "error": True,
                    "agent_id": agent_id,
                    "thread_id": thread_id,
                    "user_id": user_id,
                }
            }
