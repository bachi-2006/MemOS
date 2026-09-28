import re
from typing import Dict, Any, List, Set, Tuple, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_optional
from app.database.session import get_db
from app.models.models import User, MemoryModel
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

SYSTEM_TAGS_TO_IGNORE = {
    "summary", "fact", "decision", "preference", "goal",
    "saved_from_chat", "user_fact", "conflict_flagged",
    "conflict_resolved", "general", "manual", "mute_recall"
}

IGNORE_PHRASES = {
    "conversation analysis completed.",
    "chat conversation analyzed.",
    "conversation contained general pleasantries or greetings.",
    "hello.",
    "ready to assist with memos."
}

KNOWN_ENTITIES = {
    "sqlite": ("SQLite", "technology"),
    "qdrant": ("Qdrant", "technology"),
    "fastapi": ("FastAPI", "technology"),
    "neo4j": ("Neo4j", "technology"),
    "redis": ("Redis", "technology"),
    "postgresql": ("PostgreSQL", "technology"),
    "postgres": ("PostgreSQL", "technology"),
    "python": ("Python", "skill"),
    "typescript": ("TypeScript", "skill"),
    "javascript": ("JavaScript", "skill"),
    "next.js": ("Next.js", "technology"),
    "nextjs": ("Next.js", "technology"),
    "react": ("React", "technology"),
    "vue": ("Vue", "technology"),
    "angular": ("Angular", "technology"),
    "docker": ("Docker", "technology"),
    "ollama": ("Ollama", "technology"),
    "kubernetes": ("Kubernetes", "technology"),
    "clickhouse": ("ClickHouse", "technology"),
    "mongodb": ("MongoDB", "technology"),
    "graphql": ("GraphQL", "technology"),
    "india": ("India", "concept"),
    "new delhi": ("New Delhi", "concept"),
    "quantum electrodynamics": ("Quantum Electrodynamics", "concept"),
    "manhattan project": ("Manhattan Project", "project"),
    "los alamos national laboratory": ("Los Alamos National Laboratory", "concept"),
    "los alamos": ("Los Alamos", "concept"),
    "theoretical physics": ("Theoretical Physics", "skill"),
    "theoretical physicist": ("Theoretical Physics", "skill"),
    "christopher nolan": ("Christopher Nolan", "person"),
    "trinity test": ("Trinity Test", "concept"),
    "memos": ("MemOS", "project")
}

SENTENCE_STARTERS = {
    "the", "a", "an", "this", "that", "these", "those", "there", "it",
    "we", "they", "he", "she", "you", "i", "if", "when", "as", "in",
    "on", "at", "for", "with", "by", "from", "after", "before", "during",
    "while", "please", "hello", "hi", "hey", "yes", "no", "subject"
}


def _clean_token(text: str) -> str:
    """Strip markdown, quotes, parentheticals, and punctuation."""
    text = re.sub(r'[\*\`\_\"\']', '', text)
    text = re.sub(r'\s*\(.*?\)', '', text)
    text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
    return text.strip()


