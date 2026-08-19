import time
import uuid
import json
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import User, Chat, Message
from app.services.ollama_service import ollama_service
from app.services.context_builder import context_builder
from app.services.memory_service import memory_service
from app.core.config import settings

router = APIRouter(tags=["OpenAI & Ollama Proxy Compatibility"])

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class OpenAIChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

    def get_text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, list):
            texts = []
            for part in self.content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
            return " ".join(texts)
        return str(self.content)

class OpenAIChatRequest(BaseModel):
    model: Optional[str] = "qwen3.5:9b"
    messages: List[OpenAIChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    user: Optional[str] = None
    session_id: Optional[str] = None
    personalized: Optional[bool] = True

# -----------------------------------------------------------------------------
# Local User / Session Helper (Phase 5)
# -----------------------------------------------------------------------------

def resolve_proxy_user(db: Session, requested_user: Optional[str] = None, x_user_id: Optional[str] = None) -> User:
    """
    Safely resolves the local MemOS companion user without hardcoding `db.query(User).first()`.
    Deterministic single-user companion or scoped identifier.
    """
    user_identifier = requested_user or x_user_id or "local_companion_user"
    
    # Try finding by username or ID
    user = db.query(User).filter((User.id == user_identifier) | (User.username == user_identifier) | (User.email == user_identifier)).first()
    if not user:
        # Check if any user exists with companion email
        companion_email = f"{user_identifier}@local.memos" if "@" not in user_identifier else user_identifier
        user = db.query(User).filter(User.email == companion_email).first()
        if not user:
            user = User(
                id=user_identifier if len(user_identifier) > 8 else str(uuid.uuid4()),
                email=companion_email,
                username=user_identifier,
                hashed_password="local_companion_unrestricted_hash"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    return user

async def async_store_chat_and_memory(
    user_id: str,
    session_id: Optional[str],
    user_prompt: str,
    assistant_response: str,
    model: str
):
    """
    Phase 6: Asynchronously persists complete untruncated conversation and indexes memory
    without blocking real-time token streaming.
    """
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        # 1. Resolve or create Chat session
        chat_id = session_id
        chat = None
        if chat_id:
            chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        
        if not chat:
            title = user_prompt[:40] + ("..." if len(user_prompt) > 40 else "")
            chat = Chat(
                id=chat_id or str(uuid.uuid4()),
                user_id=user_id,
                title=title
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)

        # 2. Store full user message
        u_msg = Message(chat_id=chat.id, role="user", content=user_prompt)
        db.add(u_msg)

        # 3. Store full assistant response (NO 200-char truncation!)
        a_msg = Message(chat_id=chat.id, role="assistant", content=assistant_response)
        db.add(a_msg)
        db.commit()

        # 4. Index as external proxy memory note
        if len(user_prompt.strip()) > 5 and len(assistant_response.strip()) > 5:
            await memory_service.create_and_index_memory(
                db=db,
                user_id=user_id,
                content=f"Q: {user_prompt}\nA: {assistant_response}",
                source="ollama_desktop_proxy",
                tags=["desktop_proxy", model]
            )

        # 5. Automatically trigger background chat analysis & graph sync
        try:
            from app.services.analysis_service import analysis_service
            await analysis_service.analyze_chat(db=db, user_id=user_id, chat_id=chat.id)
        except Exception as err:
            print(f"Background proxy analysis notice: {err}")
    except Exception as e:
        print(f"Async chat storage notice: {e}")
    finally:
        db.close()


# -----------------------------------------------------------------------------
# OpenAI Compatible Endpoints (Phase 3 & 4)
# -----------------------------------------------------------------------------

@router.get("/v1/models")
async def openai_list_models():
    """
    Phase 3: Standard OpenAI models endpoint.
    Proxies local Ollama models into OpenAI JSON list format.
    """
    models_raw = await ollama_service.list_models()
    data = []
    current_time = int(time.time())
    
    for m in models_raw:
        model_name = m.get("name", "unknown")
        data.append({
            "id": model_name,
            "object": "model",
            "created": current_time,
            "owned_by": "ollama",
            "permission": [],
            "root": model_name,
            "parent": None
        })

    # Default fallback entry if none discovered yet
    if not data:
        data.append({
            "id": settings.DEFAULT_LLM_MODEL,
            "object": "model",
            "created": current_time,
            "owned_by": "ollama",
            "permission": [],
            "root": settings.DEFAULT_LLM_MODEL,
            "parent": None
        })

    return {
        "object": "list",
        "data": data
    }


@router.post("/v1/chat/completions")
@router.post("/api/chat")
async def openai_chat_completions(
    request: OpenAIChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Phase 3 & 4: Full OpenAI / Ollama Chat Completion Proxy.
    Features:
      - Memory & Graph Context Injection (Personalized ON/OFF)
      - SSE Real-time Token Streaming (`stream=true`)
      - Full message history preservation (system, user, assistant)
      - Safe user resolution (no `db.query(User).first()`)
      - Asynchronous full conversation capture
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list is empty")

    # 1. Resolve User securely
    user = resolve_proxy_user(db, request.user, x_user_id)
    user_id = user.id

    # 2. Extract messages transcript & latest user query
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found in messages list")
    
    latest_user_query = user_messages[-1].get_text_content()

    # Extract system messages if provided
    system_messages = [m.get_text_content() for m in request.messages if m.role == "system"]
    base_system_prompt = "\n\n".join(system_messages) if system_messages else None

    # 3. Memory & Personalization Context Injection (Phase 9)
    injected_system_context = base_system_prompt
    if request.personalized:
        try:
            augmented = await context_builder.build_augmented_context(
                db=db,
                user_id=user_id,
                user_prompt=latest_user_query,
                top_k=5
            )
            context_injected = augmented.get("context_injected", "")
            if context_injected:
                if injected_system_context:
                    injected_system_context = f"{injected_system_context}\n\n{context_injected}"
                else:
                    injected_system_context = context_injected
        except Exception as e:
            print(f"Context builder notice in proxy: {e}")

    # Prepare multi-turn history prompt for Ollama
    conversation_turns = []
    for m in request.messages:
        role_label = m.role.capitalize()
        content_text = m.get_text_content()
        if m.role != "system":
            conversation_turns.append(f"{role_label}: {content_text}")

    full_conversation_prompt = "\n".join(conversation_turns)
    if not full_conversation_prompt.strip():
        full_conversation_prompt = latest_user_query

    # Model options
    options: Dict[str, Any] = {}
    if request.temperature is not None:
        options["temperature"] = request.temperature
    if request.top_p is not None:
        options["top_p"] = request.top_p
    if request.max_tokens is not None:
        options["num_predict"] = request.max_tokens

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())
    selected_model = request.model or settings.DEFAULT_LLM_MODEL

    # -------------------------------------------------------------------------
    # 4. STREAMING MODE (Phase 4 SSE)
    # -------------------------------------------------------------------------
    if request.stream:
        async def event_generator():
            full_response_accumulator = []
            
            # Initial chunk (role: assistant)
            initial_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": selected_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            # Stream tokens from Ollama
            async for token in ollama_service.generate_chat_stream(
                prompt=full_conversation_prompt,
                model=selected_model,
                system_context=injected_system_context,
                options=options if options else None
            ):
                full_response_accumulator.append(token)
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": selected_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": token},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            # Final finish chunk
            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": selected_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

            # Asynchronous background capture of full untruncated conversation
            complete_assistant_text = "".join(full_response_accumulator)
            await async_store_chat_and_memory(
                user_id=user_id,
                session_id=request.session_id,
                user_prompt=latest_user_query,
                assistant_response=complete_assistant_text,
                model=selected_model
            )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Accel-Buffering": "no"
            }
        )

    # -------------------------------------------------------------------------
    # 5. NON-STREAMING MODE
    # -------------------------------------------------------------------------
    response_text = await ollama_service.generate_chat(
        prompt=full_conversation_prompt,
        model=selected_model,
        system_context=injected_system_context,
        options=options if options else None
    )

    # Trigger async background chat & memory capture
    background_tasks.add_task(
        async_store_chat_and_memory,
        user_id=user_id,
        session_id=request.session_id,
        user_prompt=latest_user_query,
        assistant_response=response_text,
        model=selected_model
    )

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": selected_model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(full_conversation_prompt.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(full_conversation_prompt.split()) + len(response_text.split())
        }
    }
