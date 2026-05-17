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
    region_pattern = re.compile(
        "|".join(re.escape(k) for k in (keywords + region_keywords)),
        re.IGNORECASE
    )

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return
        if not region_pattern.search(text):
            return
        log.info(f"Keyword matched, AI check: {text[:100]}...")
        is_threat, reason = await ai_classify(text, cfg)
        if is_threat:
            log.warning(f"THREAT: {reason}")
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
    register_family_handlers(bot_app, cfg)
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