def extract_knowledge_from_memory(
    content: str,
    tags: Optional[List[str]] = None,
    project: Optional[str] = None
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str, str]]]:
    """
    Extract high-precision entity nodes and semantic directional edges
    directly from an individual saved memory record.
    """
    clean = content.strip()
    if clean.lower() in IGNORE_PHRASES or len(clean) < 4:
        return [], []

    nodes: Dict[str, Dict[str, str]] = {}
    edges: Set[Tuple[str, str, str]] = set()
    clean_lower = clean.lower()

    # 1. Project association
    active_project = project or ("MemOS" if "memos" in clean_lower else None)
    if active_project:
        nodes[active_project] = {"id": active_project, "label": active_project, "type": "project"}
        edges.add(("User", active_project, "BUILDS"))

    # 2. Subject extraction: e.g. "Subject: J. Robert Oppenheimer (1904-1967)"
    sub_match = re.search(r"Subject:\s*([^\n\(\*]+)", clean, re.IGNORECASE)
    subject = None
    if sub_match:
        raw_sub = _clean_token(sub_match.group(1))
        if len(raw_sub) > 2:
            subject = raw_sub.title()
            is_person = any(w in raw_sub.lower() for w in [
                "oppenheimer", "einstein", "turing", "feynman", "curie", "newton", "lovelace"
            ])
            nodes[subject] = {"id": subject, "label": subject, "type": "person" if is_person else "concept"}
            edges.add(("User", subject, "RESEARCHES"))

    # 3. Markdown Key-Value Bullet points: e.g. "* **Field:** Theoretical physicist."
    bullets = re.findall(r"\*\s*\*\*([^*:]+):\*\*\s*([^\n]+)", clean)
    for k, v in bullets:
        k_clean = k.strip().upper().replace(" ", "_")
        # Ignore long narrative/commentary fields as graph entities
        if k_clean in ["QUOTE", "NOTE", "DESCRIPTION", "SUMMARY", "BACKGROUND", "SYSTEMS_&_ARCHITECTURE_RELEVANCE", "CULTURAL_CONTEXT"]:
            continue

        v_clean = _clean_token(v)
        parts = [_clean_token(p) for p in re.split(r"[;,]", v_clean) if len(_clean_token(p)) > 2]
        for p in parts[:3]:
            # Skip compounds containing operators or overly verbose phrases
            if "+" in p or "&" in p or len(p.split()) > 4:
                continue
            p = re.sub(r"^(the|a|an)\s+", "", p, flags=re.IGNORECASE).strip()
            if 3 <= len(p) <= 32 and not p.lower().startswith("http") and not p.isdigit():
                p_label = p.title()
                ntype = "concept"
                if any(w in p_label.lower() for w in ["physics", "engineering", "science", "math", "developer", "architect"]):
                    ntype = "skill"
                nodes[p_label] = {"id": p_label, "label": p_label, "type": ntype}
                if subject:
                    edges.add((subject, p_label, k_clean if k_clean in ["FIELD", "KEY_CONTRIBUTION"] else "RELATES_TO"))
                else:
                    edges.add(("User", p_label, "KNOWS"))

    # 4. Known technologies, tools, and prominent entities scan
    for tech_key, (tech_label, tech_type) in KNOWN_ENTITIES.items():
        pattern = r"\b" + re.escape(tech_key) + r"\b"
        if re.search(pattern, clean_lower):
            nodes[tech_label] = {"id": tech_label, "label": tech_label, "type": tech_type}
            if subject and subject != tech_label:
                edges.add((subject, tech_label, "RELATES_TO"))
            elif active_project and tech_label != active_project:
                edges.add((active_project, tech_label, "USES"))
            else:
                edges.add(("User", tech_label, "SAVED_INTEREST"))

    # 5. Multi-word capitalized named entities (e.g. "Sarah Connor", "Cyberdyne Systems")
    multi_cap = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", clean)
    for ent in multi_cap:
        ent_clean = _clean_token(ent)
        if len(ent_clean) > 3 and ent_clean.lower() not in SENTENCE_STARTERS:
            if ent_clean not in nodes and (not subject or ent_clean != subject):
                nodes[ent_clean] = {"id": ent_clean, "label": ent_clean, "type": "concept"}
                if subject:
                    edges.add((subject, ent_clean, "RELATES_TO"))
                else:
                    edges.add(("User", ent_clean, "KNOWS"))

    # 6. Short query / fact memories (e.g. "capital of india")
    words = clean.split()
    if len(words) <= 6 and not bullets and not subject:
        topic_label = _clean_token(clean).title()
        if len(topic_label) > 2 and topic_label.lower() not in IGNORE_PHRASES:
            nodes[topic_label] = {"id": topic_label, "label": topic_label, "type": "concept"}
            edges.add(("User", topic_label, "FACT"))
            if "india" in clean_lower and topic_label != "India":
                nodes["India"] = {"id": "India", "label": "India", "type": "concept"}
                edges.add((topic_label, "India", "LOCATED_IN"))

    # 7. Extract meaningful tags
    if tags:
        for t in tags:
            clean_t = str(t).strip().lower()
            if clean_t and clean_t not in SYSTEM_TAGS_TO_IGNORE and clean_t not in {"memos", "memos core"}:
                t_label = clean_t.title()
                nodes[t_label] = {"id": t_label, "label": t_label, "type": "concept"}
                if active_project:
                    edges.add((active_project, t_label, "TAG"))
                else:
                    edges.add(("User", t_label, "INTERESTED_IN"))

    return list(nodes.values()), list(edges)


