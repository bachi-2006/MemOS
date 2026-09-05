import json
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

OLLAMA = "http://127.0.0.1:11434"
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=None)
    return _client


@asynccontextmanager
async def lifespan(application):
    yield
    global _client
    if _client:
        await _client.aclose()
        _client = None


app = FastAPI(title="MemOS Phase 2 API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    online = False
    version = ""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(OLLAMA + "/api/tags")
            online = r.status_code == 200
            if online:
                version = (r.json() or {}).get("version", "")
    except Exception:
        pass
    return {"ok": True, "ollama": online, "version": version, "port": 5151}


async def _ollama_proxy(path: str, request: Request):
    body = await request.body()
    streaming = False
    try:
        streaming = bool(json.loads(body).get("stream"))
    except Exception:
        streaming = request.headers.get("accept", "").startswith("application/x-ndjson")

    client = _get_client()

    if streaming:
        resp_ref = [None]

        async def gen():
            async with client.stream(
                "POST", OLLAMA + path, content=body,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp_ref[0] = resp
                if resp.status_code != 200:
                    _txt = (await resp.aread())[:300].decode("utf-8", "ignore")
                    yield (json.dumps({"error": "HTTP %s: %s" % (resp.status_code, _txt)}) + "\n").encode()
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk

        return StreamingResponse(gen(), media_type="application/x-ndjson")

    resp = await client.post(
        OLLAMA + path, content=body, headers={"Content-Type": "application/json"}
    )
    try:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception:
        return JSONResponse(status_code=resp.status_code, content={"error": resp.text[:300]})


@app.post("/api/ollama/chat")
async def proxy_chat(request: Request):
    return await _ollama_proxy("/api/chat", request)


@app.post("/api/ollama/embed")
async def proxy_embed(request: Request):
    return await _ollama_proxy("/api/embed", request)


@app.post("/api/ollama/generate")
async def proxy_generate(request: Request):
    return await _ollama_proxy("/api/generate", request)


async def _ollama_get(path: str):
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(OLLAMA + path)
            return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:
        return JSONResponse(status_code=502, content={"error": "ollama unreachable"})


@app.get("/api/ollama/tags")
async def proxy_tags():
    return await _ollama_get("/api/tags")


@app.get("/api/ollama/ps")
async def proxy_ps():
    return await _ollama_get("/api/ps")


DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/", include_in_schema=False)
async def index():
    if not (DIST / "index.html").is_file():
        return JSONResponse(
            status_code=200,
            content={"ok": False, "message": "Frontend not built. Run `npm run build` inside frontend/, then reload."},
        )
    return FileResponse(DIST / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    f = DIST / full_path
    if f.is_file():
        return FileResponse(f)
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return JSONResponse(status_code=404, content={"error": "not built"})
