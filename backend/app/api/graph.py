from typing import Dict, Any, List, Set, Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_optional
from app.database.session import get_db
from app.models.models import User, MemoryModel, UserProfile
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

SYSTEM_TAGS_TO_IGNORE = {
    "summary", "fact", "decision", "preference", "goal",
    "saved_from_chat", "user_fact", "conflict_flagged",
    "conflict_resolved", "general"
}

@router.get("/")
def get_knowledge_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Retrieve entity-relationship knowledge graph for the active user.
    The graph is purely generated from the user's memories, conversation entities,
    and profile traits — NOT internal MemOS architecture components.
    """
    user_id = current_user.id
    user_label = current_user.username or "You"

    nodes_dict: Dict[str, Dict[str, str]] = {}
    edges_set: Set[Tuple[str, str, str]] = set()

    # 1. Ingest entities & facts from Graph Store (Neo4j / _local_facts)
    try:
        store_graph = graph_service.get_user_graph(user_id=user_id)
        if store_graph:
            for node in store_graph.get("nodes", []):
                nid = str(node.get("id", "")).strip()
                nlabel = str(node.get("label", nid)).strip()
                ntype = str(node.get("type", "concept")).lower()
                if nid and nid.lower() not in {"memos", "memos core"}:
                    nodes_dict[nid] = {"id": nid, "label": nlabel, "type": ntype}

            for edge in store_graph.get("edges", []):
                src = str(edge.get("source", "")).strip()
                tgt = str(edge.get("target", "")).strip()
                rel = str(edge.get("relationship", "RELATES_TO")).strip().upper()
                if (
                    src and tgt
                    and src.lower() not in {"memos", "memos core"}
                    and tgt.lower() not in {"memos", "memos core"}
                ):
                    if src not in nodes_dict:
                        nodes_dict[src] = {"id": src, "label": src, "type": "concept"}
                    if tgt not in nodes_dict:
                        nodes_dict[tgt] = {"id": tgt, "label": tgt, "type": "concept"}
                    edges_set.add((src, tgt, rel))
    except Exception as e:
        print(f"Graph service ingestion notice: {e}")

    # 2. Ingest entities from SQLite active memories
    memories = (
        db.query(MemoryModel)
        .filter(MemoryModel.user_id == user_id, MemoryModel.status == "active")
        .order_by(MemoryModel.created_at.desc())
        .limit(50)
        .all()
    )

    for mem in memories:
        # A. Extracted entities from conversation analysis
        if mem.entities and isinstance(mem.entities, list):
            for ent in mem.entities:
                if isinstance(ent, dict):
                    name = str(ent.get("name", "")).strip()
                    etype = str(ent.get("type", "concept")).lower()
                    related = str(ent.get("related_to", "")).strip()
                    rel = str(ent.get("relationship", "RELATES_TO")).strip().upper()

                    if name and name.lower() not in {"memos", "memos core"}:
                        if name not in nodes_dict:
                            nodes_dict[name] = {"id": name, "label": name, "type": etype}
                        if related and related.lower() not in {"memos", "memos core"}:
                            if related not in nodes_dict:
                                nodes_dict[related] = {"id": related, "label": related, "type": "concept"}
                            edges_set.add((name, related, rel))

        # B. Project connections
        if mem.project:
            proj_name = str(mem.project).strip()
            if proj_name and proj_name.lower() not in {"memos", "memos core"}:
                if proj_name not in nodes_dict:
                    nodes_dict[proj_name] = {"id": proj_name, "label": proj_name, "type": "project"}
                edges_set.add(("User", proj_name, "PROJECT"))

        # C. Meaningful memory tags
        if mem.tags and isinstance(mem.tags, list):
            for t in mem.tags:
                clean_t = str(t).strip().lower()
                if clean_t and clean_t not in SYSTEM_TAGS_TO_IGNORE and clean_t not in {"memos", "memos core"}:
                    tag_label = clean_t.title()
                    if tag_label not in nodes_dict:
                        nodes_dict[tag_label] = {"id": tag_label, "label": tag_label, "type": "concept"}
                    if mem.project and str(mem.project).strip().lower() not in {"memos", "memos core"}:
                        edges_set.add((str(mem.project).strip(), tag_label, "USES"))
                    else:
                        edges_set.add(("User", tag_label, "INTERESTED_IN"))

    # 3. Ingest user profile traits (languages, frameworks, skills, current projects)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        for lang in (profile.preferred_languages or []):
            lang_str = str(lang).strip()
            if lang_str and lang_str.lower() not in {"memos", "memos core"}:
                if lang_str not in nodes_dict:
                    nodes_dict[lang_str] = {"id": lang_str, "label": lang_str, "type": "skill"}
                edges_set.add(("User", lang_str, "PREFERS_LANG"))

        for fw in (profile.preferred_frameworks or []):
            fw_str = str(fw).strip()
            if fw_str and fw_str.lower() not in {"memos", "memos core"}:
                if fw_str not in nodes_dict:
                    nodes_dict[fw_str] = {"id": fw_str, "label": fw_str, "type": "technology"}
                edges_set.add(("User", fw_str, "USES_FRAMEWORK"))

        for sk in (profile.skills or []):
            sk_str = str(sk).strip()
            if sk_str and sk_str.lower() not in {"memos", "memos core"}:
                if sk_str not in nodes_dict:
                    nodes_dict[sk_str] = {"id": sk_str, "label": sk_str, "type": "skill"}
                edges_set.add(("User", sk_str, "HAS_SKILL"))

        for pr in (profile.current_projects or []):
            pr_str = str(pr).strip()
            if pr_str and pr_str.lower() not in {"memos", "memos core"}:
                if pr_str not in nodes_dict:
                    nodes_dict[pr_str] = {"id": pr_str, "label": pr_str, "type": "project"}
                edges_set.add(("User", pr_str, "BUILDS"))

    # 4. If any edge references "User", ensure "User" node exists
    has_user_edge = any(src == "User" or tgt == "User" for src, tgt, _ in edges_set)
    if has_user_edge:
        nodes_dict["User"] = {"id": "User", "label": user_label, "type": "user"}

    # If there are no memory or profile nodes, return an empty graph
    if not nodes_dict or (len(nodes_dict) == 1 and "User" in nodes_dict):
        return {
            "nodes": [],
            "edges": [],
            "mode": "memory_knowledge_graph",
            "message": "No memory entities or relationships stored yet."
        }

    formatted_nodes = list(nodes_dict.values())
    formatted_edges = [
        {"source": src, "target": tgt, "relationship": rel}
        for src, tgt, rel in edges_set
        if src in nodes_dict and tgt in nodes_dict
    ]

    return {
        "nodes": formatted_nodes,
        "edges": formatted_edges,
        "mode": "memory_knowledge_graph"
    }

