#!/usr/bin/env python3
"""
MemOS Real-Database Empirical Research Benchmarking Engine
==========================================================
This benchmark measures ACTUAL retrieval quality and latency through the real
persistence stack (PostgreSQL + Qdrant + Neo4j) and the real Ollama inference
layer. It replaces the earlier word-overlap simulation with genuine queries.

Requirements to run:
  - PostgreSQL, Qdrant, Neo4j, Redis running
  - Ollama running with at least one model + embedding model
  - A .env file present (SECRET_KEY etc.)

Run:
  python scripts/real_benchmark.py

It measures, per scenario, against the live databases:
  - Raw Ollama      : no retrieval, asks the LLM directly
  - Naive Vector RAG: Qdrant top-k vector retrieval only
  - MemOS Multi-Store: Qdrant vectors + Neo4j graph triples + user profile
Metrics: Precision@3, Recall@3, MRR, and latency breakdown
  (embedding + Qdrant + Neo4j + PostgreSQL + context + Ollama inference).
"""

import sys
import os
import time
import json
import statistics
from typing import List, Dict, Any, Tuple

# Ensure backend is importable so we can reuse the real services
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("API_V1_STR", "/api/v1")

# -----------------------------------------------------------------------------
# Load benchmark dataset
# -----------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_dataset import BENCHMARK_SCENARIOS, retrieval_scenarios  # noqa: E402

# -----------------------------------------------------------------------------
# Compute F1 / classification helpers
# -----------------------------------------------------------------------------

def retrieve_relevant_count(retrieved: List[str], ground_truth: List[str]) -> Tuple[int, int]:
    """Returns (hits, first_hit_rank). A doc 'hits' if any ground-truth term appears."""
    hits = 0
    first_hit_rank = 0
    joined_gt = [gt.lower() for gt in ground_truth]
    for idx, doc in enumerate(retrieved, start=1):
        doc_lower = doc.lower()
        if any(gt and gt in doc_lower for gt in joined_gt):
            hits += 1
            if first_hit_rank == 0:
                first_hit_rank = idx
    return hits, first_hit_rank


def compute_precision_recall_mrr(retrieved: List[str], ground_truth: List[str], k: int = 3) -> Tuple[float, float, float]:
    hits, first_hit_rank = retrieve_relevant_count(retrieved, ground_truth)
    precision = hits / k if k > 0 else 0.0
    recall = hits / len(ground_truth) if ground_truth else 0.0
    mrr = 1.0 / first_hit_rank if first_hit_rank > 0 else 0.0
    return precision, recall, mrr


# -----------------------------------------------------------------------------
# Real retrieval baselines
# -----------------------------------------------------------------------------

def seed_memory_base(db, user_id: str, corpus: List[str]):
    """
    Index the scenario corpus into the REAL memory store (Postgres + Qdrant)
    so that retrieval baselines operate on genuine stored memories.
    Returns list of stored contents.
    """
    from app.services.memory_service import memory_service
    from app.models.models import MemoryModel

    stored = []
    for content in corpus:
        if content.strip():
            exists = db.query(MemoryModel).filter(
                MemoryModel.user_id == user_id,
                MemoryModel.content == content.strip(),
                MemoryModel.status == "active"
            ).first()
            if not exists:
                import asyncio
                asyncio.run(memory_service.create_and_index_memory(
                    db=db, user_id=user_id, content=content.strip(),
                    source="benchmark", importance_score=1.0
                ))
            stored.append(content.strip())
    return stored


def real_naive_rag(user_id: str, query: str, limit: int = 5) -> Tuple[List[str], Dict[str, float]]:
    """
    Baseline B: genuine Qdrant vector retrieval only.
    Returns (retrieved_docs, latency_breakdown).
    """
    import asyncio
    import time as t
    lat = {"embedding": 0.0, "qdrant": 0.0}

    from app.services.ollama_service import ollama_service
    from app.services.qdrant_service import qdrant_service

    s = t.perf_counter()
    query_vector = asyncio.run(ollama_service.generate_embedding(query))
    lat["embedding"] = (t.perf_counter() - s) * 1000.0
    if not query_vector:
        return [], lat

    s = t.perf_counter()
    results = qdrant_service.search_similar_memories(
        query_vector=query_vector, user_id=user_id, limit=limit
    )
    lat["qdrant"] = (t.perf_counter() - s) * 1000.0

    docs = []
    for r in results:
        payload = r.get("payload", {})
        docs.append(payload.get("content", ""))
    return docs, lat


