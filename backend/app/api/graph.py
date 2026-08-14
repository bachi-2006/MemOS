from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.models import User
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

@router.get("/")
def get_knowledge_graph(current_user: User = Depends(get_current_user)):
    """Retrieve Neo4j entity-relationship graph for active user (Phase 8)"""
    try:
        data = graph_service.get_user_graph(user_id=current_user.id)
        return data
    except Exception as e:
        return {"nodes": [], "edges": [], "notice": f"Neo4j connection info: {str(e)}"}
