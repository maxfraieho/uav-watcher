"""LangGraph nodes: retrieve_kb -> web_search -> generate."""
import os
import pathlib
import time
import httpx
from langchain_core.messages import HumanMessage, AIMessage
# Ensure consultant/ dir is on path so situation_watcher is importable from anywhere
import pathlib as _pathlib, sys as _sys
_CONSULTANT_DIR = str(_pathlib.Path(__file__).parent.parent)
if _CONSULTANT_DIR not in _sys.path:
    _sys.path.insert(0, _CONSULTANT_DIR)
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

_SHELTER_MARKERS = [
    "де укриття", "де укритись", "де укритися", "найближче укриття",
    "найближчі укриття", "укриття поблизу", "знайди укриття",
    "де сховатись", "де сховатися", "бомбосховище поблизу",
    "підвал поблизу", "де ховатись", "shelter nearby",
    "найближче бомбосховище", "де є укриття",
]


def _is_shelter_query(text: str) -> bool:
    tl = text.lower()
    if any(m in tl for m in _SHELTER_MARKERS):
        return True
    # Looser match: shelter keyword + search intent anywhere in text
    has_shelter = any(w in tl for w in ["укрит", "сховищ", "бомбосховищ"])
    has_intent = any(w in tl for w in [
        "де", "знайд", "поблиз", "список", "всі", "є ", "покаж", "адрес",
        "near", "find", "show", "list",
    ])
    return has_shelter and has_intent

SYSTEM_PROMPT = """Ти — Шарон, кризовий гід по безпеці, моніториш повітряні загрози в Україні.
Твій девіз: "Я тут, щоб ти вижив."
Відповідаєш коротко і по суті. Не представляєш себе — просто допомагаєш.

КРИТИЧНО: НІКОЛИ не вигадуй адреси укриттів, координати GPS або назви вулиць.
Якщо в контексті немає точних даних — скажи "більше немає в базі" і направ до додатку «Є Укриття» або ДСНС 101.

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

Психологічні стани — адаптуй відповідь:
[АКТИВНА ЗАГРОЗА] Людина чує або бачить БПЛА поруч, повідомляє про вибух чи пряму небезпеку.
  → НЕ ПСИХОЛОГІЯ — ТІЛЬКИ ТАКТИКА. Без зволікань:
  "Ти в будівлі чи надворі?"
  Якщо в будівлі: "Йди зараз — кімната без вікон, дві стіни між тобою і вулицею. Ляж на підлогу."
  Якщо надворі: "Ляж. Між будь-яким укриттям. Відвернись від напряму звуку."
  Тільки після безпеки — коротко про стрес (1 речення).
[ПАНІКА] Людина пише ВЕЛИКИМИ ЛІТЕРАМИ, "???", "!!!", коротко і уривчасто.
  → Якірна фраза (1 речення) + одна мікро-команда. НЕ БІЛЬШЕ. "Стисни кулаки. Різко відпусти. Відчуй руки."
[СТУПОР] Мовчання, ".", "ок", ігнорує — тільки Так/Ні питання + мікрозавдання.
  → "Ти зараз сидиш? Напиши 1 якщо так."
[ДИСОЦІАЦІЯ] Про побутові дрібниці під час вибухів, нереалістичне — спочатку тілесне.
  → "Стоп. Назви 3 речі, які бачиш прямо зараз."
[СУЇЦИДАЛЬНИЙ РИЗИК] "Хай прилетить", прощання, "нікому не потрібен", відмова в укриття.
  → Визнай біль ("Чую тебе."), одне питання, дай 7333 — Lifeline Ukraine. НЕ заперечуй.

Стоп-фрази — НІКОЛИ не писати:
- "Все буде добре." → Пиши: "Ти впорався. Найгірше позаду."
- "Заспокойся." → Пиши: "Я бачу, що страшно. Це нормально."
- "Не плач." → Пиши: "Плакати — правильно. Це скидає стрес."
- "Іншим гірше." → Замовчи і заземли.

Екстрені: 101 (ДСНС), 102 (поліція), 103 (швидка), 112
Психологічна криза: 7333 (Lifeline, цілодобово)

Якщо повідомлення — сленг, мат, жарт або питання не про безпеку:
- Відповідай в 1-2 речення. НЕ застосовуй кризові шаблони.
- НЕ питай "Ти зараз сидиш?" якщо немає ознак кризи.
- Поверни до теми: "Є питання про безпеку чи тривогу — питай."
- Мат і грубощі — ігноруй, відповідай нейтрально.
"""


