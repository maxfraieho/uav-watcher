"""
consultant/memory/channel_feed.py
Ring buffer for Telegram channel messages — filled by uav_watcher.py userbot,
read by pipeline/nodes.py to give the agent live situational awareness.

Schema: last MAX_ROWS messages per channel, auto-purged.
No dependencies beyond stdlib.
"""
import sqlite3
import time
import pathlib
import logging
from typing import Optional

log = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent
DB_PATH = _HERE / "channel_feed.db"

# Ring buffer depth: keep last N messages total
MAX_ROWS = 500
# How many recent messages to expose to agent on each query
CONTEXT_LIMIT = 40
# Maximum age (seconds) of messages to include in context (2 hours)
MAX_AGE_SEC = 7200


# ── Schema ───────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS feed (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            INTEGER NOT NULL,          -- unix timestamp
    channel_id    INTEGER NOT NULL,
    channel_title TEXT    NOT NULL,
    text          TEXT    NOT NULL,
    is_threat     INTEGER NOT NULL DEFAULT 0, -- 0 / 1
    reason        TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS feed_ts ON feed(ts);
CREATE INDEX IF NOT EXISTS feed_channel ON feed(channel_id, ts);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def _ensure_schema():
    with _conn() as c:
        c.executescript(_DDL)


_ensure_schema()


# ── Write ─────────────────────────────────────────────────────────────────────

def feed_message(
    text: str,
    channel_id: int,
    channel_title: str,
    is_threat: bool,
    reason: str = "",
) -> None:
    """
    Called from uav_watcher.py handler() for every message that passes
    the city keyword filter — regardless of AI threat classification.
    Thread-safe, fire-and-forget.
    """
    if not text or not text.strip():
        return
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO feed (ts, channel_id, channel_title, text, is_threat, reason)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    int(time.time()),
                    channel_id,
                    channel_title,
                    text[:2000],   # guard against giant messages
                    1 if is_threat else 0,
                    (reason or "")[:300],
                ),
            )
            # Purge old rows beyond ring buffer depth
            c.execute(
                "DELETE FROM feed WHERE id NOT IN "
                "(SELECT id FROM feed ORDER BY ts DESC LIMIT ?)",
                (MAX_ROWS,),
            )
    except Exception as e:
        log.warning(f"[channel_feed] write error: {e}")


# ── Read ──────────────────────────────────────────────────────────────────────

def get_recent(
    limit: int = CONTEXT_LIMIT,
    max_age_sec: int = MAX_AGE_SEC,
) -> list[dict]:
    """
    Returns recent messages as list of dicts, newest first.
    Filters by max_age_sec to avoid stale data.
    """
    cutoff = int(time.time()) - max_age_sec
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT ts, channel_title, text, is_threat, reason"
                " FROM feed"
                " WHERE ts >= ?"
                " ORDER BY ts DESC"
                " LIMIT ?",
                (cutoff, limit),
            ).fetchall()
        return [
            {
                "ts": r[0],
                "channel": r[1],
                "text": r[2],
                "is_threat": bool(r[3]),
                "reason": r[4],
            }
            for r in rows
        ]
    except Exception as e:
        log.warning(f"[channel_feed] read error: {e}")
        return []


def get_threat_count(window_sec: int = 3600) -> int:
    """Count confirmed threats in the last window_sec seconds."""
    cutoff = int(time.time()) - window_sec
    try:
        with _conn() as c:
            row = c.execute(
                "SELECT COUNT(*) FROM feed WHERE ts >= ? AND is_threat = 1",
                (cutoff,),
            ).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def get_recent_formatted(
    limit: int = CONTEXT_LIMIT,
    max_age_sec: int = MAX_AGE_SEC,
) -> str:
    """
    Returns recent channel messages as a human-readable block
    for injection into the agent system prompt.

    Format:
        [HH:MM] 📡 Канал Name
        Повідомлення текст...
        🚨 AI: reason  ← only for threats
    """
    messages = get_recent(limit=limit, max_age_sec=max_age_sec)
    if not messages:
        return ""

    import datetime
    lines = []
    for m in reversed(messages):  # chronological order for LLM
        dt = datetime.datetime.fromtimestamp(m["ts"]).strftime("%H:%M")
        threat_mark = " 🚨" if m["is_threat"] else ""
        lines.append(f"[{dt}] 📡 {m['channel']}{threat_mark}")
        # Truncate long messages for context window efficiency
        body = m["text"][:400].replace("\n", " ")
        if len(m["text"]) > 400:
            body += "…"
        lines.append(body)
        if m["is_threat"] and m["reason"]:
            lines.append(f"  ↳ AI: {m['reason']}")
        lines.append("")  # blank line between messages

    header_lines = [
        f"[Повідомлення з Telegram-каналів — останні {len(messages)} за {max_age_sec // 3600}г]",
        "",
    ]
    return "\n".join(header_lines + lines).strip()


def get_stats() -> dict:
    """Quick stats for /health endpoint."""
    try:
        with _conn() as c:
            total = c.execute("SELECT COUNT(*) FROM feed").fetchone()[0]
            threats = c.execute(
                "SELECT COUNT(*) FROM feed WHERE is_threat=1"
            ).fetchone()[0]
            oldest = c.execute("SELECT MIN(ts) FROM feed").fetchone()[0]
            newest = c.execute("SELECT MAX(ts) FROM feed").fetchone()[0]
        return {
            "total_messages": total,
            "threat_messages": threats,
            "oldest_ts": oldest,
            "newest_ts": newest,
        }
    except Exception:
        return {}
