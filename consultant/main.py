"""Crisis consultant — FastAPI service, port 8770."""
import os
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

load_dotenv()

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PORT          = int(os.getenv("CONSULTANT_PORT", "8770"))
KNOWLEDGE_DIR = _HERE / "knowledge"
MEMORY_DIR    = _HERE / "memory"
PROJECT_ROOT  = _HERE.parent
MEMORY_DIR.mkdir(exist_ok=True)

_observer = None
_watcher_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _observer, _watcher_thread
    from knowledge_base import retrieval
    from knowledge_base.watcher import start_watcher as start_kb_watcher
    from situation_watcher import start_watcher as start_situation_watcher
    try:
        n = retrieval.init(KNOWLEDGE_DIR)
        log.info(f"[consultant] KB ready: {n} sections from {KNOWLEDGE_DIR}")
    except Exception as e:
        log.warning(f"[consultant] KB init failed: {e}")
    _observer = start_kb_watcher(KNOWLEDGE_DIR)
    _watcher_thread = start_situation_watcher(PROJECT_ROOT)
    yield
    if _observer:
        _observer.stop()
        _observer.join()


app = FastAPI(title="Sharon-consultant", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    lang: Optional[str] = "uk"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    kb_sections_used: int


@app.get("/health")
def health():
    from knowledge_base import retrieval
    return {"status": "ok", "service": "consultant",
            "port": PORT, "kb_sections": len(retrieval._docs)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    from pipeline.graph import get_graph
    from knowledge_base.retrieval import retrieve
    try:
        result = get_graph().invoke(
            {
                "messages": [],
                "query": req.message,
                "kb_context": "",
                "web_context": "",
                "reply": "",
                "session_id": req.session_id,
                "lang": req.lang or "uk",
            },
            config={"configurable": {"thread_id": req.session_id}},
        )
    except Exception as e:
        log.error(f"[consultant] pipeline error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    return ChatResponse(
        reply=result.get("reply", ""),
        session_id=req.session_id,
        kb_sections_used=len(retrieve(req.message, top_k=3)),
    )


@app.get("/situation")
def situation():
    """Current situation from alerts.in.ua watchdog."""
    from situation_watcher import read_situation
    summary = read_situation(PROJECT_ROOT)
    return {"summary": summary or "Дані ще не завантажені або застаріли."}


@app.get("/kb/sections")
def kb_sections():
    from knowledge_base import retrieval
    return {"count": len(retrieval._docs),
            "sections": [{"source": d["source"], "heading": d["heading"]}
                         for d in retrieval._docs]}


@app.get("/kb/search")
def kb_search(q: str, top_k: int = 3):
    from knowledge_base.retrieval import retrieve
    return {"results": retrieve(q, top_k=top_k)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)