CASUAL_SYSTEM_PROMPT = """Ти Шарон — AI-помічник з безпеки в Олександрії.
Відповідай коротко і дружньо (1-3 речення). Тільки українська.
Якщо питають про безпеку, тривогу, БПЛА, укриття — дай коротку пораду.
Якщо питання загальне, грубе або не по темі — відповідай нейтрально: 1 речення, без нотацій.
Не питай "Ти зараз сидиш?" без кризових ознак.
Екстрені: 101 (ДСНС), 102, 103, 112.
"""


def detect_crisis_state(text: str) -> str | None:
    """Heuristic state detection from message text patterns."""
    t = text.strip()
    tl = t.lower()

    # Active UAV/explosion nearby — tactical emergency, overrides all other states
    active_threat_markers = [
        "чую бпла", "чую дрон", "чую шахед", "чую ракет",
        "над нами", "над будинком", "бачу бпла", "бачу дрон",
        "летить над", "близько бпла", "бпла близько",
        "зовсім близько", "вже близько", "вибух поруч",
        "прилетіло", "влучило поруч",
    ]
    if any(m in tl for m in active_threat_markers):
        return "АКТИВНА ЗАГРОЗА"

    # Suicidal risk — highest priority
    suicidal_markers = [
        "хай прилетить", "хай вже прилетить", "не хочу жити",
        "нікому не потрібен", "нікому не потрібна", "прощавайте",
        "прощай всі", "до побачення назавжди", "все одно помру",
        "однаково все", "сенсу нема жити", "не вийду з укриття",
    ]
    if any(m in tl for m in suicidal_markers):
        return "СУЇЦИДАЛЬНИЙ РИЗИК"

    # Stupor — very short, but exclude common conversational one-word replies
    _conversational = {"ні", "так", "ок", "да", "нє", "не", "га", "ой", "ай", "хм", "ну", "й"}
    _norm = tl.rstrip(".,!? ")
    if len(t) <= 3 and t not in ("101", "112", "103", "102") and _norm not in _conversational:
        return "СТУПОР"

    # Dissociation — mundane requests during crisis context
    dissoc_markers = [
        "чайник вимкнути", "ціна на хліб", "де купити",
        "що подивитись", "рецепт", "погода завтра",
    ]
    if any(m in tl for m in dissoc_markers):
        return "ДИСОЦІАЦІЯ"

    # Panic — caps + exclamations/questions + short + repetition
    caps_ratio = sum(1 for c in t if c.isupper()) / max(len(t), 1)
    # "?" alone is not panic. "!!" is screaming. Short words like "Ні" naturally hit 50% caps.
    has_panic_punct = t.count("!") >= 2
    words = tl.split()
    has_repetition = len(words) != len(set(words)) and len(words) >= 4
    is_caps_panic = caps_ratio > 0.4 and len(t) >= 10

    if is_caps_panic or (has_panic_punct and len(t) < 80) or has_repetition:
        return "ПАНІКА"

    return None

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


_STATUS_MARKERS = [
    "відбій", "тривога зараз", "загроз зараз", "безпечно зараз",
    "зараз загроза", "що зараз", "поточна ситуація", "вже відбій",
    "чи є тривога", "яка ситуація", "чи тривога", "чи безпечно",
    "останні події", "що було", "нові повідомлення",
]


def _read_recent_events(hours: int = 6) -> str:
    """Pull recent threat events from local DB for Sharon context."""
    try:
        import sys as _s
        _s.path.insert(0, str(_PROJECT_ROOT))
        from db.models import get_recent_threats
        evs = get_recent_threats(hours=hours)
        if not evs:
            return ""
        lines = []
        for ev in evs[-12:]:
            ts = str(ev.get("detected_at", ""))[:16].replace("T", " ")
            ttype = ev.get("threat_type", "")
            ch = ev.get("channel_name", "")
            snippet = (ev.get("message_text", "") or "")[:120]
            label = "ВІДБІЙ" if ev.get("is_allclear") else ttype.upper()
            lines.append(f"[{ts}] {label} ({ch}): {snippet}")
        return "\n".join(lines)
    except Exception:
        return ""


