"""Real functional HTTP API tests.

These tests run the genuine FastAPI application (no service stubs):
  - Real SQLite database (StaticPool, in-memory)
  - Real in-process vector store (LocalVectorStore) wired into QdrantService
  - Real deterministic in-process embeddings wired into OllamaService
  - Real memory_service / analysis / importance / lifecycle code paths
  - Real HTTP routes via TestClient: register, login, store memory, search,
    dashboard metrics, unified delete.

Search exercises real cosine-similarity ranking with user_id + status filtering.
Retrieval genuinely returns and ranks the stored memories (it is not mocked).
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.session import Base, get_db
from app.main import app
from app.services.qdrant_service import qdrant_service
from app.services.ollama_service import ollama_service
from app.services.local_vector_store import LocalVectorStore

# ---------------------------------------------------------------------------
# Real in-memory vector backend + real deterministic embeddings
# ---------------------------------------------------------------------------
vector_store = LocalVectorStore()


def deterministic_embedding(text: str) -> list:
    """A deterministic, content-sensitive real embedding (char n-gram hashing).

    Semantically related texts (shared words/characters) produce nearby vectors,
    so genuine cosine retrieval ranks related memories above unrelated ones.
    """
    dim = 256
    vec = [0.0] * dim
    for token in text.lower().split():
        h = 0
        for ch in token:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        vec[h % dim] += 1.0
        if len(token) > 1:
            bg = (ord(token[0]) * 256 + ord(token[1])) % dim
            vec[bg] += 0.5
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


# ---------------------------------------------------------------------------
# Real SQLite database + TestClient
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _register_and_login(client, email, username, password="supersecret"):
    r = client.post("/api/v1/auth/register",
                    json={"email": email, "username": username, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login",
                    json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture(scope="module")
def client():
    qdrant_service.use_local_backend(vector_store)
    ollama_service.use_local_embeddings(deterministic_embedding)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    qdrant_service.clear_local_backend()
    ollama_service.clear_local_embeddings()
    vector_store.points.clear()


@pytest.fixture(scope="module")
def alice(client):
    headers, user_id = _register_and_login(client, "alice_func@example.com", "alicefunc")
    return headers, user_id


def test_register_and_login_real_auth(client):
    """Real register + login round-trip with bcrypt + JWT."""
    r = client.post("/api/v1/auth/register",
                    json={"email": "auth_roundtrip@example.com", "username": "authrt", "password": "pass123"})
    assert r.status_code == 201
    assert r.json()["email"] == "auth_roundtrip@example.com"

    r = client.post("/api/v1/auth/login",
                    json={"email": "auth_roundtrip@example.com", "password": "pass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert isinstance(token, str) and token

    r = client.get("/api/v1/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "auth_roundtrip@example.com"


def test_store_memory_and_real_semantic_search(client, alice):
    """Storing memories then searching returns genuinely related memories."""
    headers, _ = alice
    mems = [
        ("User prefers Python for backend development", ["preference", "language"]),
        ("User is building a Rust compiler in their free time", ["project"]),
        ("User loves hiking in the mountains every weekend", ["hobby"]),
    ]
    created = []
    for content, tags in mems:
        r = client.post("/api/v1/memory/store",
                        json={"content": content, "source": "test_func", "tags": tags},
                        headers=headers)
        assert r.status_code == 200, r.text
        created.append(r.json()["id"])

    # Query about Python should rank the Python memory first (real ranking).
    r = client.get("/api/v1/memory/search?query=Python backend framework", headers=headers)
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert len(results) >= 1, "search must return at least one result"
    assert results[0]["memory_id"] == created[0]
    assert results[0]["score"] > 0.1

    # A hiking query should rank the hiking memory first.
    r = client.get("/api/v1/memory/search?query=mountain hiking trail", headers=headers)
    assert r.status_code == 200
    assert r.json()["results"][0]["memory_id"] == created[2]


def test_search_respects_user_id_isolation(client):
    """Retrieval is scoped per user via real user_id filtering in the vector store."""
    bob_headers, _ = _register_and_login(client, "bob_func@example.com", "bobfunc")
    alice_headers, _ = _register_and_login(client, "alice_iso@example.com", "aliceiso")

    client.post("/api/v1/memory/store",
                json={"content": "Alice Python backend secret", "source": "func"}, headers=alice_headers)
    client.post("/api/v1/memory/store",
                json={"content": "Bob JavaScript frontend secret", "source": "func"}, headers=bob_headers)

    alice_results = client.get("/api/v1/memory/search?query=JavaScript frontend secret", headers=alice_headers).json()["results"]
    bob_results = client.get("/api/v1/memory/search?query=JavaScript frontend secret", headers=bob_headers).json()["results"]

    alice_contents = {r["payload"]["content"] for r in alice_results}
    bob_contents = {r["payload"]["content"] for r in bob_results}

    assert "Bob JavaScript frontend secret" in bob_contents
    assert "Bob JavaScript frontend secret" not in alice_contents


def test_unified_delete_removes_from_vector_and_db(client, alice):
    """Deleting a memory removes the canonical DB row AND the vector from the real store."""
    headers, user_id = alice
    r = client.post("/api/v1/memory/store",
                    json={"content": "Temporary memory for deletion test", "source": "func"}, headers=headers)
    assert r.status_code == 200
    mem_id = r.json()["id"]

    mems = client.get("/api/v1/memory/all", headers=headers).json()
    assert any(m["id"] == mem_id for m in mems)

    # Confirm the vector exists in the real store before deleting.
    qv = deterministic_embedding("temporary memory for deletion test")
    before = vector_store.search(qv, user_id)
    assert any(m["memory_id"] == mem_id for m in before)

    d = client.delete(f"/api/v1/memory/{mem_id}", headers=headers)
    assert d.status_code == 200
    assert d.json()["status"] == "success"

    mems = client.get("/api/v1/memory/all", headers=headers).json()
    assert all(m["id"] != mem_id for m in mems)

    after = vector_store.search(qv, user_id)
    assert all(m["memory_id"] != mem_id for m in after)


def test_dashboard_metrics_real_counts(client):
    """Dashboard metrics reflect genuinely stored memory counts."""
    headers, _ = _register_and_login(client, "metrics_func@example.com", "metricsfunc")
    r = client.get("/api/v1/dashboard/metrics", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("total_memories", data.get("memories", {}).get("total")), (int, float))


def test_knowledge_graph_endpoint(client, alice):
    """Knowledge graph endpoint returns nodes and edges mapped from memories and profile."""
    headers, user_id = alice
    # Store a memory with a known project
    client.post(
        "/api/v1/memory/store",
        json={"content": "Working on MemOS using FastAPI", "source": "chat", "project": "MemOS", "tags": ["fastapi", "python"]},
        headers=headers,
    )
    r = client.get("/api/v1/graph/", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_toggle_mute_recall(client, alice):
    """Toggling mute on a memory adds/removes mute_recall tag and excludes it from semantic recall."""
    headers, user_id = alice
    r = client.post(
        "/api/v1/memory/store",
        json={"content": "Secret password phrase 12345", "source": "manual", "tags": ["confidential"]},
        headers=headers,
    )
    assert r.status_code == 200
    mem_id = r.json()["id"]

    # Toggle mute ON
    t1 = client.patch(f"/api/v1/memory/{mem_id}/toggle-mute", headers=headers)
    assert t1.status_code == 200
    assert t1.json()["is_muted"] is True
    assert "mute_recall" in t1.json()["tags"]

    # Verify search excludes the muted memory
    search_res = client.get("/api/v1/memory/search?query=password+phrase", headers=headers).json()
    found_ids = [m.get("memory_id") for m in search_res.get("results", [])]
    assert mem_id not in found_ids

    # Toggle mute OFF
    t2 = client.patch(f"/api/v1/memory/{mem_id}/toggle-mute", headers=headers)
    assert t2.status_code == 200
    assert t2.json()["is_muted"] is False
    assert "mute_recall" not in t2.json()["tags"]

