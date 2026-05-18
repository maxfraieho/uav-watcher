#!/usr/bin/env python3
"""
UAV threat watcher.
Monitors Telegram channels via Telethon, classifies via AI proxy,
notifies via Telegram Bot API.
"""
import asyncio
import json
import logging
import os
import re
import httpx
from dotenv import load_dotenv
from telethon import TelegramClient, events
from geo_monitor import build_pattern_from_locations

load_dotenv()

# Dedup: suppress duplicates, allow escalation bypass
_last_notify_time: float = 0.0
_last_notify_level: int = 0
_NOTIFY_COOLDOWN_SEC = 90  # seconds between same-or-lower-level alerts
_last_allclear_time: float = 0.0
_ALLCLEAR_COOLDOWN_SEC = 300  # 5 min between all-clear notifications

def _infer_level(text: str, reason: str) -> int:
    """Infer threat level 1-3 from text/reason keywords."""
    combined = (text + " " + reason).lower()
    if any(k in combined for k in ("вибух", "прямо над", "над містом", "над нами", "над головою")):
        return 3
    if any(k in combined for k in ("у місті", "по місту", "в напрямку міста", "тривога у місті")):
        return 2
    return 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)




def score_proximity(text: str, city_keywords: list) -> tuple[int, list]:
    """Score 1-10: how close/severe is this threat to the monitored city."""
    tl = text.lower()
    score = 1  # baseline: passed region filter
    terms = []
    for kw in city_keywords:
        if kw.lower() in tl:
            score += 3
            terms.append(kw)
            break
    for m in ["над містом", "над нами", "над районом", "низько", "поряд", "поруч"]:
        if m in tl:
            score += 3
            terms.append(m)
            break
    for m in ["підліт", "підлітає", "на підльоті", "курсом на", "прямує до"]:
        if m in tl:
            score += 2
            terms.append(m)
            break
    for m in ["прильот", "влучання", "вибух", "влучив", "удар"]:
        if m in tl:
            score += 2
            terms.append(m)
            break
    return min(score, 10), terms


# Keyword patterns for reliable classification WITHOUT AI
_THREAT_PATTERNS = re.compile(
    r'рух БПЛА|підліт БПЛА|підліт ракет|над містом|низько|над районом'
    r'|атака БПЛА|удар БПЛА|прильот|влучання|ракетна атака'
    r'|ударний БПЛА|дрон-камікадзе|Shahed|шахед'
    r'|група БПЛА|роїв БПЛА|хвиля БПЛА'
    r'|ракет[ау] пущено|ракетна небезпека'
    r'|повітряна тривога.*загроза|загроза.*повітряна тривога'
    r'|УВАГА.*БПЛА|БПЛА.*УВАГА',
    re.IGNORECASE | re.UNICODE,
)
_ALLCLEAR_PATTERNS = re.compile(
    r'відбій тривоги|відбій повітряної|тривогу скасовано|тривога скасована'
    r'|кінець тривоги|відбій оголошено',
    re.IGNORECASE | re.UNICODE,
)
_AIRARAID_PATTERNS = re.compile(
    r'повітряна тривога|тривога оголошена|оголошено тривогу|повітряна небезпека',
    re.IGNORECASE | re.UNICODE,
)

def keyword_classify(text: str, city_keywords: list[str]) -> tuple[bool | None, str]:
    """
    Fast keyword pre-classifier.
    Returns (True, reason) for clear threat, (False, reason) for clear allclear,
    or (None, "") if ambiguous — let AI decide.
    """
    tl = text.lower()

    # Explicit all-clear beats everything
    if _ALLCLEAR_PATTERNS.search(text):
        return False, "відбій (ключове слово)"

    # Check if any city keyword is present in the text
    city_hit = any(kw.lower() in tl for kw in city_keywords)

    if city_hit and _THREAT_PATTERNS.search(text):
        return True, f"БПЛА загроза (ключові слова)"

    # Air raid alert for this city — always notify without AI
    if city_hit and _AIRARAID_PATTERNS.search(text):
        return True, "повітряна тривога у місті"

    # No city match but explicit threat — mark as ambiguous for AI
    return None, ""


