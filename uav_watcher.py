#!/usr/bin/env python3
"""
UAV threat watcher for Oleksandriia.
Monitors Telegram channels via Telethon, classifies via goclaw AI,
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

async def ai_classify(text: str, cfg: dict) -> tuple[bool, str]:
    """Ask goclaw AI: is this a UAV threat for Oleksandriia?"""
    prompt = (
        "Ти система моніторингу БПЛА. Визнач: чи це повідомлення містить "
        "загрозу БПЛА (безпілотного літального апарату) або ракетну загрозу "
        "саме для міста Олександрія Кіровоградської області? "
        "Відповідь ТІЛЬКИ JSON без markdown: {\"threat\": true/false, \"reason\": \"коротко\"}\n\n"
        f"Повідомлення:\n{text}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                cfg["goclaw_url"],
                headers={
                    "Authorization": f"Bearer {cfg[goclaw_api_key]}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": cfg["goclaw_model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0
                }
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
            result = json.loads(content)
            return result.get("threat", False), result.get("reason", "")
    except Exception as e:
        log.error(f"AI classify error: {e}")
        return False, ""

async def send_notification(text: str, reason: str, cfg: dict):
    """Send alert via Bot API."""
    msg = f"\U0001f6a8 *ЗАГРОЗА БПЛА — ОЛЕКСАНДРІЯ*\n\n{text}\n\n_AI: {reason}_"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{cfg[bot_token]}/sendMessage",
                json={
                    "chat_id": cfg["notify_chat_id"],
                    "text": msg,
                    "parse_mode": "Markdown"
                }
            )
            resp.raise_for_status()
            log.info(f"Notification sent: {reason}")
    except Exception as e:
        log.error(f"Send notification error: {e}")

async def main():
    cfg = load_config()
    city_pattern = re.compile("|".join(cfg["city_keywords"]), re.IGNORECASE)
    channels = cfg["channels"]

    client = TelegramClient(
        os.path.join(os.path.dirname(__file__), "uav_watcher"),
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"]
    )

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return
        if not city_pattern.search(text):
            return
        log.info(f"City keyword found, sending to AI: {text[:80]}...")
        is_threat, reason = await ai_classify(text, cfg)
        if is_threat:
            log.info(f"THREAT detected: {reason}")
            await send_notification(text, reason, cfg)
        else:
            log.info(f"Not a threat: {reason}")

    await client.start(phone=os.environ["TELEGRAM_PHONE"])
    log.info(f"Watching channels: {channels}")
    log.info("UAV watcher started. Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
