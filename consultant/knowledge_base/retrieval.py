"""BM25 retrieval singleton — call init() once at startup."""
from pathlib import Path
from rank_bm25 import BM25Plus
from .ingest import build_index, _tokenize

_index: BM25Plus | None = None
_docs: list[dict] = []


def init(knowledge_dir: str | Path) -> int:
    global _index, _docs
    _index, _docs = build_index(knowledge_dir)
    return len(_docs)


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    if _index is None:
        return []
    scores = _index.get_scores(_tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [
        {"source": _docs[i]["source"], "heading": _docs[i]["heading"],
         "text": _docs[i]["text"], "score": round(float(s), 4)}
        for i, s in ranked[:top_k] if s > 0
    ]


def retrieve_text(query: str, top_k: int = 3) -> str:
    secs = retrieve(query, top_k)
    return "\n\n---\n\n".join(f"### {s['heading']}\n{s['text']}" for s in secs)
