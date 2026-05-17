"""LangGraph nodes: retrieve_kb -> web_search -> generate."""
import os
import pathlib
import time
import httpx
from langchain_core.messages import HumanMessage, AIMessage
from situation_watcher import read_situation
from .states import CrisisState

PROXY_URL   = os.getenv("PROXY_URL", "http://localhost:18880/v1")
PROXY_TOKEN = os.getenv("PROXY_TOKEN", "freecc")
PROXY_MODEL = os.getenv("PROXY_MODEL", "docs-assistant-proxy")

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_WEB_SEARCH_KEYWORDS = [
    "де ", "найближч", "бомбосховищ", "укрит", "зараз", "ситуаці",
    "новин", "адрес", "знайти", "поруч", "where", "shelter",
    "nearest", "news", "current", "address", "find", "nearby",
]

SYSTEM_PROMPT = """Ти — кризовий консультант системи UAV Watcher.
Твоя роль: надавати точні, практичні інструкції цивільним людям під час
повітряних тривог, ракетних обстрілів та надзвичайних ситуацій в Україні.

## Правила відповіді

**Формат:**
- Відповідай УКРАЇНСЬКОЮ мовою (якщо користувач пише іншою — відповідай тією ж мовою)
- Стисло і по пунктах. Максимум 5-7 рядків на відповідь
- При загрозі життю — починай з найважливішої дії, без вступів
- Використовуй емодзі тільки функціонально

**Тон:**
- Спокійний, впевнений, без паніки
- Директивний при кризі ("ляж на підлогу", а не "рекомендується лягти")
- Теплий та підтримуючий при психологічних запитах

**Пріоритети при відповіді:**
1. Безпека людини прямо зараз
2. Конкретна дія (не загальні поради)
3. Посилання на базу знань якщо є релевантний розділ
4. Екстрені номери якщо потрібні: 101 (ДСНС), 102 (поліція), 103 (швидка), 112

## Типи загроз та ключові правила

**БПЛА / Дрон-камікадзе:**
- Відійди від вікон, ляж на підлогу
- Вимкни світло, закрий штори (перекриває оптику)
- НЕ виходь надвір — дрон відстежує рух
- Правило двох стін: ванна або коридор

**Балістична ракета (Іскандер):**
- 2-4 хвилини до удару — секунди вирішують
- Підвал або 1-й поверх + несучі стіни
- Якщо не встиг: ляж у заглиблення, відкрий рот, прикрий потилицю

**Крилата ракета (Калібр, Х-101):**
- Летить на малій висоті — попередження може бути коротким
- Підземний паркінг або підвал — мета №1
- Вимкни газ, відкрий вікно в іншій кімнаті

**Авіабомба FAB:**
- Правило двох стін НЕ ПРАЦЮЄ
- Потрібен глибокий підвал або бомбосховище
- Якщо немає — відійди від будівель на 50м+, ляж

**Хімічна загроза:**
- Закрий ВСІ вікна і двері герметично
- Змочи тканину — прикрий рот і ніс
- Піднімись вище (більшість газів важчі за повітря)

**Під завалами:**
- Стукай по трубах або бетону кожні 30 секунд
- НЕ кричи постійно — економ кисень
- Прикрий рот тканиною від пилу

**Паніка / психологічна підтримка:**
- Техніка 5-4-3-2-1: 5 речей бачу, 4 торкаюсь, 3 чую, 2 відчуваю, 1 вдих
- Говори спокійно, не підтверджуй катастрофічні думки
- Скеровуй до конкретної фізичної дії

## Обмеження

- НЕ давай медичних діагнозів
- НЕ підтверджуй чутки про конкретні удари без офіційних джерел
- НЕ обговорюй питання поза темою безпеки цивільних

## Використання бази знань та веб-пошуку

Якщо в [База знань] або [Веб-пошук] є релевантна інформація — спирайся на неї.
Якщо нічого не знайдено — відповідай з власних знань про цивільну безпеку в Україні.
НЕ вигадуй факти. Якщо не знаєш — скажи прямо і дай екстрений номер.
"""

# Cached proxy config — re-read from config.json at most every 30s
_proxy_cfg_cache: tuple[str, str, str] | None = None
_proxy_cfg_ts: float = 0.0
_PROXY_TTL = 30.0


