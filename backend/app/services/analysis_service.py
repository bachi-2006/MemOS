import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.models import MemoryModel, Message, UserProfile, AnalysisHistory
from app.services.ollama_service import ollama_service
from app.services.memory_service import memory_service
from app.services.graph_service import graph_service
from app.services.importance_service import importance_engine
from app.services.conflict_service import conflict_engine

class AnalyzeChatEngine:
    async def analyze_chat(
        self,
        db: Session,
        user_id: str,
        chat_id: Optional[str] = None,
        messages_input: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Feature 1: Analyze Chat Engine.
        Parses conversation history, ignores small talk, extracts structured memory metadata,
        deduplicates facts, detects conflicts, updates confidence/importance scores, updates Neo4j knowledge graph,
        indexes embeddings in Qdrant, stores metadata in PostgreSQL, and updates UserProfile.
        """
        # 1. Resolve messages transcript
        raw_messages = []
        if chat_id:
            db_messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
            for m in db_messages:
                raw_messages.append(f"{m.role.capitalize()}: {m.content}")
        elif messages_input:
            for m in messages_input:
                role = m.get("role", "user").capitalize()
                content = m.get("content", "")
                raw_messages.append(f"{role}: {content}")

        if not raw_messages:
            return {
                "summary": "No messages found to analyze.",
                "facts": [],
                "entities": [],
                "projects": [],
                "technologies": [],
                "user_preferences": [],
                "goals": [],
                "skills": [],
                "recurring_topics": [],
                "important_decisions": [],
                "memories_created": [],
                "duplicates_removed": 0,
                "graph_nodes_created": 0,
                "conflicts_detected": []
            }

        transcript = "\n".join(raw_messages)

        # 2. Prompt LLM for structured analysis ignoring greetings and small talk
        analysis_prompt = f"""
You are an expert AI Memory Extraction System. Read the conversation transcript below.

CONVERSATION TRANSCRIPT:
{transcript}

CRITICAL INSTRUCTIONS:
- IGNORE ALL greetings, pleasantries, small talk, and chit-chat (e.g., "hi", "hello", "how are you", "thanks", "bye").
- EXTRACT only meaningful knowledge, facts, user details, projects, technologies, and decisions.
- Output ONLY a valid JSON object matching this exact format (no surrounding commentary):

{{
  "summary": "Concise 1-2 sentence memory summary of the conversation core",
  "facts": ["Extracted Fact 1", "Extracted Fact 2"],
  "entities": [
    {{"name": "EntityName", "type": "Technology", "related_to": "TargetEntity", "relationship": "USES"}}
  ],
  "projects": ["Detected Project Name"],
  "technologies": ["Detected Technology"],
  "user_preferences": ["User Preference"],
  "goals": ["Detected Goal"],
  "skills": ["Detected Skill"],
  "recurring_topics": ["Recurring Topic"],
  "important_decisions": ["Important Decision Made"]
}}
"""

        llm_response = await ollama_service.generate_chat(prompt=analysis_prompt)

        # 3. Parse LLM response JSON safely
        extracted_data = self._parse_json_response(llm_response, transcript)

        summary_text = extracted_data.get("summary", "Conversation analysis completed.")
        facts = extracted_data.get("facts", [])
        entities = extracted_data.get("entities", [])
        projects = extracted_data.get("projects", [])
        technologies = extracted_data.get("technologies", [])
        user_preferences = extracted_data.get("user_preferences", [])
        goals = extracted_data.get("goals", [])
        skills = extracted_data.get("skills", [])
        recurring_topics = extracted_data.get("recurring_topics", [])
        important_decisions = extracted_data.get("important_decisions", [])

        # Primary project tag if detected
        primary_project = projects[0] if projects else None

        # 4. Deduplicate memories & Calculate Importance/Confidence scores & Conflict detection
        existing_memories = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.status == "active"
        ).all()
        existing_contents = {m.content.lower().strip() for m in existing_memories}

        duplicates_count = 0
        conflicts_detected = []

        # Include summary as primary memory item
        all_candidate_items = []
        if summary_text and len(summary_text.strip()) > 10:
            all_candidate_items.append({"content": summary_text, "tags": ["summary"]})

        for fact in facts:
            all_candidate_items.append({"content": fact, "tags": ["fact"]})

        for dec in important_decisions:
            all_candidate_items.append({"content": f"Decision: {dec}", "tags": ["decision"]})

        for pref in user_preferences:
            all_candidate_items.append({"content": f"User Preference: {pref}", "tags": ["preference"]})

        for goal in goals:
            all_candidate_items.append({"content": f"User Goal: {goal}", "tags": ["goal"]})

        created_memory_records = []

        for item in all_candidate_items:
            content_str = item["content"].strip()
            if content_str.lower() in existing_contents:
                duplicates_count += 1
                # Update existing memory confidence & access count
                matching_mem = next((m for m in existing_memories if m.content.lower().strip() == content_str.lower()), None)
                if matching_mem:
                    matching_mem.access_count += 1
                    matching_mem.confidence_score = min(1.0, (matching_mem.confidence_score or 0.8) + 0.05)
                    matching_mem.importance_score = importance_engine.calculate_importance(matching_mem)
                    db.commit()
                continue

            # Run Phase 11 Conflict Detection
            conflict_res = await conflict_engine.detect_and_resolve_conflicts(db, user_id, content_str)
            item_tags = list(item["tags"])
            if conflict_res.get("conflict_detected"):
                item_tags.append("conflict_flagged")
                conflicts_detected.append({
                    "new_memory": content_str,
                    "analysis": conflict_res.get("analysis")
                })

            # Create new canonical memory record in Postgres & Index in Qdrant
            tags = item_tags + (["project:" + primary_project] if primary_project else [])
            memory_rec = await memory_service.create_and_index_memory(
                db=db,
                user_id=user_id,
                content=content_str,
                source="chat_analysis",
                tags=tags,
                importance_score=1.0
            )

            # Update additional fields
            if primary_project:
                memory_rec.project = primary_project
            if "project" in tags or primary_project:
                memory_rec.collection = "Projects"
            elif "preference" in tags or "goal" in tags:
                memory_rec.collection = "Personal"
            elif "tech" in tags or "decision" in tags:
                memory_rec.collection = "Coding"
            
            memory_rec.entities = entities
            db.commit()
            db.refresh(memory_rec)
            existing_contents.add(content_str.lower())

            created_memory_records.append({
                "id": memory_rec.id,
                "content": memory_rec.content,
                "tags": memory_rec.tags,
                "importance_score": memory_rec.importance_score,
                "confidence_score": memory_rec.confidence_score,
                "conflict_flagged": "conflict_flagged" in memory_rec.tags
            })

        # 5. Update Neo4j Knowledge Graph
        graph_nodes_count = 0
        try:
            for ent in entities:
                ent_name = ent.get("name")
                ent_type = ent.get("type", "Concept")
                rel = ent.get("relationship", "DISCUSSES")
                target = ent.get("related_to", "UserContext")
                if ent_name:
                    graph_service.add_fact(
                        user_id=user_id,
                        entity_a=ent_name,
                        label_a=ent_type,
                        predicate=rel,
                        entity_b=target,
                        label_b="Concept"
                    )
                    graph_nodes_count += 1

            for proj in projects:
                graph_service.add_fact(user_id, "User", "User", "WORKING_ON", proj, "Project")
                graph_nodes_count += 1

            for tech in technologies:
                graph_service.add_fact(user_id, "User", "User", "USES", tech, "Technology")
                graph_nodes_count += 1

            for sk in skills:
                graph_service.add_fact(user_id, "User", "User", "HAS_SKILL", sk, "Skill")
                graph_nodes_count += 1

            for pref in user_preferences:
                graph_service.add_fact(user_id, "User", "User", "PREFERS", pref, "Preference")
                graph_nodes_count += 1
        except Exception as e:
            print(f"Neo4j graph update notice: {e}")

        # 6. Continuously Update UserProfile metadata
        self._update_user_profile(
            db=db,
            user_id=user_id,
            projects=projects,
            technologies=technologies,
            skills=skills,
            preferences=user_preferences,
            goals=goals,
            topics=recurring_topics
        )

        # 7. Record in AnalysisHistory
        history = AnalysisHistory(
            user_id=user_id,
            chat_id=chat_id,
            summary=summary_text,
            entities_extracted=entities,
            facts_extracted=facts,
            duplicates_removed=duplicates_count,
            graph_nodes_added=graph_nodes_count,
            vectors_indexed=len(created_memory_records)
        )
        db.add(history)
        db.commit()

        return {
            "summary": summary_text,
            "facts": facts,
            "entities": entities,
            "projects": projects,
            "technologies": technologies,
            "user_preferences": user_preferences,
            "goals": goals,
            "skills": skills,
            "recurring_topics": recurring_topics,
            "important_decisions": important_decisions,
            "memories_created": created_memory_records,
            "duplicates_removed": duplicates_count,
            "graph_nodes_created": graph_nodes_count,
            "conflicts_detected": conflicts_detected
        }

    def _parse_json_response(self, response_text: str, fallback_transcript: str) -> Dict[str, Any]:
        """Safely extracts JSON from LLM output string or generates structured fallback."""
        try:
            # Try direct JSON loads
            return json.loads(response_text)
        except Exception:
            pass

        # Try regex search for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                pass

        # Fallback if LLM output was unparseable text
        return {
            "summary": response_text[:200] if response_text else "Chat conversation analyzed.",
            "facts": [line.strip("- ") for line in response_text.split("\n") if line.strip().startswith("-")][:5],
            "entities": [],
            "projects": [],
            "technologies": [],
            "user_preferences": [],
            "goals": [],
            "skills": [],
            "recurring_topics": [],
            "important_decisions": []
        }

    def _update_user_profile(
        self,
        db: Session,
        user_id: str,
        projects: List[str],
        technologies: List[str],
        skills: List[str],
        preferences: List[str],
        goals: List[str],
        topics: List[str]
    ):
        """Continuously auto-updates UserProfile record in Postgres"""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        def merge_unique(existing: Optional[List[str]], new_items: List[str]) -> List[str]:
            base = list(existing) if existing else []
            for item in new_items:
                if item and item not in base:
                    base.append(item)
            return base

        profile.current_projects = merge_unique(profile.current_projects, projects)
        profile.technologies = merge_unique(profile.technologies, technologies)
        profile.skills = merge_unique(profile.skills, skills)
        profile.interests = merge_unique(profile.interests, preferences)
        profile.learning_goals = merge_unique(profile.learning_goals, goals)
        profile.recent_focus = merge_unique(profile.recent_focus, topics)
        profile.updated_at = datetime.utcnow()

        db.commit()

    async def optimize_memory_store(
        self,
        db: Session,
        user_id: str,
        compression_days: int = 30
    ) -> Dict[str, Any]:
        """
        Phase 10: 🧹 Optimize Memory / 🧠 Analyze Memory Operation.
        Processes the existing memory store:
          1. Recalculates importance scores across all memories.
          2. Runs conflict detection on recent active memories.
          3. Synthesizes and compresses older memories (> 30 days) via LLM.
          4. Runs adaptive forgetting for stale/low-importance archived memories.
          5. Refreshes knowledge graph consistency.
        """
        from app.services.lifecycle_service import lifecycle_engine

        # 1. Update importance scores
        importance_engine.update_all_importance_scores(db, user_id)

        # 2. Query active memories
        active_memories = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.status == "active"
        ).all()
        scanned_count = len(active_memories)

        # 3. Memory Compression
        compressed_count = await lifecycle_engine.compress_old_memories(
            db=db,
            user_id=user_id,
            days_threshold=compression_days
        )

        # 4. Adaptive Forgetting
        forgotten_count = lifecycle_engine.adaptive_forgetting(
            db=db,
            user_id=user_id,
            min_importance_threshold=0.3
        )

        # 5. Check for conflicts among recent memories
        conflicts_flagged = []
        for mem in active_memories[:10]:
            try:
                c_res = await conflict_engine.detect_and_resolve_conflicts(db, user_id, mem.content)
                if c_res.get("conflict_detected"):
                    conflicts_flagged.append({
                        "memory_id": mem.id,
                        "content": mem.content,
                        "analysis": c_res.get("analysis")
                    })
            except Exception:
                pass

        # 6. Record in AnalysisHistory
        history = AnalysisHistory(
            user_id=user_id,
            chat_id=None,
            summary=f"Memory Store Optimization: Scanned {scanned_count} memories, compressed {compressed_count}, forgotten {forgotten_count}.",
            entities_extracted=[],
            facts_extracted=[],
            duplicates_removed=0,
            graph_nodes_added=0,
            vectors_indexed=scanned_count
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "message": "Memory store optimization completed successfully.",
            "memories_scanned": scanned_count,
            "memories_compressed": compressed_count,
            "memories_forgotten": forgotten_count,
            "conflicts_flagged": conflicts_flagged
        }

analysis_service = AnalyzeChatEngine()
