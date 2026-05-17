"""BM25 index builder — loads all .md files from knowledge_dir."""
import re
from pathlib import Path
from rank_bm25 import BM25Plus


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯіІїЇєЄёЁ0-9_]+", text.lower())


def _split_sections(text: str) -> list[dict]:
    sections, heading, lines = [], "intro", []
    for line in text.splitlines():
        if line.startswith("## "):
            if lines:
                sections.append({"heading": heading, "text": "\n".join(lines).strip()})
            heading, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if lines:
        sections.append({"heading": heading, "text": "\n".join(lines).strip()})
    return [s for s in sections if s["text"]]


def build_index(knowledge_dir: str | Path) -> tuple[BM25Plus, list[dict]]:
    """Load all .md files -> BM25 index + docs list."""
    knowledge_dir = Path(knowledge_dir)
    docs: list[dict] = []
    for md in sorted(knowledge_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for sec in _split_sections(text):
            tokens = _tokenize(sec["heading"] + " " + sec["text"])
            docs.append({"source": md.name, "heading": sec["heading"],
                         "text": sec["text"], "tokens": tokens})
    if not docs:
        return None, []
    return BM25Plus([d["tokens"] for d in docs]), docs