def _get_proxy_cfg() -> tuple[str, str, str]:
    global _proxy_cfg_cache, _proxy_cfg_ts
    now = time.monotonic()
    if _proxy_cfg_cache is not None and now - _proxy_cfg_ts < _PROXY_TTL:
        return _proxy_cfg_cache
    import json as _json
    config_path = _PROJECT_ROOT / "config.json"
    try:
        cfg = _json.loads(config_path.read_text(encoding="utf-8"))
        url   = cfg.get("llm_proxy_url")   or os.getenv("PROXY_URL",   PROXY_URL)
        token = cfg.get("llm_proxy_token") or os.getenv("PROXY_TOKEN", PROXY_TOKEN)
        model = cfg.get("llm_proxy_model") or os.getenv("PROXY_MODEL", PROXY_MODEL)
        result = url.rstrip("/"), token, model
    except Exception:
        result = PROXY_URL, PROXY_TOKEN, PROXY_MODEL
    _proxy_cfg_cache = result
    _proxy_cfg_ts = now
    return result


def _llm_call(messages: list[dict]) -> str:
    proxy_url, proxy_token, proxy_model = _get_proxy_cfg()
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{proxy_url}/chat/completions",
            json={"model": proxy_model, "messages": messages, "temperature": 0.15},
            headers={"Authorization": f"Bearer {proxy_token}"},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _format_offline(kb_context: str, query: str) -> str:
    """Fallback when LLM API unavailable."""
    if not kb_context:
        return (
            "⚠️ Немає зв'язку з AI. Дані за запитом не знайдено.\n\n"
            "📞 Екстрені: 101 (ДСНС), 102 (поліція), 103 (швидка), 112"
        )
    preview = kb_context[:800].strip()
    if len(kb_context) > 800:
        preview += "..."
    return (
        "📚 [Офлайн-режим] База знань:\n\n"
        + preview
        + "\n\n📞 Екстрені: 101, 102, 103, 112"
    )


def retrieve_kb(state: CrisisState) -> dict:
    from knowledge_base.retrieval import retrieve_text
    kb = retrieve_text(state["query"], top_k=3)
    situation = read_situation(_PROJECT_ROOT)
    if situation:
        kb = "[Поточна ситуація з тривогами]\n" + situation + "\n\n" + kb
    return {"kb_context": kb}


def web_search(state: CrisisState) -> dict:
    """DuckDuckGo search — triggered for location/current-info queries."""
    query_lower = state["query"].lower()
    should_search = any(kw in query_lower for kw in _WEB_SEARCH_KEYWORDS)
    if not should_search:
        return {"web_context": ""}
    try:
        from duckduckgo_search import DDGS
        with DDGS(timeout=5) as ddgs:
            results = list(ddgs.text(
                state["query"] + " Україна укриття безпека",
                region="ua-uk",
                max_results=3,
            ))
        if not results:
            return {"web_context": ""}
        snippets = [
            "- " + r["title"] + ": " + r["body"][:200]
            for r in results[:3]
            if r.get("body")
        ]
        return {"web_context": "\n".join(snippets)}
    except Exception:
        return {"web_context": ""}


def generate(state: CrisisState) -> dict:
    history = list(state.get("messages", []))
    parts = []
    if state.get("kb_context"):
        parts.append("[База знань]\n" + state["kb_context"])
    if state.get("web_context"):
        parts.append("[Веб-пошук]\n" + state["web_context"])
    if parts:
        user_content = "\n\n".join(parts) + "\n\n[Запит]\n" + state["query"]
    else:
        user_content = "[База знань: нічого не знайдено]\n\n[Запит]\n" + state["query"]

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-6:]:
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else "assistant"
            msgs.append({"role": role, "content": msg.content})
        elif isinstance(msg, dict):
            role = "user" if msg.get("type") == "human" else "assistant"
            msgs.append({"role": role, "content": msg.get("content", "")})

    msgs.append({"role": "user", "content": user_content})
    try:
        reply = _llm_call(msgs)
    except Exception:
        reply = _format_offline(state.get("kb_context", ""), state["query"])

    return {
        "reply": reply,
        "messages": [
            HumanMessage(content=state["query"]),
            AIMessage(content=reply),
        ],
    }