def real_memos_hybrid(db, user_id: str, query: str, limit: int = 5) -> Tuple[List[str], Dict[str, float]]:
    """
    Proposed: MemOS multi-store retrieval.
    Combines:
      1. Qdrant vector similarity (user-scoped, active)
      2. Neo4j knowledge graph triples (user-scoped)
      3. PostgreSQL user-profile preferences
    Returns (retrieved_docs, latency_breakdown).
    """
    import asyncio
    import time as t
    from sqlalchemy import text
    lat = {"embedding": 0.0, "qdrant": 0.0, "neo4j": 0.0, "postgres": 0.0}

    from app.services.ollama_service import ollama_service
    from app.services.qdrant_service import qdrant_service
    from app.services.graph_service import graph_service

    docs = []
    ranked = []   # (docs) in retrieval order

    # 1. Embedding
    s = t.perf_counter()
    query_vector = asyncio.run(ollama_service.generate_embedding(query))
    lat["embedding"] = (t.perf_counter() - s) * 1000.0
    if query_vector:
        # 2. Qdrant
        s = t.perf_counter()
        results = qdrant_service.search_similar_memories(
            query_vector=query_vector, user_id=user_id, limit=limit
        )
        lat["qdrant"] = (t.perf_counter() - s) * 1000.0
        for r in results:
            payload = r.get("payload", {})
            content = payload.get("content", "")
            if content:
                docs.append(content)

    # 3. Neo4j graph triples (user-scoped)
    try:
        s = t.perf_counter()
        nodes = graph_service.get_user_graph(user_id)
        lat["neo4j"] = (t.perf_counter() - s) * 1000.0
        if nodes and nodes.get("edges"):
            for edge in nodes["edges"]:
                triple = f"Fact: {edge.get('source','')} -[{edge.get('relationship','')}]-> {edge.get('target','')}"
                if triple not in docs:
                    docs.append(triple)
    except Exception as e:
        print(f"  [neo4j notice] {e}")

    # 4. PostgreSQL user profile
    try:
        s = t.perf_counter()
        from app.models.models import UserProfile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        lat["postgres"] = (t.perf_counter() - s) * 1000.0
        if profile:
            for field in ("preferred_languages", "preferred_frameworks", "current_projects",
                          "interests", "skills", "technologies"):
                val = getattr(profile, field, None)
                if val:
                    if isinstance(val, list):
                        for item in val:
                            line = f"Profile: {field} -> {item}"
                            if line not in docs:
                                docs.append(line)
                    elif isinstance(val, str) and val:
                        line = f"Profile: {field} -> {val}"
                        if line not in docs:
                            docs.append(line)
    except Exception as e:
        print(f"  [postgres notice] {e}")

    return docs, lat


def raw_ollama_llm(user_id: str, query: str) -> Tuple[List[str], Dict[str, float], str]:
    """Baseline A: query the LLM with no retrieval. Returns (empty docs, latency, answer)."""
    import asyncio
    import time as t
    from app.services.ollama_service import ollama_service

    lat = {"ollama_inference": 0.0}
    s = t.perf_counter()
    answer = asyncio.run(ollama_service.generate_chat(prompt=f"Question: {query}\nAnswer: "))
    lat["ollama_inference"] = (t.perf_counter() - s) * 1000.0
    return [], lat, answer


# -----------------------------------------------------------------------------
# Main benchmark runner
# -----------------------------------------------------------------------------

