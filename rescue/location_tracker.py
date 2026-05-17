"""
Location check-in and dead man's switch for victim location under rubble.
Stores last known location per user in SQLite (same DB as family groups).
GPS coordinates are never logged to stdout in production.
"""
import sqlite3
import logging
from datetime import datetime
from db.models import DB_PATH

log = logging.getLogger(__name__)


def _ensure_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS location_checkins (
        user_id INTEGER PRIMARY KEY,
        lat REAL,
        lon REAL,
        address TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()


def save_checkin(user_id: int, lat: float, lon: float, address: str = None):
    """Save or update last known location for a user."""
    _ensure_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO location_checkins (user_id, lat, lon, address, updated_at) VALUES (?,?,?,?,?)",
        (user_id, lat, lon, address, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    log.info(f"Location check-in saved for user {user_id}")  # no coords in log


def get_last_location(user_id: int):
    """Return last known location dict or None."""
    _ensure_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT lat, lon, address, updated_at FROM location_checkins WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"lat": row[0], "lon": row[1], "address": row[2], "updated_at": row[3]}
    return None


def register_location_handlers(bot_client, cfg):
    """Register /checkin and location message handlers on the bot client."""
    from telethon import events
    import httpx

    @bot_client.on(events.NewMessage(pattern='/checkin|/чекін'))
    async def cmd_checkin_prompt(event):
        await event.respond(
            "📍 *Надішли свою геолокацію*\n\n"
            "Натисни скрепку 📎 → Геолокація → Надіслати поточне місцезнаходження.\n\n"
            "Вона буде збережена як твоє останнє відоме місцезнаходження "
            "і передана рідним якщо ти не відповіси на rollcall.",
            parse_mode='md'
        )

    @bot_client.on(events.NewMessage(func=lambda e: e.geo is not None))
    async def handle_location_message(event):
        geo = event.geo
        sender = await event.get_sender()
        save_checkin(sender.id, geo.lat, geo.long)
        await event.respond(
            "✅ Геолокацію збережено.\n"
            "Якщо ти не відповіси на rollcall протягом 10 хвилин — "
            "рідні отримають посилання на твоє місцезнаходження."
        )

    log.info("Location tracker handlers registered.")
