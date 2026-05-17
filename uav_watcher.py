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
        f"Ти система моніторингу БПЛА. Визнач: чи це повідомлення містить "
        f"загрозу БПЛА (безпілотного літального апарату) або ракетну загрозу "
        f"саме для міста {city} ({region})? "
        f"Відповідь ТІЛЬКИ JSON без markdown: "
        f'{"{"}"threat": true/false, "reason": "коротко в 5-10 слів"{"}"}\n\n'
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

    # Region keywords: alert even without specific city name
    region = cfg.get("city_region", "Кіровоградська")
    region_keywords = cfg.get("region_keywords", [region[:12]])
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
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
