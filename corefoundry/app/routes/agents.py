"""Agent routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import get_db
from corefoundry.app.services.agent_service import AgentService
from corefoundry.app.services.memory_service import MemoryService
from corefoundry.app.services.knowledge_service import KnowledgeService
from corefoundry.app.db.auth_models import AuthUser
from corefoundry.app.routes.auth import get_current_user
import os
from pathlib import Path
import shutil

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
    title: Optional[str] = None


class MemoryResponse(BaseModel):
    """Response model for memory."""
    model_config = {"from_attributes": True}

    id: int
    agent_id: int
    key: str
    value: str
    metadata: Optional[dict]
    created_at: str
    updated_at: str


class KnowledgeFileResponse(BaseModel):
    """Response model for knowledge file."""
    filename: str
    size: int
    created_at: str
    agent_id: int


# Routes
@router.post("/create", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new agent.
    
    Args:
        request: Agent creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created agent
    """
    service = AgentService(db)
    agent = service.create_agent(
        user_id=current_user.id,
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
async def get_agent(
    agent_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get an agent by ID.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Agent details
        
    Raises:
        HTTPException: If agent not found or user doesn't have access
    """
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_name=agent.model_name,
        config=agent.config,
        created_at=agent.created_at.isoformat()
    )


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all agents for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of agents belonging to the current user
    """
    service = AgentService(db)
    agents = service.list_agents(user_id=current_user.id)
    
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
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with an agent.
    
    Args:
        agent_id: Agent ID
        request: Chat request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Chat response
        
    Raises:
        HTTPException: If agent not found or user doesn't have access
    """
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        result = await service.chat(
            agent_id=agent_id,
            user_id=current_user.id,
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
async def delete_agent(
    agent_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an agent.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If agent not found or user doesn't have access
    """
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service.delete_agent(agent_id)
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/history")
async def get_history(
    agent_id: int,
    thread_id: int,
    current_user: AuthUser = Depends(get_current_user),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get conversation history for an agent.
    
    Args:
        agent_id: Agent ID
        thread_id: Thread ID
        current_user: Current authenticated user
        limit: Maximum number of messages to return
        db: Database session
        
    Returns:
        List of messages
        
    Raises:
        HTTPException: If agent not found or user doesn't have access
    """
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        service.validate_thread_scope(agent_id, current_user.id, thread_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    messages = service.get_conversation_history(
        agent_id=agent_id,
        thread_id=thread_id,
        limit=limit
    )
    
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
async def list_threads(
    agent_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List threads for a specific user-agent pair."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    threads = service.list_threads(agent_id=agent_id, user_id=current_user.id)
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
async def create_thread(
    agent_id: int,
    request: CreateThreadRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a thread for a specific user-agent pair."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        thread = service.create_thread(
            agent_id=agent_id,
            user_id=current_user.id,
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


# Memory routes
@router.get("/{agent_id}/memories", response_model=List[MemoryResponse])
async def get_agent_memories(
    agent_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all memories for an agent."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    memory_service = MemoryService(db)
    memories = memory_service.get_all_memories(agent_id)
    
    return [
        MemoryResponse(
            id=memory.id,
            agent_id=memory.agent_id,
            key=memory.key,
            value=memory.value,
            metadata=memory.memory_metadata,
            created_at=memory.created_at.isoformat(),
            updated_at=memory.updated_at.isoformat(),
        )
        for memory in memories
    ]


# Knowledge routes
@router.post("/{agent_id}/knowledge/upload")
async def upload_knowledge_file(
    agent_id: int,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a knowledge file (txt, csv, pdf) for an agent."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate file type
    allowed_extensions = ['.txt', '.csv', '.pdf']
    file_ext = os.path.splitext(file.filename)[0] if file.filename else ''
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create uploads directory structure
    upload_dir = Path("uploads") / str(agent_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename if file already exists
    original_filename = file.filename
    file_path = upload_dir / original_filename
    counter = 1
    while file_path.exists():
        name, ext = os.path.splitext(original_filename)
        file_path = upload_dir / f"{name}_{counter}{ext}"
        counter += 1
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Read and process file content
    try:
        content = ""
        if file_path.suffix == '.txt':
            content = file_path.read_text(encoding='utf-8')
        elif file_path.suffix == '.csv':
            import csv
            with file_path.open('r', encoding='utf-8') as f:
                reader = csv.reader(f)
                content = '\n'.join([','.join(row) for row in reader])
        elif file_path.suffix == '.pdf':
            try:
                from pypdf import PdfReader
                with file_path.open('rb') as f:
                    pdf_reader = PdfReader(f)
                    content = '\n'.join([page.extract_text() for page in pdf_reader.pages])
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PDF support not available. Install pypdf."
                )
        
        # Store in knowledge base
        knowledge_service = KnowledgeService(db)
        chunks = knowledge_service.upload_text(
            text=content,
            agent_id=agent_id,
            source=file_path.name,
            metadata={
                "original_filename": original_filename,
                "file_type": file_path.suffix,
                "agent_id": agent_id
            }
        )
        
        return {
            "message": "File uploaded successfully",
            "filename": file_path.name,
            "chunks_created": len(chunks),
            "agent_id": agent_id
        }
    
    except Exception as e:
        # Clean up file if processing fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.get("/{agent_id}/knowledge/files", response_model=List[KnowledgeFileResponse])
async def list_knowledge_files(
    agent_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all knowledge files for an agent."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get files from uploads directory
    upload_dir = Path("uploads") / str(agent_id)
    if not upload_dir.exists():
        return []
    
    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                KnowledgeFileResponse(
                    filename=file_path.name,
                    size=stat.st_size,
                    created_at=str(stat.st_ctime),
                    agent_id=agent_id
                )
            )
    
    return files


@router.delete("/{agent_id}/knowledge/files/{filename}")
async def delete_knowledge_file(
    agent_id: int,
    filename: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a knowledge file and its associated chunks."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify the agent belongs to the current user
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete file
    file_path = Path("uploads") / str(agent_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        
        # Delete associated knowledge chunks
        knowledge_service = KnowledgeService(db)
        knowledge_service.delete_by_source(agent_id, filename)
        
        return {"message": "File deleted successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