@router.get("/")
def get_knowledge_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Retrieve entity-relationship knowledge graph for the active user.
    The graph is purely generated from the user's saved persistent memories
    and extracted knowledge triples.
    """
    user_id = current_user.id
    user_label = current_user.username or "You"

    nodes_dict: Dict[str, Dict[str, str]] = {}
    edges_set: Set[Tuple[str, str, str]] = set()

    # 1. Ingest entities & facts from durable Graph Store (Neo4j / _local_facts)
    try:
        store_graph = graph_service.get_user_graph(user_id=user_id)
        if store_graph:
            for node in store_graph.get("nodes", []):
                nid = str(node.get("id", "")).strip()
                nlabel = str(node.get("label", nid)).strip()
                ntype = str(node.get("type", "concept")).lower()
                if nid and nid.lower() not in {"memos core"}:
                    nodes_dict[nid] = {"id": nid, "label": nlabel, "type": ntype}

            for edge in store_graph.get("edges", []):
                src = str(edge.get("source", "")).strip()
                tgt = str(edge.get("target", "")).strip()
                rel = str(edge.get("relationship", "RELATES_TO")).strip().upper()
                if src and tgt and src.lower() not in {"memos core"} and tgt.lower() not in {"memos core"}:
                    if src not in nodes_dict:
                        nodes_dict[src] = {"id": src, "label": src, "type": "concept"}
                    if tgt not in nodes_dict:
                        nodes_dict[tgt] = {"id": tgt, "label": tgt, "type": "concept"}
                    edges_set.add((src, tgt, rel))
    except Exception as e:
        print(f"[KnowledgeGraph] Graph store ingestion notice: {e}")

    # 2. Ingest entities strictly from the user's saved memories
    memories = (
        db.query(MemoryModel)
        .filter(MemoryModel.user_id == user_id, MemoryModel.status == "active")
        .order_by(MemoryModel.created_at.desc())
        .limit(100)
        .all()
    )

    seen_memory_texts: Set[str] = set()
    needs_db_commit = False

    for mem in memories:
        content_key = (mem.content or "").strip().lower()
        if not content_key or content_key in seen_memory_texts or content_key in IGNORE_PHRASES:
            continue
        seen_memory_texts.add(content_key)

        # Check if structured entities and relationships are already cached on the memory row
        if (
            mem.entities and isinstance(mem.entities, list) and len(mem.entities) > 0
            and mem.relationships and isinstance(mem.relationships, list) and len(mem.relationships) > 0
        ):
            for ent in mem.entities:
                if isinstance(ent, dict):
                    name = str(ent.get("name", "")).strip()
                    etype = str(ent.get("type", "concept")).lower()
                    if name and name.lower() not in {"memos core"}:
                        nodes_dict[name] = {"id": name, "label": name, "type": etype}
            for rel in mem.relationships:
                if isinstance(rel, dict):
                    src = str(rel.get("source", "")).strip()
                    tgt = str(rel.get("target", "")).strip()
                    r_type = str(rel.get("relationship", "RELATES_TO")).strip().upper()
                    if src and tgt and src != tgt:
                        edges_set.add((src, tgt, r_type))
        else:
            extracted_nodes, extracted_edges = extract_knowledge_from_memory(
                content=mem.content,
                tags=mem.tags or [],
                project=mem.project
            )
            for n in extracted_nodes:
                nid = n["id"]
                if nid not in nodes_dict:
                    nodes_dict[nid] = n
            for e in extracted_edges:
                edges_set.add(e)

            # Persist both entities and relationships on the memory row
            if extracted_nodes:
                mem.entities = [
                    {"name": n["label"], "type": n["type"]} for n in extracted_nodes
                ]
                mem.relationships = [
                    {"source": s, "target": t, "relationship": r} for s, t, r in extracted_edges
                ]
                needs_db_commit = True

    if needs_db_commit:
        try:
            db.commit()
        except Exception as ex:
            db.rollback()
            print(f"[KnowledgeGraph] Memory entity cache notice: {ex}")

    # 3. If any edge references "User", ensure "User" node exists
    has_user_edge = any(src == "User" or tgt == "User" for src, tgt, _ in edges_set)
    if has_user_edge or (nodes_dict and "User" not in nodes_dict):
        nodes_dict["User"] = {"id": "User", "label": user_label, "type": "user"}

    # If there are no saved memory nodes, return a clean empty state
    if not nodes_dict or (len(nodes_dict) == 1 and "User" in nodes_dict):
        return {
            "nodes": [],
            "edges": [],
            "mode": "memory_knowledge_graph",
            "message": "No memory entities or relationships stored yet. Save memories to populate your graph!"
        }

    formatted_nodes = list(nodes_dict.values())
    formatted_edges = [
        {"source": src, "target": tgt, "relationship": rel}
        for src, tgt, rel in edges_set
        if src in nodes_dict and tgt in nodes_dict and src != tgt
    ]

    return {
        "nodes": formatted_nodes,
        "edges": formatted_edges,
        "mode": "memory_knowledge_graph"
    }


