from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Chat, Message, User
from app.schemas.schemas import ChatRequest
from app.api.deps import get_current_user_optional
from app.services.ollama_service import ollama_service
from app.services.context_builder import context_builder

router = APIRouter(prefix="/chats", tags=["Chat Storage & History"])

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

    return {
        "chat_id": chat.id,
        "user_message": {"id": user_msg.id, "role": "user", "content": user_msg.content},
        "assistant_message": {"id": assistant_msg.id, "role": "assistant", "content": assistant_msg.content},
        "personalized": request.personalized,
        "explanation": context_meta
    }
