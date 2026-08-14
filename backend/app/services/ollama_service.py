import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

class OllamaService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    async def list_models(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("models", [])
                return []
            except Exception as e:
                print(f"Ollama connection error: {e}")
                return []

    async def generate_chat(
        self,
        prompt: str,
        model: str = None,
        system_context: Optional[str] = None
    ) -> str:
        model = model or settings.DEFAULT_LLM_MODEL
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system_context:
            payload["system"] = system_context

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "")
                return f"Ollama Error ({response.status_code}): {response.text}"
            except Exception as e:
                return f"Failed to connect to local Ollama instance at {self.base_url}: {str(e)}"

    async def generate_embedding(self, text: str, model: str = None) -> List[float]:
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
