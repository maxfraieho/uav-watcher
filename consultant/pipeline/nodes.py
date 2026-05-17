"""LangGraph nodes: retrieve_kb → generate."""
import os
import httpx
from .states import CrisisState

PROXY_URL   = os.getenv("PROXY_URL", "http://localhost:18880/v1")
PROXY_TOKEN = os.getenv("PROXY_TOKEN", "freecc")
PROXY_MODEL = os.getenv("PROXY_MODEL", "docs-assistant-proxy")

SYSTEM_PROMPT = """Ти — кризовий консультант системи UAV Watcher.
Відповідай стисло, чітко, по пунктах. Використовуй надану базу знань.
Якщо питання не стосується безпеки — ввічливо поясни що ти спеціалізуєшся на кризових ситуаціях.
Відповідай УКРАЇНСЬКОЮ мовою."""


def _llm_call(messages: list[dict]) -> str:
    resp = httpx.post(
        f"{PROXY_URL}/chat/completions",
        json={"model": PROXY_MODEL, "messages": messages, "temperature": 0.15},
        headers={"Authorization": f"Bearer {PROXY_TOKEN}"},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def retrieve_kb(state: CrisisState) -> dict:
    from knowledge_base.retrieval import retrieve_text
    return {"kb_context": retrieve_text(state["query"], top_k=3)}


def generate(state: CrisisState) -> dict:
    history = list(state.get("messages", []))
    user_content = state["query"]
    if state.get("kb_context"):
        user_content = f"[База знань]\n{state['kb_context']}\n\n[Запит]\n{state['query']}"

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-6:]:
        msgs.append({"role": msg["type"], "content": msg["content"]})
    msgs.append({"role": "user", "content": user_content})

    reply = _llm_call(msgs)
    return {
        "reply": reply,
        "messages": [
            {"type": "human", "content": state["query"]},
            {"type": "ai",    "content": reply},
        ],
    }