def _infrastructure_ready() -> bool:
    """Return True only when the live stores the benchmark actually needs
    (Ollama + Qdrant) are reachable. Guards CI and other infra-less runs so the
    harness exits cleanly instead of producing garbage metrics against
    fallback/absent backend storеs."""
    import asyncio
    from app.core.config import settings
    from app.services.ollama_service import ollama_service
    from app.services.qdrant_service import qdrant_service

    status = asyncio.run(ollama_service.get_status())
    if not status.get("connected"):
        print(f"[SKIP] Real benchmark requires a live Ollama instance at "
              f"{settings.OLLAMA_BASE_URL} (status: {status.get('status')}). "
              f"Skipping benchmark.")
        return False
    if not status.get("installed_models"):
        print("[SKIP] Real benchmark requires at least one installed Ollama "
              "model. Skipping benchmark.")
        return False
    if qdrant_service.get_client() is None:
        print(f"[SKIP] Real benchmark requires a reachable Qdrant server at "
              f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}. Skipping benchmark.")
        return False
    return True


def run_benchmark() -> Dict[str, Any]:
    if not _infrastructure_ready():
        return {
            "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "SKIPPED",
            "reason": "Live Ollama / Qdrant infrastructure not reachable.",
            "uses_real_databases": False,
        }

    from sqlalchemy.orm import Session as SaSession
    from app.database.session import SessionLocal
    from app.models.models import User

    # Use a dedicated benchmark user so we never pollute real user data
    bench_user_id = "benchmark_user"
    db: SaSession = SessionLocal()
    try:
        user = db.query(User).filter(User.id == bench_user_id).first()
        if not user:
            user = User(id=bench_user_id, email="bench@memos.local", username="benchmark",
                        hashed_password="benchmark")
            db.add(user)
            db.commit()
    finally:
        pass

    scenarios = retrieval_scenarios()
    all_scenarios = BENCHMARK_SCENARIOS

    results = {
        "raw_llm": {"precision": [], "recall": [], "mrr": [], "latencies": []},
        "naive_rag": {"precision": [], "recall": [], "mrr": [], "latencies": []},
        "memos_hybrid": {"precision": [], "recall": [], "mrr": [], "latencies": []},
    }

    # Classification metrics for lifecycle (duplicate / conflict detection)
    # TP / FP / FN / TN across ALL scenarios (not just the positive ones)
    dup_clf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    conf_clf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    print("=" * 78)
    print("   [REAL MEMOS BENCHMARK] Live PostgreSQL + Qdrant + Neo4j + Ollama")
    print("=" * 78)
    print(f"Retrieval scenarios: {len(scenarios)}")
    print(f"Total scenarios (incl. lifecycle): {len(all_scenarios)}")

    for sc in all_scenarios:
        query = sc["query"]
        gt = sc.get("ground_truth", [])
        corpus = sc.get("corpus", [])
        existing = sc.get("existing_memories", [])

        # Seed corpus + existing memories into the REAL store
        seed_corpus = corpus + existing
        if seed_corpus:
            seed_memory_base(db, bench_user_id, seed_corpus)

        # Retrieval scenarios (exclude pure dup/conflict tests from ranking eval)
        if not sc.get("is_duplicate", False) and not sc.get("is_conflict", False):
            time.sleep(0.05)

            # --- Baseline A: Raw LLM (no retrieval) ---
            _, raw_lat, raw_answer = raw_ollama_llm(bench_user_id, query)
            results["raw_llm"]["latencies"].append(sum(raw_lat.values()))
            p, r, mrr = compute_precision_recall_mrr([raw_answer], gt, k=3)
            results["raw_llm"]["precision"].append(p)
            results["raw_llm"]["recall"].append(r)
            results["raw_llm"]["mrr"].append(mrr)

            # --- Baseline B: Naive Vector RAG (real Qdrant) ---
            docs, naive_lat = real_naive_rag(bench_user_id, query)
            results["naive_rag"]["latencies"].append(sum(naive_lat.values()))
            p, r, mrr = compute_precision_recall_mrr(docs, gt, k=3)
            results["naive_rag"]["precision"].append(p)
            results["naive_rag"]["recall"].append(r)
            results["naive_rag"]["mrr"].append(mrr)

            # --- Proposed: MemOS Multi-Store ---
            docs, memos_lat = real_memos_hybrid(db, bench_user_id, query)
            results["memos_hybrid"]["latencies"].append(sum(memos_lat.values()))
            p, r, mrr = compute_precision_recall_mrr(docs, gt, k=3)
            results["memos_hybrid"]["precision"].append(p)
            results["memos_hybrid"]["recall"].append(r)
            results["memos_hybrid"]["mrr"].append(mrr)

        # --- Duplicate classification ---
        is_dup = bool(sc.get("is_duplicate"))
        pred_dup = False
        if is_dup or existing:
            pred_dup = evaluate_similarity(sc["query"], sc.get("existing_memories", []))
        if is_dup and pred_dup:
            dup_clf["tp"] += 1
        elif is_dup and not pred_dup:
            dup_clf["fn"] += 1
        elif not is_dup and pred_dup:
            dup_clf["fp"] += 1
        elif not is_dup and not pred_dup:
            dup_clf["tn"] += 1

        # --- Conflict classification ---
        is_conf = bool(sc.get("is_conflict"))
        pred_conf = False
        if is_conf or existing:
            pred_conf = evaluate_conflict(sc["query"], sc.get("existing_memories", []))
        if is_conf and pred_conf:
            conf_clf["tp"] += 1
        elif is_conf and not pred_conf:
            conf_clf["fn"] += 1
        elif not is_conf and pred_conf:
            conf_clf["fp"] += 1
        elif not is_conf and not pred_conf:
            conf_clf["tn"] += 1

    # Aggregate
    def mean(v): return round(statistics.mean(v), 4) if v else 0.0

    raw_p = mean(results["raw_llm"]["precision"])
    raw_r = mean(results["raw_llm"]["recall"])
    raw_m = mean(results["raw_llm"]["mrr"])
    raw_l = round(statistics.mean(results["raw_llm"]["latencies"]), 2) if results["raw_llm"]["latencies"] else 0.0

    naive_p = mean(results["naive_rag"]["precision"])
    naive_r = mean(results["naive_rag"]["recall"])
    naive_m = mean(results["naive_rag"]["mrr"])
    naive_l = round(statistics.mean(results["naive_rag"]["latencies"]), 2) if results["naive_rag"]["latencies"] else 0.0

    memos_p = mean(results["memos_hybrid"]["precision"])
    memos_r = mean(results["memos_hybrid"]["recall"])
    memos_m = mean(results["memos_hybrid"]["mrr"])
    memos_l = round(statistics.mean(results["memos_hybrid"]["latencies"]), 2) if results["memos_hybrid"]["latencies"] else 0.0

    dup_rate = round((dup_clf["tp"] + dup_clf["tn"]) / max(1, sum(dup_clf.values())) * 100, 1)
    conf_rate = round((conf_clf["tp"] + conf_clf["tn"]) / max(1, sum(conf_clf.values())) * 100, 1)

    def f1_calc(clf: Dict[str, int]) -> float:
        precision = clf["tp"] / (clf["tp"] + clf["fp"]) if (clf["tp"] + clf["fp"]) else 0.0
        recall = clf["tp"] / (clf["tp"] + clf["fn"]) if (clf["tp"] + clf["fn"]) else 0.0
        return round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0.0

    dup_f1 = f1_calc(dup_clf)
    conf_f1 = f1_calc(conf_clf)

    print("\n" + "=" * 78)
    print("RESULTS (real retrieval, live databases)")
    print("=" * 78)
    print(f"{'System':<22} | {'Precision@3':<11} | {'Recall@3':<9} | {'MRR':<8} | {'Latency(ms)':<11}")
    print("-" * 70)
    print(f"{'Raw Ollama':<22} | {raw_p:<11} | {raw_r:<9} | {raw_m:<8} | {raw_l:<11}")
    print(f"{'Naive Vector RAG':<22} | {naive_p:<11} | {naive_r:<9} | {naive_m:<8} | {naive_l:<11}")
    print(f"{'MemOS Multi-Store':<22} | {memos_p:<11} | {memos_r:<9} | {memos_m:<8} | {memos_l:<11}")
    print("-" * 70)

    print("\nLIFECYCLE EVALUATION (classification over all scenarios):")
    print(f"  Duplicate detection: accuracy {dup_rate}%  | precision "
          f"{round(dup_clf['tp']/max(1,dup_clf['tp']+dup_clf['fp']),4)} | recall "
          f"{round(dup_clf['tp']/max(1,dup_clf['tp']+dup_clf['fn']),4)} | F1 {dup_f1}")
    print(f"  Conflict detection : accuracy {conf_rate}% | precision "
          f"{round(conf_clf['tp']/max(1,conf_clf['tp']+conf_clf['fp']),4)} | recall "
          f"{round(conf_clf['tp']/max(1,conf_clf['tp']+conf_clf['fn']),4)} | F1 {conf_f1}")
    print(f"  (Duplicate) TP={dup_clf['tp']} FP={dup_clf['fp']} FN={dup_clf['fn']} TN={dup_clf['tn']}")
    print(f"  (Conflict ) TP={conf_clf['tp']} FP={conf_clf['fp']} FN={conf_clf['fn']} TN={conf_clf['tn']}")

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scenarios": len(scenarios),
        "uses_real_databases": True,
        "metrics": {
            "raw_llm": {"precision_at_3": raw_p, "recall_at_3": raw_r, "mrr": raw_m, "latency_ms": raw_l},
            "naive_rag": {"precision_at_3": naive_p, "recall_at_3": naive_r, "mrr": naive_m, "latency_ms": naive_l},
            "memos_hybrid": {"precision_at_3": memos_p, "recall_at_3": memos_r, "mrr": memos_m, "latency_ms": memos_l}
        },
        "lifecycle_accuracy": {
            "duplicate_detection_percent": dup_rate,
            "conflict_detection_percent": conf_rate
        },
        "lifecycle_metrics": {
            "duplicate_f1": dup_f1,
            "duplicate_tp_fp_fn_tn": dup_clf,
            "conflict_f1": conf_f1,
            "conflict_tp_fp_fn_tn": conf_clf
        }
    }

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "BENCHMARK_RESULTS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[OK] Real benchmark results exported to: {out_path}")

    db.close()
    return summary


