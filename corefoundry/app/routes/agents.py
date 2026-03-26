"""Agent routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import get_db
from corefoundry.app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response models
class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""
    name: str
    description: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[dict] = None


class AgentResponse(BaseModel):
    """Response model for agent."""
    model_config = {"from_attributes": True}
    
    id: int
    name: str
    description: Optional[str]
    model_name: str
    config: Optional[dict]
    created_at: str


class ChatRequest(BaseModel):
    """Request model for chat."""
    input: str
    user_id: int
    thread_id: int
    use_knowledge: bool = False


class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    metadata: dict


class UploadKnowledgeRequest(BaseModel):
    """Request model for uploading knowledge."""
    text: str
    source: Optional[str] = None
    metadata: Optional[dict] = None


class ChatUserResponse(BaseModel):
    """Response model for chat user."""
    model_config = {"from_attributes": True}

    id: int
    name: str
    created_at: str


class CreateChatUserRequest(BaseModel):
    """Request model for creating chat user."""
    name: str


class ThreadResponse(BaseModel):
    """Response model for thread."""
    model_config = {"from_attributes": True}

    id: int
    agent_id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str


class CreateThreadRequest(BaseModel):
    """Request model for creating thread."""
    user_id: int
    title: Optional[str] = None


# Routes
@router.post("/create", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new agent.
    
    Args:
        request: Agent creation request
        db: Database session
        
    Returns:
        Created agent
    """
    service = AgentService(db)
    agent = service.create_agent(
        name=request.name,
        description=request.description,
        model_name=request.model_name,
        config=request.config
    )
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_name=agent.model_name,
        config=agent.config,
        created_at=agent.created_at.isoformat()
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """
    Get an agent by ID.
    
    Args:
        agent_id: Agent ID
        db: Database session
        
    Returns:
        Agent details
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_name=agent.model_name,
        config=agent.config,
        created_at=agent.created_at.isoformat()
    )


@router.get("/", response_model=list[AgentResponse])
async def list_agents(db: Session = Depends(get_db)):
    """
    List all agents.
    
    Args:
        db: Database session
        
    Returns:
        List of agents
    """
    service = AgentService(db)
    agents = service.list_agents()
    
    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            model_name=agent.model_name,
            config=agent.config,
            created_at=agent.created_at.isoformat()
        )
        for agent in agents
    ]


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat(
    agent_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with an agent.
    
    Args:
        agent_id: Agent ID
        request: Chat request
        db: Database session
        
    Returns:
        Chat response
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentService(db)
    
    try:
        result = await service.chat(
            agent_id=agent_id,
            user_id=request.user_id,
            thread_id=request.thread_id,
            user_input=request.input,
            use_knowledge=request.use_knowledge
        )
        
        return ChatResponse(
            response=result["response"],
            metadata=result["metadata"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """
    Delete an agent.
    
    Args:
        agent_id: Agent ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentService(db)
    
    if not service.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/history")
async def get_history(
    agent_id: int,
    user_id: int,
    thread_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get conversation history for an agent.
    
    Args:
        agent_id: Agent ID
        user_id: Selected user ID
        thread_id: Selected thread ID
        limit: Maximum number of messages
        db: Database session
        
    Returns:
        List of messages
    """
    service = AgentService(db)
    
    # Check if agent exists
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        service.validate_thread_scope(agent_id=agent_id, user_id=user_id, thread_id=thread_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    messages = service.get_conversation_history(agent_id, thread_id, limit)
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.message_metadata
        }
        for msg in reversed(messages)  # Return in chronological order
    ]


@router.get("/chat-users", response_model=list[ChatUserResponse])
async def list_chat_users(db: Session = Depends(get_db)):
    """List all chat users."""
    service = AgentService(db)
    users = service.list_chat_users()

    return [
        ChatUserResponse(
            id=user.id,
            name=user.name,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]


@router.post("/chat-users", response_model=ChatUserResponse)
async def create_chat_user(request: CreateChatUserRequest, db: Session = Depends(get_db)):
    """Create a chat user."""
    service = AgentService(db)
    user = service.create_chat_user(request.name)

    return ChatUserResponse(
        id=user.id,
        name=user.name,
        created_at=user.created_at.isoformat(),
    )


@router.get("/{agent_id}/threads", response_model=list[ThreadResponse])
async def list_threads(agent_id: int, user_id: int, db: Session = Depends(get_db)):
    """List threads for a specific user-agent pair."""
    service = AgentService(db)

    if not service.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    if not service.get_chat_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")

    threads = service.list_threads(agent_id=agent_id, user_id=user_id)
    return [
        ThreadResponse(
            id=thread.id,
            agent_id=thread.agent_id,
            user_id=thread.user_id,
            title=thread.title,
            created_at=thread.created_at.isoformat(),
            updated_at=thread.updated_at.isoformat(),
        )
        for thread in threads
    ]


@router.post("/{agent_id}/threads", response_model=ThreadResponse)
async def create_thread(agent_id: int, request: CreateThreadRequest, db: Session = Depends(get_db)):
    """Create a thread for a specific user-agent pair."""
    service = AgentService(db)
    try:
        thread = service.create_thread(
            agent_id=agent_id,
            user_id=request.user_id,
            title=request.title,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ThreadResponse(
        id=thread.id,
        agent_id=thread.agent_id,
        user_id=thread.user_id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )
