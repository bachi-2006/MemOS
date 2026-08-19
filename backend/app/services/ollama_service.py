import time
import json
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.config import settings

class OllamaService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def get_status(self) -> Dict[str, Any]:
        """
        Phase 1: Deep health & status detection of local Ollama instance.
        Returns:
            connected: bool
            endpoint: str
            status: OLLAMA_NOT_RUNNING | OLLAMA_RUNNING_NO_MODELS | OLLAMA_RUNNING_WITH_MODELS
            installed_models: List[str]
            selected_model: str
            version: Optional[str]
            latency_ms: float
        """
        start_time = time.time()
        endpoint = self.base_url
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # 1. Check version endpoint
                version = "unknown"
                try:
                    v_res = await client.get(f"{endpoint}/api/version")
                    if v_res.status_code == 200:
                        version = v_res.json().get("version", "unknown")
                except Exception:
                    pass

                # 2. Check tags / models endpoint
                tags_res = await client.get(f"{endpoint}/api/tags")
                latency = round((time.time() - start_time) * 1000, 1)

                if tags_res.status_code == 200:
                    data = tags_res.json()
                    models_raw = data.get("models", [])
                    model_names = [m.get("name") for m in models_raw if "name" in m]
                    
                    if len(model_names) == 0:
                        status_enum = "OLLAMA_RUNNING_NO_MODELS"
                    else:
                        status_enum = "OLLAMA_RUNNING_WITH_MODELS"

                    selected = settings.DEFAULT_LLM_MODEL
                    if model_names and selected not in model_names:
                        selected = model_names[0]

                    return {
                        "connected": True,
                        "endpoint": endpoint,
                        "status": status_enum,
                        "installed_models": model_names,
                        "models_details": models_raw,
                        "selected_model": selected,
                        "version": version,
                        "latency_ms": latency
                    }
                else:
                    return {
                        "connected": False,
                        "endpoint": endpoint,
                        "status": "OLLAMA_NOT_RUNNING",
                        "installed_models": [],
                        "models_details": [],
                        "selected_model": settings.DEFAULT_LLM_MODEL,
                        "version": None,
                        "latency_ms": latency,
                        "error": f"Ollama HTTP {tags_res.status_code}"
                    }
        except Exception as e:
            latency = round((time.time() - start_time) * 1000, 1)
            return {
                "connected": False,
                "endpoint": endpoint,
                "status": "OLLAMA_NOT_RUNNING",
                "installed_models": [],
                "models_details": [],
                "selected_model": settings.DEFAULT_LLM_MODEL,
                "version": None,
                "latency_ms": latency,
                "error": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available local Ollama models with real metadata."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("models", [])
                return []
            except Exception as e:
                print(f"Ollama connection error in list_models: {e}")
                return []

    async def generate_chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_context: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Non-streaming generation from local Ollama."""
        model = model or settings.DEFAULT_LLM_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system_context:
            payload["system"] = system_context
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "")
                return f"Ollama Error ({response.status_code}): {response.text}"
            except Exception as e:
                return f"Failed to connect to local Ollama instance at {self.base_url}: {str(e)}"

    async def generate_chat_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_context: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Phase 4: Streaming token generator directly from Ollama.
        Yields individual text token deltas as they arrive from Ollama.
        """
        model = model or settings.DEFAULT_LLM_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if system_context:
            payload["system"] = system_context
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status_code != 200:
                        yield f"Error: Ollama returned status {response.status_code}"
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done", False):
                                break
                        except Exception:
                            continue
            except Exception as e:
                yield f"[Ollama Connection Error: {str(e)}]"

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generates embedding vector from local Ollama."""
        model = model or settings.DEFAULT_EMBEDDING_MODEL
        payload = {
            "model": model,
            "prompt": text
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                if response.status_code == 200:
                    return response.json().get("embedding", [])
                return []
            except Exception as e:
                print(f"Ollama embedding error: {e}")
                return []

ollama_service = OllamaService()
