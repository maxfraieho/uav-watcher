"""Tests for knowledge_base: ingest + retrieval."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base import ingest, retrieval


def _make_kb(tmp_path: Path) -> Path:
    md = tmp_path / "test.md"
    md.write_text(
        "# Тест\n\n## Евакуація\nПри загрозі евакуація негайна.\n\n"
        "## Зв'язок\nЕкстрений номер 112.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_index_returns_sections(tmp_path):
    _make_kb(tmp_path)
    idx, docs = ingest.build_index(tmp_path)
    assert len(docs) >= 2
    headings = [d["heading"] for d in docs]
    assert any("Евакуація" in h for h in headings)
    assert any("Зв'язок" in h for h in headings)


def test_retrieve_finds_relevant(tmp_path):
    _make_kb(tmp_path)
    n = retrieval.init(tmp_path)
    assert n >= 2
    results = retrieval.retrieve("евакуація при загрозі", top_k=2)
    assert len(results) >= 1
    assert any("евакуація" in r["text"].lower() or "евакуація" in r["heading"].lower()
               for r in results)


def test_retrieve_text_returns_string(tmp_path):
    _make_kb(tmp_path)
    retrieval.init(tmp_path)
    text = retrieval.retrieve_text("екстрений номер", top_k=2)
    assert isinstance(text, str)
    assert len(text) > 0


def test_empty_dir_returns_zero(tmp_path):
    n = retrieval.init(tmp_path)
    assert n == 0
    results = retrieval.retrieve("щось", top_k=3)
    assert results == []
