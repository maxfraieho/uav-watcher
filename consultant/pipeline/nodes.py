"""LangGraph nodes: retrieve_kb -> web_search -> generate."""
import logging
import os
import pathlib
import time
import httpx

log = logging.getLogger(__name__)
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
    "де ", "найближч", "бомбосховищ", "укрит",
    "новин", "адрес", "знайти", "поруч", "where", "shelter",
    "nearest", "news", "address", "find", "nearby",
]

_SHELTER_MARKERS = [
    "де укриття", "де укритись", "де укритися", "найближче укриття",
    "найближчі укриття", "укриття поблизу", "знайди укриття",
    "де сховатись", "де сховатися", "бомбосховище поблизу",
    "підвал поблизу", "де ховатись", "shelter nearby",
    "найближче бомбосховище", "де є укриття",
    # Partial/typo variants
    "де укр", "де схов", "де безпечн", "де захист",
]


_SHELTER_FUZZY_WORDS = ["укриття", "укритись", "укритися", "сховище", "бомбосховище"]

# Domain vocabulary for global typo normalization (all queries)
_QUERY_VOCAB = (
    "укриття", "укритись", "укритися", "сховище", "бомбосховище",
    "сховатись", "сховатися", "захист",
    "тривога", "відбій", "ракета", "загроза", "загрози",
    "ситуація", "обстановка", "небезпека",
    "зараз", "поточний", "нині",
    "знайди", "покажи", "виведи",
    "найближче",
)


def _normalize_query(text: str) -> str:
    """Normalize common typos in query words using fuzzy vocab matching.

    Prefers vocab words closest in length to prevent зарза→загроза (prefer зараз).
    Only normalizes words ≥5 chars to avoid false positives on short words.
    """
    import difflib
    words = text.split()
    result = []
    for word in words:
        clean = word.strip("?!.,;:")
        if len(clean) < 5:
            result.append(word)
            continue
        matches = difflib.get_close_matches(clean.lower(), _QUERY_VOCAB, n=3, cutoff=0.75)
        if matches:
            best = min(matches, key=lambda m: abs(len(m) - len(clean)))
            if clean[0].isupper():
                best = best[0].upper() + best[1:]
            punct = word[len(clean):]
            result.append(best + punct)
        else:
            result.append(word)
    return " ".join(result)


def _shelter_fuzzy(text: str, threshold: float = 0.75) -> bool:
    """Fuzzy match: catches one-letter typos like унриття→укриття."""
    import difflib
    words = [w.strip("?!.,") for w in text.lower().split()]
    for word in words:
        if len(word) < 5:
            continue
        for sw in _SHELTER_FUZZY_WORDS:
            if abs(len(word) - len(sw)) > 2:
                continue
            if difflib.SequenceMatcher(None, word, sw).ratio() >= threshold:
                return True
    return False


def _is_shelter_query(text: str) -> bool:
    tl = text.lower()
    if any(m in tl for m in _SHELTER_MARKERS):
        return True
    # Fuzzy: catches 1-char typos (унриття, укрития, сховиче, etc.)
    if _shelter_fuzzy(tl):
        return True
    # Shelter stem match
    _shelter_stems = ["укрит", "укрот", "укрыт", "сховищ", "схованк",
                      "сховат", "бомбосховищ", "де захист", "де безпечн"]
    has_shelter = any(w in tl for w in _shelter_stems)
    has_intent = any(w in tl for w in [
        "де", "знайд", "поблиз", "список", "всі", "є ", "покаж", "адрес",
        "near", "find", "show", "list", "куди", "коли", "як",
    ])
    if has_shelter and len(tl.strip()) < 25:
        return True
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


