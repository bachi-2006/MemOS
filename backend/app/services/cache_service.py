"""Redis-backed LRU embedding cache with graceful no-Redis fallback.

When Redis is available, embedding vectors are cached for 24 hours (configurable
via ttl parameter) to avoid re-computing expensive Ollama embeddings for repeated
text. When Redis is unavailable (standalone mode, Redis not running), all operations
silently no-op and the caller falls through to fresh Ollama embedding generation.
"""
import json
import hashlib
from typing import List, Optional


class EmbeddingCache:
    def __init__(self):
        self._client = None
        self._failed: bool = False  # Avoid repeated connection attempts after failure

    def _redis(self):
        if self._failed:
            return None
        if self._client:
            return self._client
        try:
            import redis
            from app.core.config import settings
            c = redis.from_url(settings.REDIS_URL, socket_timeout=1.0, decode_responses=True)
            c.ping()
            self._client = c
        except Exception as e:
            print(f"[EmbeddingCache] Redis unavailable — running without embedding cache: {e}")
            self._failed = True
        return self._client

    def _key(self, text: str, model: str) -> str:
        """Stable content-addressed cache key (MD5 is fine — not a security context)."""
        return f"emb:{model}:{hashlib.md5(text.encode('utf-8')).hexdigest()}"

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Return cached embedding vector or None if uncached / Redis offline."""
        r = self._redis()
        if not r:
            return None
        try:
            raw = r.get(self._key(text, model))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set(self, text: str, model: str, vector: List[float], ttl: int = 86400):
        """Cache embedding vector with a TTL (default: 24 hours)."""
        r = self._redis()
        if not r:
            return
        try:
            r.setex(self._key(text, model), ttl, json.dumps(vector))
        except Exception:
            pass

    def invalidate(self, text: str, model: str):
        """Explicitly evict a specific key (useful after content updates)."""
        r = self._redis()
        if not r:
            return
        try:
            r.delete(self._key(text, model))
        except Exception:
            pass


# Module-level singleton — imported by ollama_service
embedding_cache = EmbeddingCache()
