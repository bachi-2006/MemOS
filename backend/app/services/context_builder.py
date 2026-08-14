from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import MemoryModel, UserProfile
from app.services.memory_service import memory_service
from app.services.graph_service import graph_service

class ContextBuilder:
    async def build_augmented_context(
        self,
        db: Session,
        user_id: str,
        user_prompt: str,
        top_k: int = 5,
        active_project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Feature 2 Context Builder Engine:
        Retrieves:
        1. Relevant semantic vector memories (Qdrant)
        2. Related knowledge graph nodes & triples (Neo4j)
        3. User profile (skills, languages, framework preferences, style)
        4. Active projects
        5. Pinned memories
        Combines and builds an optimized personalized prompt context.
        """
        context_parts = []
        retrieved_memories_meta = []
        retrieved_graph_meta = []

        # 1. Retrieve User Profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile:
            profile_lines = []
            if profile.preferred_languages:
                profile_lines.append(f"Preferred Languages: {', '.join(profile.preferred_languages)}")
            if profile.preferred_frameworks:
                profile_lines.append(f"Preferred Frameworks: {', '.join(profile.preferred_frameworks)}")
            if profile.skills:
                profile_lines.append(f"Skills: {', '.join(profile.skills)}")
            if profile.writing_style:
                profile_lines.append(f"Writing Style: {profile.writing_style}")

            if profile_lines:
                context_parts.append("=== USER PROFILE & PREFERENCES ===")
                context_parts.extend(profile_lines)

        # 2. Retrieve Active Projects
        projects = []
        if active_project:
            projects = [active_project]
        elif profile and profile.current_projects:
            projects = profile.current_projects

        if projects:
            context_parts.append("\n=== ACTIVE PROJECTS ===")
            context_parts.append(f"Current Focus Projects: {', '.join(projects)}")

        # 3. Retrieve Pinned Memories
        pinned_query = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.is_pinned == True,
            MemoryModel.status == "active"
        )
        if active_project:
            pinned_query = pinned_query.filter(MemoryModel.project == active_project)
        
        pinned_memories = pinned_query.limit(5).all()
        if pinned_memories:
            context_parts.append("\n=== PINNED MEMORIES ===")
            for p_idx, pm in enumerate(pinned_memories, 1):
                context_parts.append(f"📌 [Pinned #{p_idx}] {pm.content}")
                retrieved_memories_meta.append({
                    "id": pm.id,
                    "content": pm.content,
                    "type": "pinned",
                    "importance_score": pm.importance_score
                })

        # 4. Retrieve Relevant Semantic Vector Memories (Qdrant)
        vector_memories = await memory_service.search_memories(
            db=db,
            user_id=user_id,
            query=user_prompt,
            limit=top_k
        )

        valid_vector_memories = []
        for item in vector_memories:
            payload = item.get("payload", {})
            m_project = payload.get("project")
            if active_project and m_project and m_project != active_project:
                continue # Skip if project focus mode is active and memory is from a different project
            valid_vector_memories.append(item)

        if valid_vector_memories:
            context_parts.append("\n=== RELEVANT LONG-TERM MEMORIES ===")
            for idx, item in enumerate(valid_vector_memories, 1):
                payload = item.get("payload", {})
                content = payload.get("content", "")
                score = item.get("score", 0.0)
                mem_id = item.get("memory_id", str(idx))
                context_parts.append(f"{idx}. {content} (Relevance: {score:.2f})")
                retrieved_memories_meta.append({
                    "id": mem_id,
                    "content": content,
                    "type": "vector",
                    "relevance_score": score
                })

        # 5. Retrieve Related Graph Nodes (Neo4j)
        try:
            graph_data = graph_service.get_user_graph(user_id=user_id)
            edges = graph_data.get("edges", [])
            if edges:
                context_parts.append("\n=== KNOWLEDGE GRAPH CONTEXT ===")
                for edge in edges[:5]:
                    src = edge.get("source")
                    rel = edge.get("relationship")
                    tgt = edge.get("target")
                    context_parts.append(f"Graph Fact: ({src}) -[{rel}]-> ({tgt})")
                    retrieved_graph_meta.append(edge)
        except Exception as e:
            print(f"Neo4j graph context retrieval notice: {e}")

        if not context_parts:
            return {
                "augmented_prompt": user_prompt,
                "context_injected": "",
                "memories_used": [],
                "graph_nodes_used": []
            }

        context_parts.append("\nInstructions: Personalize your response strictly using the user profile, active project details, and relevant memories above.")
        full_context_text = "\n".join(context_parts)
        
        augmented_prompt = f"{full_context_text}\n\nUser Question: {user_prompt}"

        return {
            "augmented_prompt": augmented_prompt,
            "context_injected": full_context_text,
            "memories_used": retrieved_memories_meta,
            "graph_nodes_used": retrieved_graph_meta
        }

context_builder = ContextBuilder()
