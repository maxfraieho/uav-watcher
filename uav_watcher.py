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
                cfg["goclaw_url"],
                headers={
                    "Authorization": f"Bearer {cfg['goclaw_api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg["goclaw_model"],
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


async def send_notification(text: str, reason: str, cfg: dict):
    """Send alert via Telegram Bot API."""
    city = cfg.get("city", "Олександрія").upper()
    # Escape special markdown chars in original text
    safe_text = text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
    msg = (
        f"\U0001f6a8 *ЗАГРОЗА БПЛА — {city}*\n\n"
        f"{safe_text}\n\n"
        f"_AI: {reason}_"
    )
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
            log.info(f"Notification sent: {reason}")
    except Exception as e:
        log.error(f"Send notification error: {e}")


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
    log.info(f"AI model: {cfg['goclaw_model']} via {cfg['goclaw_url']}")

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
        if is_threat:
            log.warning(f"THREAT [prox={prox_score}/10, terms={prox_terms}]: {reason}")
            await send_notification(text, reason, cfg)
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
    from telethon.tl.types import KeyboardButtonCallback

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
            "🛡 *UAV Watcher — Кризовий консультант*\n\nОберіть тип загрози:",
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

    await bot_app.start(bot_token=cfg['bot_token'])
    log.info("Bot command handlers started.")

    # --- FAMILY HANDLERS (Task 1.2) ---
    from family.bot_handlers import register_family_handlers
    register_family_handlers(bot_app, cfg, user_client=client)
    log.info("Family bot handlers registered.")

    # --- LOCATION TRACKER (Task 2.1) ---
    from rescue.location_tracker import register_location_handlers
    register_location_handlers(bot_app, cfg)
    log.info("Location tracker handlers registered.")

    await asyncio.gather(
        client.run_until_disconnected(),
        bot_app.run_until_disconnected()
    )


if __name__ == "__main__":
    asyncio.run(main())