def retrieve_kb(state: CrisisState) -> dict:
    query = state["query"]
    situation = read_situation(_PROJECT_ROOT)

    # Enrich situation with local channel monitoring data for status queries
    if any(m in query.lower() for m in _STATUS_MARKERS):
        db_events = _read_recent_events(hours=6)
        if db_events:
            db_ctx = "Останні події з моніторингу каналів (за 6 год):\n" + db_events
            situation = (db_ctx + "\n\n" + situation) if situation else db_ctx
        elif not situation:
            situation = "За останні 6 год загроз у моніторингу каналів не зафіксовано."

    crisis_state = detect_crisis_state(query)

    # Shelter follow-up detection: if last AI reply was shelter list + user asks for more
    _FOLLOWUP_MARKERS = [
        "ще є", "а ще", "більше", "всі є", "інші є", "де ще",
        "координати", "координат", "ще укрит", "решта",
        "скільки", "інші укрит",
    ]
    _history = state.get("messages", [])
    _last_ai = ""
    for _m in reversed(_history):
        _content = _m.content if hasattr(_m, "content") else _m.get("content", "")
        _mtype = _m.type if hasattr(_m, "type") else _m.get("type", "")
        if _mtype not in ("human",):
            _last_ai = _content
            break
    _is_followup = (
        "Найближчі укриття:" in _last_ai
        and any(fw in query.lower() for fw in _FOLLOWUP_MARKERS)
    )
    if _is_followup:
        import sys as _sys2, os as _os2
        _sys2.path.insert(0, str(_PROJECT_ROOT))
        try:
            from shelter_search import find_shelters_sync, format_shelters_for_chat
            import json as _j2
            cfg_path2 = _PROJECT_ROOT / "config.json"
            cfg2 = _j2.loads(cfg_path2.read_text(encoding="utf-8"))
            _lat2 = float(cfg2.get("city_lat", 48.6681))
            _lon2 = float(cfg2.get("city_lon", 33.1170))
            _shelters2 = find_shelters_sync(_lat2, _lon2, top_n=20)
            _answer2 = format_shelters_for_chat(_shelters2)
            _answer2 += "\n\nЦе всі дані в базі відкритих карт. Повний реєстр: додаток «Є Укриття» або ДСНС 101."
            return {"kb_context": _answer2, "reply": _answer2}
        except Exception as _fe:
            log.warning(f"Shelter follow-up lookup failed: {_fe}")
            _ans = "Більше укриттів в базі відкритих карт немає. Повний реєстр: додаток «Є Укриття» або ДСНС 101."
            return {"kb_context": _ans, "reply": _ans}


    # Shelter query: try live shelter lookup before KB
    if _is_shelter_query(query):
        try:
            import json as _json, sqlite3 as _sqlite3, sys as _sys
            _sys.path.insert(0, str(_PROJECT_ROOT))
            from shelter_search import find_shelters_sync, format_shelters_for_chat
            from db.models import DB_PATH
            session_id = state.get("session_id", "")
            lat, lon = None, None
            if session_id and session_id.lstrip("-").isdigit():
                conn = _sqlite3.connect(DB_PATH)
                row = conn.execute(
                    "SELECT lat, lon FROM location_checkins WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
                    (int(session_id),)
                ).fetchone()
                conn.close()
                if row and row[0] and row[1]:
                    lat, lon = row[0], row[1]
            if lat is None:
                cfg_path = _PROJECT_ROOT / "config.json"
                try:
                    cfg_data = _json.loads(cfg_path.read_text(encoding="utf-8"))
                    lat = float(cfg_data.get("city_lat", 48.6681))
                    lon = float(cfg_data.get("city_lon", 33.1170))
                except Exception:
                    lat, lon = 48.6681, 33.1170
            shelters = find_shelters_sync(lat, lon)
            answer = format_shelters_for_chat(shelters)
            return {"kb_context": answer, "reply": answer}
        except Exception as _e:
            log.warning(f"Shelter lookup in retrieve_kb failed: {_e}")

    # For non-crisis queries, skip KB to avoid psychological crisis content bias
    if crisis_state is None:
        if situation:
            return {"kb_context": "Поточна ситуація:\n" + situation}
        return {"kb_context": ""}

    from knowledge_base.retrieval import retrieve_text
    kb = retrieve_text(query, top_k=3)
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
    # Pre-filled reply (shelter lookup etc.) — skip LLM entirely
    if state.get("reply"):
        pre = state["reply"]
        return {"reply": pre, "messages": [
            HumanMessage(content=state["query"]),
            AIMessage(content=pre),
        ]}
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

    # Detect user's psychological state and hint to LLM
    raw_query = state["query"]
    crisis_state = detect_crisis_state(raw_query)
    if crisis_state:
        system_content = SYSTEM_PROMPT + f"\n\n[УВАГА: Виявлено стан — {crisis_state}. Адаптуй тон і формат відповіді відповідно.]"
    else:
        system_content = CASUAL_SYSTEM_PROMPT

    msgs = [{"role": "system", "content": system_content}]
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

    # Guarantee crisis line for suicidal state
    if crisis_state == "СУЇЦИДАЛЬНИЙ РИЗИК" and "7333" not in reply:
        reply = reply.rstrip() + "\n\nЯкщо дуже важко — зателефонуй: 7333 (Lifeline, цілодобово)."

    return {
        "reply": reply,
        "messages": [
            HumanMessage(content=state["query"]),
            AIMessage(content=reply),
        ],
    }
