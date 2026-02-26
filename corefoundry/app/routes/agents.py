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
        result = service.chat(
            agent_id=agent_id,
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
async def get_history(agent_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """
    Get conversation history for an agent.
    
    Args:
        agent_id: Agent ID
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
    
    messages = service.get_conversation_history(agent_id, limit)
    
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