def build_ai_prompt(text: str, city: str, region: str) -> str:
    return (
        "Ти класифікатор повідомлень про повітряні загрози.\n"
        f"Місто: {city} ({region}).\n"
        "\n"
        "Правила:\n"
        "- threat=true: АКТИВНА загроза БПЛА або ракетна атака прямо зараз\n"
        "- threat=false: відбій тривоги, кінець тривоги, зняття тривоги\n"
        "- ВАЖЛИВО: слова 'відбій', 'відбій тривоги' = threat=false\n"
        "\n"
        "Відповідь ТІЛЬКИ JSON без markdown:\n"
        '{"threat": true, "reason": "БПЛА атака підтверджена"}\n'
        "\n"
        f"Повідомлення:\n{text}"
    )


async def ai_classify(text: str, cfg: dict) -> tuple[bool, str]:
    """Ask AI: is this a UAV threat for the configured city?"""
    city = cfg.get("city", "Олександрія")
    region = cfg.get("city_region", "Кіровоградська область")

    # Fast path: keyword classifier (reliable, no AI needed)
    city_keywords = cfg.get("city_keywords", [city])
    kw_result, kw_reason = keyword_classify(text, city_keywords)
    if kw_result is not None:
        log.info(f"Keyword pre-classify: threat={kw_result}, reason={kw_reason}")
        return kw_result, kw_reason

    prompt = build_ai_prompt(text, city, region)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                cfg.get("llm_proxy_url") or cfg.get("goclaw_url", ""),
                headers={
                    "Authorization": f"Bearer {cfg.get('llm_proxy_token') or cfg.get('goclaw_api_key', '')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg.get("llm_proxy_model") or cfg.get("goclaw_model", ""),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if model adds them
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
            result = json.loads(content)
            return result.get("threat", False), result.get("reason", "")
    except Exception as e:
        log.error(f"AI classify error: {e}")
        return False, ""


async def send_notification(text: str, reason: str, cfg: dict, channel_name: str = ""):
    """Send alert via Telegram Bot API (with dedup cooldown)."""
    global _last_notify_time, _last_notify_level
    import time
    now = time.monotonic()
    elapsed = now - _last_notify_time
    level = _infer_level(text, reason)
    if elapsed < _NOTIFY_COOLDOWN_SEC and level <= _last_notify_level:
        log.info(f"[dedup] suppressed L{level}<=L{_last_notify_level} elapsed={elapsed:.0f}s: {reason}")
        return
    if level > _last_notify_level:
        log.info(f"[dedup] escalation L{_last_notify_level}→L{level}, bypass cooldown")
    _last_notify_time = now
    _last_notify_level = level
    city = cfg.get("city", "ВашеМісто").upper()
    safe_text = text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
    # Level-based formatting
    if level >= 3:
        header = f"🔴 *КРИТИЧНО — {city}*"
        action = "\n\n⚠️ _Негайно в укриття!_"
    elif level == 2:
        header = f"🚨 *ЗАГРОЗА — {city}*"
        action = ""
    else:
        header = f"⚠️ *МОНІТОРИНГ — {city}*"
        action = ""
    # Channel citation for level 2+
    if level >= 2 and channel_name:
        cite = f"\n📡 _{channel_name}:_\n{safe_text}"
    else:
        cite = f"\n{safe_text}"
    msg = f"{header}{cite}\n\n_Аналіз: {reason}_{action}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                json={
                    "chat_id": cfg["notify_chat_id"],
                    "text": msg,
                    "parse_mode": "Markdown",
                },
            )
            resp.raise_for_status()
            log.info(f"Notification sent L{level}: {reason}")
    except Exception as e:
        log.error(f"Send notification error: {e}")


async def send_allclear_notification(cfg: dict):
    """Send all-clear with 5-min dedup; resets threat level so next threat notifies immediately."""
    global _last_notify_time, _last_notify_level, _last_allclear_time
    import time as _t
    now = _t.monotonic()
    if now - _last_allclear_time < _ALLCLEAR_COOLDOWN_SEC:
        log.info(f"[dedup] all-clear suppressed, elapsed={now - _last_allclear_time:.0f}s")
        return
    _last_allclear_time = now
    _last_notify_level = 0      # reset so next threat notifies at any level
    _last_notify_time = 0.0     # reset threat cooldown too
    city = cfg.get("city", "ВашеМісто").upper()
    msg = f"✅ *ВІДБІЙ — {city}*\n\nТривогу знято."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                json={"chat_id": cfg["notify_chat_id"], "text": msg, "parse_mode": "Markdown"},
            )
            resp.raise_for_status()
            log.info("All-clear notification sent")
    except Exception as e:
        log.error(f"Send all-clear error: {e}")


