from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.session import get_db, SessionLocal
from app.models.models import Chat, Message, User
from app.schemas.schemas import ChatRequest
from app.api.deps import get_current_user_optional
from app.services.ollama_service import ollama_service
from app.services.context_builder import context_builder
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/chats", tags=["Chat Storage & History"])

async def async_extract_chat_memories(user_id: str, chat_id: str):
    """
    Phase 2: Automated Background Memory Extraction.
    Extracts facts, deduplicates, flags conflicts, and updates Qdrant & Neo4j silently
    after every conversation turn without blocking user chat streaming.
    """
    db = SessionLocal()
    try:
        await analysis_service.analyze_chat(db=db, user_id=user_id, chat_id=chat_id)
    except Exception as e:
        print(f"Background chat analysis error for chat {chat_id}: {e}")
    finally:
        db.close()

@router.get("/")
def get_user_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.updated_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at} for c in chats]

@router.get("/{chat_id}/messages")
def get_chat_messages(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

@router.post("/send")
async def send_chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    # Get or create chat session
    if request.chat_id:
        chat = db.query(Chat).filter(Chat.id == request.chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        # Create a new chat session with prompt prefix as title
        title = request.prompt[:30] + "..." if len(request.prompt) > 30 else request.prompt
        chat = Chat(user_id=current_user.id, title=title)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=request.prompt)
    db.add(user_msg)
    db.commit()

    final_prompt = request.prompt
    context_meta = {}

    if request.personalized:
        context_res = await context_builder.build_augmented_context(
            db=db,
            user_id=current_user.id,
            user_prompt=request.prompt,
            top_k=5,
            active_project=request.active_project
        )
        final_prompt = context_res["augmented_prompt"]
        context_meta = {
            "memories_used": context_res["memories_used"],
            "graph_nodes_used": context_res["graph_nodes_used"],
            "context_injected": context_res["context_injected"]
        }

    # Generate response from Ollama
    assistant_response = await ollama_service.generate_chat(
        prompt=final_prompt,
        model=request.model,
        system_context=request.system_context
    )

    # Save assistant response
    assistant_msg = Message(chat_id=chat.id, role="assistant", content=assistant_response)
    db.add(assistant_msg)
    db.commit()

    # Automatically extract memories, facts, and graph triples in background
    background_tasks.add_task(async_extract_chat_memories, user_id=current_user.id, chat_id=chat.id)

    return {
        "chat_id": chat.id,
        "user_message": {"id": user_msg.id, "role": "user", "content": user_msg.content},
        "assistant_message": {"id": assistant_msg.id, "role": "assistant", "content": assistant_msg.content},
        "personalized": request.personalized,
        "explanation": context_meta
    }

@router.post("/stream")
async def stream_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Phase 4: Real-time token streaming chat endpoint via Server-Sent Events (SSE).
    Builds personalized context, streams tokens dynamically, persists assistant message,
    and automatically triggers background memory extraction upon stream completion.
    """
    # Get or create chat session
    if request.chat_id:
        chat = db.query(Chat).filter(Chat.id == request.chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        title = request.prompt[:30] + "..." if len(request.prompt) > 30 else request.prompt
        chat = Chat(user_id=current_user.id, title=title)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=request.prompt)
    db.add(user_msg)
    db.commit()

    final_prompt = request.prompt
    context_meta = {}

    if request.personalized:
        context_res = await context_builder.build_augmented_context(
            db=db,
            user_id=current_user.id,
            user_prompt=request.prompt,
            top_k=5,
            active_project=request.active_project
        )
        final_prompt = context_res["augmented_prompt"]
        context_meta = {
            "memories_used": context_res["memories_used"],
            "graph_nodes_used": context_res["graph_nodes_used"],
            "context_injected": context_res["context_injected"]
        }

    chat_id_val = chat.id
    user_id_val = current_user.id

    async def sse_generator():
        import json
        import asyncio
        full_response = []
        try:
            async for token in ollama_service.generate_chat_stream(
                prompt=final_prompt,
                model=request.model,
                system_context=request.system_context
            ):
                full_response.append(token)
                payload = json.dumps({"token": token, "done": False, "chat_id": chat_id_val})
                yield f"data: {payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"token": f" [Error: {str(e)}]", "done": False, "chat_id": chat_id_val})
            yield f"data: {err_payload}\n\n"

        # Persist full assistant message to DB
        complete_text = "".join(full_response)
        try:
            assistant_msg = Message(chat_id=chat_id_val, role="assistant", content=complete_text or "No response generated.")
            db.add(assistant_msg)
            db.commit()

            # Schedule automated background memory extraction without delaying the stream
            asyncio.create_task(async_extract_chat_memories(user_id=user_id_val, chat_id=chat_id_val))
        except Exception as err:
            print(f"Error saving stream message to DB: {err}")

        final_payload = json.dumps({
            "token": "",
            "done": True,
            "chat_id": chat_id_val,
            "personalized": request.personalized,
            "explanation": context_meta
        })
        yield f"data: {final_payload}\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
