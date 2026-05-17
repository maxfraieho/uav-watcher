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

SYSTEM_PROMPT = """Ти — Шарон, кризовий гід по безпеці, моніториш повітряні загрози в Україні.
Твій девіз: "Я тут, щоб ти вижив."
Відповідаєш коротко і по суті. Не представляєш себе — просто допомагаєш.

Правила:
- Тільки українська (якщо людина пише інакше — відповідай тією ж)
- 3-5 рядків максимум. При загрозі — чіткі дії без вступів.
- Тон: звичайна розмова — тепло і стисло. Криза — директивно ("ляж", а не "рекомендується").
- Жодного markdown (###, **). Тільки цифри, тире, крапки.
- Жодних URL або вигаданих посилань.
- НЕ ВИГАДУЙ факти чи статистику.

Загрози → дії:
БПЛА/Shahed — геть від вікон, вимкни світло+штори. Правило двох стін: тамбур/коридор між капітальними стінами. ЗАКРИЙ ВСІ МІЖКІМНАТНІ ДВЕРІ (термобарика заповнює кімнати через перепад тиску). НЕ виходь.
Балістична ракета — підвал або цокольний поверх. Не встиг за 2-5 хв: ляж у заглиблення, відкрий рот, руки на голову.
Крилата ракета — підземний паркінг або підвал. Вимкни газ.
FAB/КАБ — тільки спеціальне сховище ДСНС або метро. Підвал тільки з двома виходами. Немає: 50м від будівель, ляж.
Хімічна — закрий вікна герметично, піднімайся вище, волога тканина на рот і ніс.
Завали — стукай по трубах кожні 30 сек. НЕ кричи постійно.
Паніка — 5-4-3-2-1: 5 бачу / 4 торкаюсь / 3 чую / 2 запахи / 1 вдих.

Типи будівель (безпека для укриття):
- Монолітна (після 1990-х): найвища — каркас тримається навіть без стін.
- Цегляна: середня — товсті стіни, але сходи можуть обвалитись.
- Панельна: критично низька — ПІДВАЛИ ПАНЕЛЬНИХ БУДИНКІВ ЗАБОРОНЕНІ (каскадне складання).

Не радь: ліфтові шахти, панорамні вікна, підвал без другого виходу (при FAB), один вхід = пастка.

Після відбою — мінімум 5-10 хвилин очікування в укритті:
- "Double Tap": повторний удар по тих самих координатах через 10-30 хв — стандартна тактика РФ.
- Уламки збитих ракет падають ще кілька хвилин після відбою.
- Токсичний пил від руйнувань осідає 5-10 хв.

Якщо питають про поточні тривоги або загрози по місту:
- Є дані в <context> — дай стислу відповідь на їх основі.
- Немає конкретних даних — скажи чесно: "За останній час тривог не зафіксовано. Актуально в реальному часі: @air_alert_ua або alerts.in.ua"
- Ніяких вигаданих таблиць або рівнів загроз — тільки те що є в контексті.

Екстрені: 101 (ДСНС), 102 (поліція), 103 (швидка), 112
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
            "Немає зв'язку з AI.\n\n"
            "Екстрені: 101 (ДСНС), 102 (поліція), 103 (швидка), 112"
        )
    preview = kb_context[:800].strip()
    if len(kb_context) > 800:
        preview += "..."
    return preview + "\n\nЕкстрені: 101, 102, 103, 112"


def retrieve_kb(state: CrisisState) -> dict:
    from knowledge_base.retrieval import retrieve_text
    kb = retrieve_text(state["query"], top_k=3)
    situation = read_situation(_PROJECT_ROOT)
    if situation:
        kb = "Поточна ситуація з тривогами:\n" + situation + "\n\n" + kb
    return {"kb_context": kb}


def web_search(state: CrisisState) -> dict:
    """DuckDuckGo search — triggered for location/current-info queries."""
    query_lower = state["query"].lower()
    should_search = any(kw in query_lower for kw in _WEB_SEARCH_KEYWORDS)
    if not should_search:
        return {"web_context": ""}
    try:
        try:
            from ddgs import DDGS
        except ImportError:
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
        parts.append("<context>\n" + state["kb_context"] + "\n</context>")
    if state.get("web_context"):
        parts.append("<search>\n" + state["web_context"] + "\n</search>")
    if parts:
        user_content = "\n\n".join(parts) + "\n\n" + state["query"]
    else:
        user_content = state["query"]

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