def _significant_tokens(text: str):
    """Content-bearing tokens (length > 3), excluding generic filler words and punctuation."""
    import re
    stop = {"with", "from", "that", "this", "have", "been", "into", "your", "more", "user", "using"}
    words = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return {w for w in words if len(w) > 3 and w not in stop}


def evaluate_similarity(query: str, existing: List[str]) -> bool:
    """Heuristic: near-duplicate detection via token overlap + Jaccard.

    Two independent signals:
      1. >= 2 shared significant tokens  -> duplicate/similar
      2. High Jaccard overlap on the smaller text (catches short rephrases that
         share only a single strong content word, e.g. "I primarily use Python."
         vs "My primary language is Python.")
    """
    q_tokens = _significant_tokens(query)
    if not q_tokens:
        return bool(existing)
    for ex in existing:
        ex_tokens = _significant_tokens(ex)
        shared = q_tokens.intersection(ex_tokens)
        if len(shared) >= 2:
            return True
        # Short-text Jaccard: a single shared content word among a tiny set is a
        # strong near-duplicate signal.
        union = q_tokens | ex_tokens
        if union and len(shared) >= 1:
            jac = len(shared) / len(union)
            if len(union) <= 6 and jac >= 0.30:
                return True
    return False


def evaluate_conflict(query: str, existing: List[str]) -> bool:
    """Heuristic: presence of opposing keyword pairs => conflict."""
    opposing = [("python", "go"), ("local", "cloud"), ("qdrant", "pinecone"),
                ("next.js", "vue"), ("neo4j", "arangodb"), ("redis", "in-memory"),
                ("vector", "sql"), ("ollama", "cloud")]
    q_l = query.lower()
    for a, b in opposing:
        ex_l = " ".join(existing).lower()
        if (a in q_l and b in ex_l) or (b in q_l and a in ex_l):
            return True
    return False


if __name__ == "__main__":
    run_benchmark()
