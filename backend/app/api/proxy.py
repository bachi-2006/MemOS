from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import User
from app.services.ollama_service import ollama_service
from app.services.context_builder import context_builder
from app.services.memory_service import memory_service

router = APIRouter(tags=["Ollama OpenAI Proxy Compatibility"])

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: Optional[str] = "qwen3.5:9b"
    messages: List[OpenAIChatMessage]
    stream: Optional[bool] = False

@router.post("/v1/chat/completions")
@router.post("/api/chat")
async def ollama_proxy_chat(request: OpenAIChatRequest, db: Session = Depends(get_db)):
    """
    OpenAI / Ollama proxy compatibility layer.
    Allows Ollama Desktop, Open WebUI, or any third-party app pointing to MemOS
    to automatically inject vector memory context before sending to Ollama!
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list empty")

    user_query = request.messages[-1].content
    
    # Retrieve default or first user in db for local proxy memory attachment
    user = db.query(User).first()
    user_id = user.id if user else "default_local_user"

    # Build context from Qdrant vector memories
    augmented_context = await context_builder.build_augmented_context(
        db=db,
        user_id=user_id,
        user_prompt=user_query,
        top_k=5
    )

    full_prompt = user_query
    if augmented_context:
        full_prompt = f"{augmented_context}\n\nUser Question: {user_query}"

    # Query Ollama
    response_text = await ollama_service.generate_chat(
        prompt=full_prompt,
        model=request.model
    )

    # Automatically persist this conversation as new memory
    if user:
        await memory_service.create_and_index_memory(
            db=db,
            user_id=user.id,
            content=f"User asked: {user_query} | AI answered: {response_text[:200]}",
            source="ollama_desktop"
        )

    # Return standard OpenAI response format
    return {
        "id": "chatcmpl-memos",
        "object": "chat.completion",
        "created": 123456789,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ]
    }