async def main():
    from db.models import init_db
    init_db()

    cfg = load_config()
    city = cfg.get("city", "Олександрія")
    keywords = cfg.get("city_keywords", [city])
    city_pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    LOCKED = [-1001223955273]
    user_channels = cfg.get("channels", [])
    channels = list(set(LOCKED + user_channels))

    log.info(f"City: {city} | Keywords: {keywords}")
    log.info(f"Channels: {channels}")
    log.info(f"AI model: {cfg.get('llm_proxy_model') or cfg.get('goclaw_model','?')} via {cfg.get('llm_proxy_url') or cfg.get('goclaw_url','?')}")

    client = TelegramClient(
        os.path.join(os.path.dirname(__file__), "uav_watcher"),
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"],
    )

    # Auto-derive region keyword from city_region adjective suffix
    # "Харківська область" -> "Харків"; "Донецька" -> "Донецьк"
    city_region = cfg.get("city_region", "")
    region_word = city_region.split()[0] if city_region else ""
    if region_word.endswith("ська"):
        region_word = region_word[:-4]
    elif region_word.endswith("зька"):
        region_word = region_word[:-4]
    elif region_word.endswith("ька"):
        region_word = region_word[:-1]
    default_region_kw = [region_word] if region_word else []
    region_keywords = cfg.get("region_keywords", default_region_kw)
    # DB path for location check-ins (same dir as session file)
    _db_path = os.path.join(os.path.dirname(__file__), "data", "families.db")

    # Initial static pattern (fallback before Overpass loads)
    _kw_all = [k for k in (keywords + (region_keywords or [])) if k]
    _static_pattern = re.compile(
        "|".join(re.escape(k) for k in _kw_all) if _kw_all else r"\bx\B",
        re.IGNORECASE | re.UNICODE,
    )
    # Mutable container — async tasks update _pattern_ref[0]
    _pattern_ref = [_static_pattern]

    async def _refresh_pattern():
        """Rebuild region pattern from all active family member GPS positions."""
        try:
            new_pat = await build_pattern_from_locations(_db_path, _kw_all)
            _pattern_ref[0] = new_pat
            log.info("Region pattern refreshed from live locations")
        except Exception as exc:
            log.error(f"Region pattern refresh error: {exc}")

    async def _periodic_refresh():
        """Refresh region pattern every 30 minutes."""
        while True:
            await asyncio.sleep(1800)
            await _refresh_pattern()

    def region_pattern_search(text: str) -> bool:
        return bool(_pattern_ref[0].search(text))

    ai_sem = asyncio.Semaphore(1)

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return
        if not region_pattern_search(text):
            return
        # Identify source channel
        chat = await event.get_chat()
        ch_name = getattr(chat, "title", str(event.chat_id))
        log.info(f"Keyword matched [{ch_name}]: {text[:100]}...")
        # Score proximity before AI classification
        prox_score, prox_terms = score_proximity(text, keywords)
        async with ai_sem:
            is_threat, reason = await ai_classify(text, cfg)
        # Classify all_clear
        is_allclear = (not is_threat) and bool(_ALLCLEAR_PATTERNS.search(text))
        # Persist to threat_events for statistics and consultant context
        try:
            from db.models import save_threat_event
            save_threat_event(
                channel_id=event.chat_id,
                channel_name=ch_name,
                text=text,
                threat_type="uav" if is_threat else ("allclear" if is_allclear else "info"),
                proximity_score=prox_score,
                location_terms=prox_terms,
                is_allclear=is_allclear,
            )
        except Exception as _db_err:
            log.error(f"threat_event DB write failed: {_db_err}")
        if is_threat:
            log.warning(f"THREAT [prox={prox_score}/10, terms={prox_terms}]: {reason}")
            await send_notification(text, reason, cfg, channel_name=ch_name)
        elif is_allclear:
            log.info(f"ALL-CLEAR: {reason}")
            await send_allclear_notification(cfg)
        else:
            log.info(f"No threat: {reason}")

    await client.start(phone=os.environ["TELEGRAM_PHONE"])

    # Join all monitored channels so Telegram delivers updates to this account
    from telethon.tl.functions.channels import JoinChannelRequest
    for ch_id in channels:
        try:
            entity = await client.get_entity(ch_id)
            if hasattr(entity, 'username') and entity.username:
                await client(JoinChannelRequest(entity))
                log.info(f"Joined channel: {getattr(entity, 'title', ch_id)}")
        except Exception as e:
            log.warning(f"Could not join {ch_id}: {e}")

    # Initial region pattern refresh from DB locations
    await _refresh_pattern()
    asyncio.create_task(_periodic_refresh())

    async def _periodic_shelter_update():
        """Оновлювати кеш укриттів і KB-файл кожні 24 год."""
        from shelter_search import refresh_shelters_kb
        project_root = os.path.dirname(os.path.abspath(__file__))
        s_lat = float(cfg.get("city_lat", 48.6681))
        s_lon = float(cfg.get("city_lon", 33.1170))
        await refresh_shelters_kb(project_root, s_lat, s_lon, user_client=client)
        while True:
            await asyncio.sleep(86400)
            await refresh_shelters_kb(project_root, s_lat, s_lon, user_client=client)

    asyncio.create_task(_periodic_shelter_update())


    # --- STARTUP CATCHUP: fetch last 4h from channels to fill crash gaps ---
    async def _catchup_history():
        """On startup, process recent channel history missed during downtime."""
        import time as _time
        from db.models import save_threat_event as _save
        cutoff_ts = _time.time() - 4 * 3600  # 4 hours ago
        log.info("[catchup] Scanning last 4h of channel history...")
        total = 0
        for ch_id in channels:
            try:
                async for msg in client.iter_messages(ch_id, limit=200):
                    if not msg.text:
                        continue
                    if msg.date.timestamp() < cutoff_ts:
                        break
                    if not region_pattern_search(msg.text):
                        continue
                    try:
                        chat = await client.get_entity(ch_id)
                        ch_name = getattr(chat, "title", str(ch_id))
                    except Exception:
                        ch_name = str(ch_id)
                    is_allclear = bool(_ALLCLEAR_PATTERNS.search(msg.text))
                    is_threat_kw = any(k in msg.text.lower() for k in (
                        "повітряна тривога", "воздушна тревога", "тривога", "загроза",
                        "бпла", "ракет", "вибух", "обстріл",
                    ))
                    msg_ts = msg.date.strftime("%Y-%m-%d %H:%M:%S")
                    _save(
                        channel_id=ch_id,
                        channel_name=ch_name,
                        text=msg.text,
                        threat_type="allclear" if is_allclear else ("uav" if is_threat_kw else "info"),
                        proximity_score=5,
                        location_terms=[],
                        is_allclear=is_allclear,
                        detected_at=msg_ts,
                    )
                    total += 1
            except Exception as _ce:
                log.warning(f"[catchup] channel {ch_id}: {_ce}")
        log.info(f"[catchup] Done. Inserted {total} missed events.")

    asyncio.create_task(_catchup_history())

    log.info(f"UAV watcher started. Watching {len(channels)} channel(s). Press Ctrl+C to stop.")

    # --- OFFICIAL API POLLER (Task 0.3) ---
    if cfg.get('alerts_ua_token'):
        from integrations.alerts_ua import AlertsUAPoller

        async def on_official_alert(alert_type, location, started_at):
            msg = f"🔴 *ОФІЦІЙНА ТРИВОГА* [{location}]\nТип: {alert_type}\nПочаток: {started_at}"
            await send_notification(msg, f"Офіційна тривога: {alert_type}", cfg)

        poller = AlertsUAPoller(
            token=cfg['alerts_ua_token'],
            region=cfg['city_region'],
            callback=on_official_alert
        )
        asyncio.ensure_future(poller.poll_loop())
        log.info("alerts.in.ua official poller started in background")

    # --- CRISIS CHATBOT BOT COMMANDS (Task 0.1) ---
    from bot.crisis_templates import TEMPLATES, THREAT_KEYBOARD, GROUNDING_STEPS
    from telethon.tl.types import KeyboardButtonCallback, ReplyKeyboardMarkup, KeyboardButtonRow, KeyboardButton as KBButton

    bot_app = TelegramClient(
        os.path.join(os.path.dirname(__file__), "bot"),
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"]
    )

    @bot_app.on(events.NewMessage(pattern='/help|/допомога|/що_робити'))
    async def cmd_help(event):
        buttons = [
            [KeyboardButtonCallback(b["text"], b["callback_data"].encode()) for b in row]
            for row in THREAT_KEYBOARD
        ]
        await event.respond(
            "🛡 *Sharon — Кризовий консультант*\n\nОберіть тип загрози:",
            buttons=buttons,
            parse_mode='md'
        )

    @bot_app.on(events.CallbackQuery(pattern=b'crisis_(.+)'))
    async def handle_crisis_callback(event):
        threat_key = event.data.decode().replace('crisis_', '')
        if threat_key in TEMPLATES:
            await event.edit(TEMPLATES[threat_key]["text"], parse_mode='md')
        await event.answer()

    @bot_app.on(events.NewMessage(pattern='/заземлення|/calm|/паніка'))
    async def cmd_grounding(event):
        await event.respond(
            "🧘 *Техніка заземлення — зупинись і читай повільно:*\n\nЦе допоможе тобі повернутись у теперішній момент.",
            parse_mode='md'
        )
        for step in GROUNDING_STEPS:
            await asyncio.sleep(8)
            await event.respond(step)

    @bot_app.on(events.NewMessage(pattern='/status|/статус|/безпечно'))
    async def cmd_status(event):
        import datetime
        now = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        sender = await event.get_sender()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Користувач"
        await event.respond(f"✅ Статус оновлено: {now}\n\nНадсилаємо сповіщення...")
        msg = f"✅ *{name}* в безпеці\n🕐 {now}"
        async with httpx.AsyncClient(timeout=10.0) as hclient:
            await hclient.post(
                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                json={'chat_id': cfg['notify_chat_id'], 'text': msg, 'parse_mode': 'Markdown'}
            )

    CORRECTIONS_PATH = os.path.join(os.path.dirname(__file__), "consultant", "knowledge", "corrections.md")

    @bot_app.on(events.NewMessage(pattern=r'^/correct\s+(.*)'))
    async def cmd_correct(event):
        """Save a Sharon response correction to the KB."""
        import datetime
        correction_text = event.pattern_match.group(1).strip()
        if not correction_text:
            await event.respond("Використання: /correct <правильна відповідь>")
            return
        # Extract context from replied-to message if available
        context_note = ""
        if event.is_reply:
            replied = await event.get_reply_message()
            if replied and replied.text:
                context_note = f"Помилкова відповідь: {replied.text[:300]}\n"
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"\n## Виправлення {ts}\n"
            f"{context_note}"
            f"Правильно: {correction_text}\n"
        )
        try:
            with open(CORRECTIONS_PATH, "a", encoding="utf-8") as cf:
                cf.write(entry)
            await event.respond(f"\u2705 Збережено в базу знань.")
            log.info(f"Correction saved: {correction_text[:80]}")
        except Exception as ex:
            await event.respond(f"\u274c Помилка: {ex}")

    await bot_app.start(bot_token=cfg['bot_token'])
    log.info("Bot command handlers started.")

    # Register bot command menu (shown when user types "/" in Telegram)
    try:
        async with httpx.AsyncClient(timeout=10) as _hc:
            await _hc.post(
                f"https://api.telegram.org/bot{cfg['bot_token']}/setMyCommands",
                json={
                    "commands": [
                        {"command": "shelter",       "description": "🏠 Найближчі укриття"},
                        {"command": "ok",            "description": "✅ Я в порядку"},
                        {"command": "sos",           "description": "🆘 Потрібна допомога"},
                        {"command": "checkin",       "description": "📍 Зберегти моє місцезнаходження"},
                        {"command": "family_status", "description": "👨‍👩‍👧 Статус родини"},
                        {"command": "family_create", "description": "Створити сімейну групу"},
                        {"command": "family_join",   "description": "Приєднатись до групи"},
                    ]
                },
            )
        log.info("Bot command menu registered (setMyCommands)")
    except Exception as _e:
        log.warning(f"setMyCommands failed: {_e}")

    # --- SHARON TELEGRAM CHAT ---
    _MAIN_KEYBOARD = ReplyKeyboardMarkup(
        rows=[
            KeyboardButtonRow(buttons=[
                KBButton(text="📍 Укриття поруч"),
                KBButton(text="⚠️ Загрози зараз"),
            ]),
            KeyboardButtonRow(buttons=[
                KBButton(text="📋 Типи загроз"),
                KBButton(text="🧘 Заземлення"),
            ]),
        ],
        resize=True,
        persistent=True,
    )

    @bot_app.on(events.NewMessage(pattern=r'^/start'))
    async def cmd_start(event):
        await event.respond(
            "👋 Привіт! Я *Sharon* — кризовий консультант.\n\n"
            "Надішли питання або скористайся кнопками нижче.\n\n"
            "📍 *Укриття поруч* — надішли геолокацію\n"
            "⚠️ *Загрози зараз* — поточна ситуація\n"
            "📋 *Типи загроз* — інструкції по кожному типу\n"
            "🧘 *Заземлення* — техніка при паніці",
            buttons=_MAIN_KEYBOARD,
            parse_mode='md'
        )

    @bot_app.on(events.NewMessage(pattern=r'^📋 Типи загроз$'))
    async def cmd_threat_menu_btn(event):
        inline_buttons = [
            [KeyboardButtonCallback(b["text"], b["callback_data"].encode()) for b in row]
            for row in THREAT_KEYBOARD
        ]
        await event.respond("🛡 *Оберіть тип загрози:*", buttons=inline_buttons, parse_mode='md')
        raise events.StopPropagation

    @bot_app.on(events.NewMessage(pattern=r'^🧘 Заземлення$'))
    async def cmd_grounding_btn(event):
        await event.respond(
            "🧘 *Техніка заземлення — зупинись і читай повільно:*\n\nЦе допоможе тобі повернутись у теперішній момент.",
            parse_mode='md'
        )
        for step in GROUNDING_STEPS:
            await asyncio.sleep(8)
            await event.respond(step)
        raise events.StopPropagation

    @bot_app.on(events.NewMessage(
        func=lambda e: e.is_private and bool(e.text) and not e.text.startswith('/')
    ))
    async def sharon_private_chat(event):
        """Route any private text message to Sharon consultant."""
        user_text = event.text.strip()
        session_id = str(event.sender_id)
        # Shelter query without geolocation → ask for GPS
        if any(kw in user_text.lower() for kw in _SHELTER_KEYWORDS):
            await event.respond(_SHELTER_GEO_MSG, parse_mode='md')
            return
        try:
            async with httpx.AsyncClient(timeout=30.0) as hc:
                resp = await hc.post(
                    "http://localhost:8770/chat",
                    json={"message": user_text, "session_id": session_id},
                )
                resp.raise_for_status()
                reply = resp.json().get("reply", "")
        except Exception as e:
            log.error(f"Sharon chat error: {e}")
            reply = "Вибач, зараз не можу відповісти.\nЕкстрені: 101 (ДСНС), 112"
        if reply:
            await event.respond(reply)

    # --- FAMILY HANDLERS (Task 1.2) ---
    from family.bot_handlers import register_family_handlers
    register_family_handlers(bot_app, cfg, user_client=client)

    # --- SHELTER COMMAND ---
    _SHELTER_GEO_MSG = (
        "📍 *Де ти зараз?*\n\n"
        "Надішли свою геолокацію — знайду найближчі укриття саме для тебе.\n\n"
        "*Як надіслати:*\n"
        "• Натисни 📎 (скрепка) → *Геолокація*\n"
        "• або: «+» → *Місцезнаходження* → *Поточне місцезнаходження*\n\n"
        "_Без точної геолокації покажу укриття лише від центру міста — вони можуть бути далеко від тебе._"
    )
    _SHELTER_KEYWORDS = (
        # Short partials catch typos and variants
        "укрит", "укрот", "укрыт",          # укриття + typos
        "сховищ", "схованк", "сховат",       # сховище, сховатись
        "бомбосховищ", "/shelter",
        "де захист", "де безпечн",
    )

    @bot_app.on(events.NewMessage(pattern=r'^/shelter'))
    async def cmd_shelter(event):
        await event.respond(_SHELTER_GEO_MSG, parse_mode='md')

    # --- LOCATION TRACKER (Task 2.1) ---
    from rescue.location_tracker import register_location_handlers
    register_location_handlers(bot_app, cfg, user_client=client)

    await asyncio.gather(
        client.run_until_disconnected(),
        bot_app.run_until_disconnected()
    )


if __name__ == "__main__":
    asyncio.run(main())
