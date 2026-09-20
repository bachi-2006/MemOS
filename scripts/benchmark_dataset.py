#!/usr/bin/env python3
"""
MemOS Ground-Truth Benchmark Dataset
====================================
A curated research dataset of 60+ scenarios used to evaluate retrieval,
personalization, deduplication, and conflict detection across three systems:
  Raw Ollama | Naive Vector RAG | MemOS Multi-Store

Each scenario encodes:
  - id, category, query (the question a user asks)
  - ground_truth (strings the retrieved context must contain to count as a hit)
  - expected_in_context (personalized facts the answer should draw on)
  - is_duplicate / is_conflict flags for lifecycle evaluation
  - irrelevant (flag for the "irrelevant information" negative class)
"""

BENCHMARK_SCENARIOS = [
    # =========================================================================
    # CATEGORY: Facts (29)
    # =========================================================================
    {"id": "fact_01", "category": "Facts", "query": "What language do I primarily use for backend development?", "ground_truth": ["Python"], "expected_in_context": ["Python", "backend"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_02", "category": "Facts", "query": "What framework is my backend built with?", "ground_truth": ["FastAPI"], "expected_in_context": ["FastAPI"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_03", "category": "Facts", "query": "Which database stores my vector embeddings?", "ground_truth": ["Qdrant"], "expected_in_context": ["Qdrant", "vector"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_04", "category": "Facts", "query": "Which database stores my knowledge relationships?", "ground_truth": ["Neo4j"], "expected_in_context": ["Neo4j", "graph"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_05", "category": "Facts", "query": "What is my current project called?", "ground_truth": ["MemOS"], "expected_in_context": ["MemOS"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_06", "category": "Facts", "query": "What frontend framework do I use?", "ground_truth": ["Next.js"], "expected_in_context": ["Next.js", "React"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_07", "category": "Facts", "query": "What local LLM runtime do I use?", "ground_truth": ["Ollama"], "expected_in_context": ["Ollama", "11434"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_08", "category": "Facts", "query": "What embedding model do I use for vector indexing?", "ground_truth": ["nomic-embed-text"], "expected_in_context": ["nomic-embed-text"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_09", "category": "Facts", "query": "What caching layer do I use for sessions?", "ground_truth": ["Redis"], "expected_in_context": ["Redis", "cache"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_10", "category": "Facts", "query": "What scheduler runs my nightly memory tasks?", "ground_truth": ["APScheduler"], "expected_in_context": ["APScheduler", "nightly"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_11", "category": "Facts", "query": "Which ORM do I use to talk to my relational database?", "ground_truth": ["SQLAlchemy"], "expected_in_context": ["SQLAlchemy"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_12", "category": "Facts", "query": "What is my proxy port for the OpenAI-compatible bridge?", "ground_truth": ["11435"], "expected_in_context": ["11435", "proxy"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_13", "category": "Facts", "query": "What default LLM do I prefer for chat?", "ground_truth": [""], "expected_in_context": ["model"], "is_duplicate": False, "is_conflict": False, "note": "Default model is user-configurable"},
    {"id": "fact_14", "category": "Facts", "query": "What API framework does my backend expose?", "ground_truth": ["FastAPI", "REST", "SSE"], "expected_in_context": ["FastAPI", "SSE"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_15", "category": "Facts", "query": "What port does my backend server run on?", "ground_truth": ["8000"], "expected_in_context": ["8000"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_16", "category": "Facts", "query": "What collection do I use to store embeddings?", "ground_truth": ["memos_vectors"], "expected_in_context": ["memos_vectors"], "is_duplicate": False, "is_conflict": False, "note": "Qdrant collection name"},
    {"id": "fact_17", "category": "Facts", "query": "What is my knowledge graph query language?", "ground_truth": ["Cypher"], "expected_in_context": ["Cypher", "Neo4j"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_18", "category": "Facts", "query": "Which HTTP client library does my backend use for Ollama?", "ground_truth": ["httpx"], "expected_in_context": ["httpx"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_19", "category": "Facts", "query": "How do I hash user passwords?", "ground_truth": ["bcrypt"], "expected_in_context": ["bcrypt", "password"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_20", "category": "Facts", "query": "How do I sign JWT tokens?", "ground_truth": ["HS256"], "expected_in_context": ["HS256", "JWT"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_21", "category": "Facts", "query": "What status do memories get when they age past 30 days?", "ground_truth": ["archived"], "expected_in_context": ["archived", "30", "days"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_22", "category": "Facts", "query": "What status do low-value archived memories get?", "ground_truth": ["forgotten"], "expected_in_context": ["forgotten", "0.3", "importance"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_23", "category": "Facts", "query": "What is the pin bonus in importance scoring?", "ground_truth": ["2.0"], "expected_in_context": ["2.0", "pinned"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_24", "category": "Facts", "query": "What is the daily recency decay factor?", "ground_truth": ["0.05"], "expected_in_context": ["0.05", "per day"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_25", "category": "Facts", "query": "How often does the scheduler run memory compression?", "ground_truth": ["nightly", "midnight"], "expected_in_context": ["midnight", "cron"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_26", "category": "Facts", "query": "What user query does the default local companion user use?", "ground_truth": ["local"], "expected_in_context": ["local@memos.ai"], "is_duplicate": False, "is_conflict": False, "note": "Demonstrates single-tenant fallback"},
    {"id": "fact_27", "category": "Facts", "query": "What is my memory compression source tag?", "ground_truth": ["lifecycle_compression"], "expected_in_context": ["compressed_archive"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_28", "category": "Facts", "query": "Where do I store my canonical memory metadata?", "ground_truth": ["PostgreSQL"], "expected_in_context": ["PostgreSQL", "metadata"], "is_duplicate": False, "is_conflict": False},
    {"id": "fact_29", "category": "Facts", "query": "What is my memory source type when shared from an Ollama desktop hook?", "ground_truth": ["ollama_app_hook"], "expected_in_context": ["ollama_app_hook"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Preferences (8)
    # =========================================================================
    {"id": "pref_01", "category": "Preferences", "query": "Do I prefer local or cloud execution for my AI tools?", "ground_truth": ["local", "privacy"], "expected_in_context": ["100% on-device", "privacy"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_02", "category": "Preferences", "query": "What writing style do I expect in code explanations?", "ground_truth": ["concise", "technical", "direct"], "expected_in_context": ["Concise"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_03", "category": "Preferences", "query": "Do I prefer to keep my data on-device?", "ground_truth": ["yes", "on-device"], "expected_in_context": ["on-device", "privacy"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_04", "category": "Preferences", "query": "Which frontend framework do I prefer?", "ground_truth": ["Next.js", "React"], "expected_in_context": ["Next.js"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_05", "category": "Preferences", "query": "What database do I prefer for vector search?", "ground_truth": ["Qdrant"], "expected_in_context": ["Qdrant"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_06", "category": "Preferences", "query": "Do I have any cloud API dependencies?", "ground_truth": ["none", "no"], "expected_in_context": ["no cloud"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_07", "category": "Preferences", "query": "What programming languages do I prefer?", "ground_truth": ["Python", "TypeScript"], "expected_in_context": ["Python"], "is_duplicate": False, "is_conflict": False},
    {"id": "pref_08", "category": "Preferences", "query": "What UI library does my frontend use?", "ground_truth": ["Tailwind", "Lucide"], "expected_in_context": ["Tailwind"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Projects (4)
    # =========================================================================
    {"id": "proj_01", "category": "Projects", "query": "What is my main project this term?", "ground_truth": ["MemOS"], "expected_in_context": ["MemOS"], "is_duplicate": False, "is_conflict": False},
    {"id": "proj_02", "category": "Projects", "query": "What is the goal of MemOS?", "ground_truth": ["persistent memory", "local LLM"], "expected_in_context": ["persistent memory"], "is_duplicate": False, "is_conflict": False},
    {"id": "proj_03", "category": "Projects", "query": "What stack does MemOS use?", "ground_truth": ["FastAPI", "Next.js", "PostgreSQL", "Qdrant", "Neo4j", "Ollama"], "expected_in_context": ["FastAPI", "Qdrant", "Neo4j"], "is_duplicate": False, "is_conflict": False},
    {"id": "proj_04", "category": "Projects", "query": "Is there a companion app for MemOS?", "ground_truth": ["desktop", "bridge", "proxy"], "expected_in_context": ["proxy"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Skills (5)
    # =========================================================================
    {"id": "skill_01", "category": "Skills", "query": "What are my strongest engineering skills?", "ground_truth": ["full stack", "Python"], "expected_in_context": ["Full Stack"], "is_duplicate": False, "is_conflict": False},
    {"id": "skill_02", "category": "Skills", "query": "Am I skilled in AI systems architecture?", "ground_truth": ["AI", "architecture"], "expected_in_context": ["AI Systems"], "is_duplicate": False, "is_conflict": False},
    {"id": "skill_03", "category": "Skills", "query": "Do I have backend development skills?", "ground_truth": ["FastAPI", "Python"], "expected_in_context": ["FastAPI"], "is_duplicate": False, "is_conflict": False},
    {"id": "skill_04", "category": "Skills", "query": "Do I know graph databases?", "ground_truth": ["Neo4j"], "expected_in_context": ["Neo4j"], "is_duplicate": False, "is_conflict": False},
    {"id": "skill_05", "category": "Skills", "query": "Do I have frontend development experience?", "ground_truth": ["Next.js", "React", "TypeScript"], "expected_in_context": ["Next.js"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Goals (4)
    # =========================================================================
    {"id": "goal_01", "category": "Goals", "query": "What is my learning goal?", "ground_truth": ["autonomous", "agent OS"], "expected_in_context": ["fully autonomous", "agent OS"], "is_duplicate": False, "is_conflict": False},
    {"id": "goal_02", "category": "Goals", "query": "What am I trying to build long-term?", "ground_truth": ["local agent OS"], "expected_in_context": ["autonomous local agent OS"], "is_duplicate": False, "is_conflict": False},
    {"id": "goal_03", "category": "Goals", "query": "Am I working toward full data privacy?", "ground_truth": ["yes"], "expected_in_context": ["on-device", "privacy"], "is_duplicate": False, "is_conflict": False},
    {"id": "goal_04", "category": "Goals", "query": "What is my research contribution?", "ground_truth": ["persistent memory", "lifecycle"], "expected_in_context": ["persistent memory", "lifecycle"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Temporal Information (6)
    # =========================================================================
    {"id": "temp_01", "category": "Temporal Information", "query": "How long ago did I first set up MemOS?", "ground_truth": ["weeks", "month"], "expected_in_context": ["started", "during"], "is_duplicate": False, "is_conflict": False, "note": "Recency-relative"},
    {"id": "temp_02", "category": "Temporal Information", "query": "How often do I run memory optimization?", "ground_truth": ["nightly", "daily"], "expected_in_context": ["nightly", "scheduler"], "is_duplicate": False, "is_conflict": False},
    {"id": "temp_03", "category": "Temporal Information", "query": "When do I run lifecycle compression jobs?", "ground_truth": ["midnight", "00:00"], "expected_in_context": ["midnight", "cron"], "is_duplicate": False, "is_conflict": False},
    {"id": "temp_04", "category": "Temporal Information", "query": "When are memories considered stale?", "ground_truth": ["30 days", "older than"], "expected_in_context": ["30", "days"], "is_duplicate": False, "is_conflict": False},
    {"id": "temp_05", "category": "Temporal Information", "query": "How often does the frontend poll Ollama status?", "ground_truth": ["10 seconds", "10s"], "expected_in_context": ["10"], "is_duplicate": False, "is_conflict": False},
    {"id": "temp_06", "category": "Temporal Information", "query": "How long is my JWT session valid?", "ground_truth": ["7 days", "week"], "expected_in_context": ["7", "days"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Multi-Hop Reasoning (8)
    # =========================================================================
    {"id": "hop_01", "category": "Multi-Hop Reasoning", "query": "Which query language does the database that stores my relationships use?", "ground_truth": ["Cypher", "Neo4j"], "expected_in_context": ["Cypher"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_02", "category": "Multi-Hop Reasoning", "query": "What service schedules the worker that triggers compression?", "ground_truth": ["APScheduler", "LifecycleEngine"], "expected_in_context": ["APScheduler"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_03", "category": "Multi-Hop Reasoning", "query": "Which service generates the embedding that goes into Qdrant?", "ground_truth": ["Ollama", "nomic"], "expected_in_context": ["Ollama"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_04", "category": "Multi-Hop Reasoning", "query": "Which component builds personalized context from my profile?", "ground_truth": ["ContextBuilder", "context"], "expected_in_context": ["ContextBuilder"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_05", "category": "Multi-Hop Reasoning", "query": "What protects my chat sessions from cross-user access?", "ground_truth": ["JWT", "token", "user_id"], "expected_in_context": ["JWT"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_06", "category": "Multi-Hop Reasoning", "query": "What does the bridge proxy expose OpenAI endpoints to?", "ground_truth": ["Ollama"], "expected_in_context": ["Ollama", "OpenAI"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_07", "category": "Multi-Hop Reasoning", "query": "What is the relationship between MemOS and these three databases?", "ground_truth": ["PostgreSQL", "Qdrant", "Neo4j"], "expected_in_context": ["PostgreSQL", "Qdrant", "Neo4j"], "is_duplicate": False, "is_conflict": False},
    {"id": "hop_08", "category": "Multi-Hop Reasoning", "query": "Which system inserts facts into my knowledge graph?", "ground_truth": ["AnalysisEngine", "graph_service"], "expected_in_context": ["graph", "analyze"], "is_duplicate": False, "is_conflict": False},

    # =========================================================================
    # CATEGORY: Duplicates (6) - semantic near-duplicates
    # =========================================================================
    {"id": "dup_01", "category": "Duplicates", "query": "I use Python for backend engineering.", "existing_memories": ["User prefers Python for backend development."], "is_duplicate": True, "ground_truth": ["duplicate"]},
    {"id": "dup_02", "category": "Duplicates", "query": "We use PostgreSQL 15 for relational storage.", "existing_memories": ["MemOS stores relational metadata in PostgreSQL 15."], "is_duplicate": True, "ground_truth": ["duplicate"]},
    {"id": "dup_03", "category": "Duplicates", "query": "I primarily use Python.", "existing_memories": ["My primary language is Python."], "is_duplicate": True, "ground_truth": ["duplicate"]},
    {"id": "dup_04", "category": "Duplicates", "query": "FastAPI is my backend framework.", "existing_memories": ["I build my backend with FastAPI."], "is_duplicate": True, "ground_truth": ["duplicate"]},
    {"id": "dup_05", "category": "Duplicates", "query": "I store vectors in Qdrant.", "existing_memories": ["Qdrant is my vector store."], "is_duplicate": True, "ground_truth": ["duplicate"]},
    {"id": "dup_06", "category": "Duplicates", "query": "I run local models through Ollama.", "existing_memories": ["Ollama handles my local inference."], "is_duplicate": True, "ground_truth": ["duplicate"]},

    # =========================================================================
    # CATEGORY: Conflicts (6) - contradictions
    # =========================================================================
    {"id": "conf_01", "category": "Conflicts", "query": "I have completely migrated all my backend code from Python to Go.", "existing_memories": ["User's primary backend language is Python with FastAPI."], "is_conflict": True, "ground_truth": ["conflict"]},
    {"id": "conf_02", "category": "Conflicts", "query": "We decided to host all vector data in Pinecone cloud instead of local Qdrant.", "existing_memories": ["User strictly prefers 100% on-device local execution with Qdrant. No cloud API dependencies."], "is_conflict": True, "ground_truth": ["conflict"]},
    {"id": "conf_03", "category": "Conflicts", "query": "I switched my frontend to Vue.js.", "existing_memories": ["User's frontend framework is Next.js with React."], "is_conflict": True, "ground_truth": ["conflict"]},
    {"id": "conf_04", "category": "Conflicts", "query": "We migrated our graph store from Neo4j to ArangoDB.", "existing_memories": ["MemOS uses Neo4j for entity-relationship storage."], "is_conflict": True, "ground_truth": ["conflict"]},
    {"id": "conf_05", "category": "Conflicts", "query": "I now prefer cloud-hosted AI services over local Ollama.", "existing_memories": ["User prefers local on-device execution for privacy."], "is_conflict": True, "ground_truth": ["conflict"]},
    {"id": "conf_06", "category": "Conflicts", "query": "We removed Redis and now use in-memory state only.", "existing_memories": ["Redis provides session caching for MemOS."], "is_conflict": True, "ground_truth": ["conflict"]},

    # =========================================================================
    # CATEGORY: Irrelevant / Negative (4) - should NOT match
    # =========================================================================
    {"id": "irr_01", "category": "Irrelevant", "query": "What did I eat for breakfast yesterday?", "ground_truth": [], "is_duplicate": False, "is_conflict": False, "note": "No relevant stored memory - should retrieve nothing / respond 'unknown'"},
    {"id": "irr_02", "category": "Irrelevant", "query": "What is the weather forecast?", "ground_truth": [], "is_duplicate": False, "is_conflict": False, "note": "No relevant stored memory"},
    {"id": "irr_03", "category": "Irrelevant", "query": "What is the capital of France singing?", "ground_truth": [], "is_duplicate": False, "is_conflict": False, "note": "Irrelevant to user's stored knowledge"},
    {"id": "irr_04", "category": "Irrelevant", "query": "Which movie should I watch tonight?", "ground_truth": [], "is_duplicate": False, "is_conflict": False, "note": "No stored recall"}

    # =========================================================================
    # TOTAL: 29 facts + 8 prefs + 4 projects + 5 skills + 4 goals
    #        + 6 temporal + 8 multi-hop + 6 dup + 6 conflict + 4 irrelevant
    #        = 80 scenarios
    # =========================================================================
]


def category_counts() -> dict:
    counts = {}
    for s in BENCHMARK_SCENARIOS:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    return counts


def retrieval_scenarios():
    """Scenarios that exercise retrieval/ranking (excludes pure dup/conflict tests)."""
    return [s for s in BENCHMARK_SCENARIOS if not s.get("is_duplicate") and not s.get("is_conflict")]


def lifecycle_scenarios():
    return {
        "duplicates": [s for s in BENCHMARK_SCENARIOS if s.get("is_duplicate")],
        "conflicts": [s for s in BENCHMARK_SCENARIOS if s.get("is_conflict")],
    }


if __name__ == "__main__":
    print(f"Total scenarios: {len(BENCHMARK_SCENARIOS)}")
    print("Category breakdown:")
    for cat, count in category_counts().items():
        print(f"  {cat}: {count}")