def _casual_system_prompt(lang: str = "uk") -> str:
    import json as _j
    try:
        _cfg = _j.loads((_PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
        _city = _cfg.get("city", "Олександрія")
    except Exception:
        _city = "Олександрія"
    _LANG_RULES = {
        "uk": "Відповідай ТІЛЬКИ українською мовою.",
        "en": "ALWAYS respond in English only. Never use Ukrainian.",
        "de": "Antworte NUR auf Deutsch. Verwende kein Ukrainisch.",
        "fr": "Réponds UNIQUEMENT en français. N'utilise pas l'ukrainien.",
        "pl": "Odpowiadaj TYLKO po polsku. Nie używaj ukraińskiego.",
    }
    _lang_rule = _LANG_RULES.get(lang, _LANG_RULES["uk"])
    return (
        f"Ти Шарон — AI-помічник з безпеки в {_city}.\n"
        f"{_lang_rule}\n"
        "Відповідай коротко і дружньо (1-3 речення).\n"
        "Якщо питають про безпеку, тривогу, БПЛА, укриття — дай коротку пораду.\n"
        "Якщо питання загальне або не по темі — відповідай нейтрально: 1 речення, без нотацій.\n"
        "Не питай \"Ти зараз сидиш?\" без кризових ознак.\n"
        "Екстрені: 101 (ДСНС), 102, 103, 112.\n"
    )
CASUAL_SYSTEM_PROMPT = _casual_system_prompt  # kept for backward compat


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
    # Explicit status queries
    "відбій", "тривога зараз", "загроз зараз", "безпечно зараз",
    "зараз загроза", "що зараз", "поточна ситуація", "вже відбій",
    "чи є тривога", "яка ситуація", "чи тривога", "чи безпечно",
    "останні події", "що було", "нові повідомлення",
    # Ukrainian case variants
    "по загроз", "загрозам", "обстановка", "обстановку", "обстановці",
    "по тривог", "яка тривога", "яка обстановка", "що відбув",
    "що сталос", "що трапил", "як зараз", "що по ", "поточн",
]


# Cached city keywords — mirrors _get_proxy_cfg() pattern, TTL 30s
_city_kw_cache: list | None = None
_city_kw_ts: float = 0.0
_CITY_KW_TTL = 30.0


def _get_city_keywords() -> list[str]:
    """Return current city_keywords from config.json (cached 30s)."""
    global _city_kw_cache, _city_kw_ts
    now = time.monotonic()
    if _city_kw_cache is not None and now - _city_kw_ts < _CITY_KW_TTL:
        return _city_kw_cache
    import json as _json
    config_path = _PROJECT_ROOT / "config.json"
    try:
        cfg = _json.loads(config_path.read_text(encoding="utf-8"))
        kws = cfg.get("city_keywords") or []
        city = cfg.get("city", "")
        if city and city not in kws:
            kws = [city] + kws
        result = [k.lower() for k in kws if k]
    except Exception:
        result = []
    _city_kw_cache = result
    _city_kw_ts = now
    return result


def _read_recent_events(hours: int = 6) -> str:
    """Pull recent threat events from local DB for Sharon context."""
    try:
        import sys as _s
        _s.path.insert(0, str(_PROJECT_ROOT))
        from db.models import get_recent_threats
        evs = get_recent_threats(hours=hours)
        if not evs:
            return ""
        # Filter to events relevant to current city
        city_kws = _get_city_keywords()
        if city_kws:
            evs = [e for e in evs
                   if any(k in (e.get('message_text') or '').lower() for k in city_kws)
                   or any(k in (e.get('channel_name') or '').lower() for k in city_kws)]
        if not evs:
            return ""
        # Chronological order (oldest→newest) so LLM reads timeline correctly
        recent = list(reversed(evs[:12]))
        lines = []
        for ev in recent:
            ts = str(ev.get("detected_at", ""))[:16].replace("T", " ")
            ttype = ev.get("threat_type", "")
            ch = ev.get("channel_name", "")
            snippet = (ev.get("message_text", "") or "")[:120]
            label = "ВІДБІЙ" if ev.get("is_allclear") else ttype.upper()
            lines.append(f"[{ts}] {label} ({ch}): {snippet}")
        # Post-strike summaries ("ЗБИТО/ПОДАВЛЕНО X БПЛА") arrive AFTER all-clear and
        # must not override it — skip them when determining current state
        def _is_poststrike(ev):
            t = (ev.get("message_text") or "").lower()
            return any(p in t for p in [
                "збито", "подавлено",          # "ЗБИТО/ПОДАВЛЕНО X БПЛА"
                "у ніч на", "за ніч", "минулої ночі", "за добу",
                "за даними командування",       # Air Force post-attack reports
                "завдали комбінованого",        # past-tense attack description
                "завдав комбінованого",
                "напрямок удару",               # attack direction summary
                "ракет наземного базування",    # technical summary language
                "радіотехнічні війська",        # air force technical report
            ])

        def _is_drill(ev):
            t = (ev.get("message_text") or "").lower()
            return any(p in t for p in [
                "навчання",       # планові/тактичні навчання
                "навчальн",       # навчальна тривога
                "тренувальн",     # тренувальна тривога
                "проводитимуть",  # "проводитимуться тактичні навчання"
                "навчальна стрільба",
                "стрільби",
            ])

        cur = "Даних про стан тривоги немає"
        for ev in reversed(recent):
            if ev.get("is_allclear"):
                cur = "ВІДБІЙ — активної тривоги немає"
                break
            if _is_drill(ev):
                continue
            if not _is_poststrike(ev):
                cur = f"ТРИВОГА АКТИВНА ({ev.get('threat_type','').upper()})"
                break
        lines.append(f"\n>> Поточний стан: {cur}")
        return "\n".join(lines)
    except Exception:
        return ""


def retrieve_kb(state: CrisisState) -> dict:
    query = _normalize_query(state["query"])
    situation = read_situation(_PROJECT_ROOT)

    # Always inject very recent events (2h) so any query has threat context
    recent_2h = _read_recent_events(hours=2)
    if recent_2h:
        recent_prefix = "⚡ Останні події з моніторингу каналів (2 год):\n" + recent_2h
        situation = (recent_prefix + "\n\n" + situation) if situation else recent_prefix

    # Enrich with extended 6h history for explicit status queries
    if any(m in query.lower() for m in _STATUS_MARKERS):
        db_events = _read_recent_events(hours=6)
        if db_events:
            db_ctx = "Останні події з моніторингу каналів (за 6 год):\n" + db_events
            if not recent_2h:
                situation = (db_ctx + "\n\n" + situation) if situation else db_ctx
        elif not situation and not recent_2h:
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
            _lang2 = state.get("lang", "uk") or "uk"
            _shelters2 = find_shelters_sync(_lat2, _lon2, top_n=20)
            _answer2 = format_shelters_for_chat(_shelters2, lang=_lang2, city_center_fallback=True)
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
            # Web session (UUID) — no GPS available, redirect to Telegram bot
            _is_tg_session = session_id and session_id.lstrip("-").isdigit()
            if not _is_tg_session:
                try:
                    _cfg_data = _json.loads((_PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
                    _bot_uname = _cfg_data.get("bot_username", "")
                except Exception:
                    _bot_uname = ""
                _bot_link = f"[@{_bot_uname}](https://t.me/{_bot_uname})" if _bot_uname else "нашому Telegram-боту"
                _redirect = (
                    "📍 Для пошуку укриттів поруч мені потрібна твоя геолокація.\n\n"
                    f"Напиши {_bot_link} — там натисни 📎 → *Геолокація* → *Поточне місцезнаходження*.\n\n"
                    "Знайду найближчі укриття точно для твого місця, а не від центру міста."
                )
                return {"kb_context": _redirect, "reply": _redirect}
            if session_id and session_id.lstrip("-").isdigit():
                conn = _sqlite3.connect(DB_PATH)
                row = conn.execute(
                    "SELECT lat, lon FROM location_checkins WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
                    (int(session_id),)
                ).fetchone()
                conn.close()
                if row and row[0] and row[1]:
                    lat, lon = row[0], row[1]
            _city_fallback = (lat is None)
            if lat is None:
                cfg_path = _PROJECT_ROOT / "config.json"
                try:
                    cfg_data = _json.loads(cfg_path.read_text(encoding="utf-8"))
                    lat = float(cfg_data.get("city_lat", 48.6681))
                    lon = float(cfg_data.get("city_lon", 33.1170))
                except Exception:
                    lat, lon = 48.6681, 33.1170
            _lang = state.get("lang", "uk") or "uk"
            shelters = find_shelters_sync(lat, lon)
            answer = format_shelters_for_chat(shelters, lang=_lang, city_center_fallback=_city_fallback)
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
    # Channel feed summary from summarizer (patch)
    try:
        from memory.summarizer import read_channel_summary
        channel_summary = read_channel_summary()
        if channel_summary:
            kb = "[Зведення з каналів моніторингу]\n" + channel_summary + "\n\n" + kb
    except Exception:
        pass

    return {"kb_context": kb}


def web_search(state: CrisisState) -> dict:
    """DuckDuckGo search — triggered for location/current-info queries."""
    query_lower = state["query"].lower()
    # Status queries rely only on local DB — DuckDuckGo returns stale news
    if any(m in query_lower for m in _STATUS_MARKERS):
        return {"web_context": ""}
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
                state["query"] + " Україна" + (" укриття безпека" if _is_shelter_query(query_lower) else ""),
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
    _lang = state.get("lang", "uk") or "uk"
    try:
        from bot.i18n import get as _t_bot
        _lang_instr = _t_bot(_lang, "llm_lang_instruction")
    except Exception:
        _lang_instr = ""
    if crisis_state:
        system_content = _lang_instr + SYSTEM_PROMPT.replace("Тільки українська (якщо людина пише інакше — відповідай тією ж)", "") + f"\n\n[УВАГА: Виявлено стан — {crisis_state}. Адаптуй тон і формат відповіді відповідно.]"
    else:
        system_content = _lang_instr + _casual_system_prompt(_lang)

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
    except Exception as _e:
        log.warning(f"[generate] LLM call failed: {_e}")
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
