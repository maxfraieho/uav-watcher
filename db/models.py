"""
Local SQLite database for family groups and rollcall state.
Zero external dependencies — all data stored locally for OPSEC.
"""
import sqlite3
import os
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'families.db')


def init_db():
    """Initialize database schema on first run."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_user_id INTEGER NOT NULL,
        invite_code TEXT UNIQUE NOT NULL,
        telegram_group_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER REFERENCES families(id),
        user_id INTEGER NOT NULL,
        username TEXT,
        display_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(family_id, user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS rollcalls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER REFERENCES families(id),
        threat_type TEXT,
        initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS rollcall_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rollcall_id INTEGER REFERENCES rollcalls(id),
        user_id INTEGER NOT NULL,
        status TEXT CHECK(status IN ('safe','sos','no_response')),
        responded_at TIMESTAMP,
        location_encrypted TEXT
    )''')

    conn.commit()
    conn.close()
    return DB_PATH


def create_family(name: str, creator_id: int) -> dict:
    """Create a new family group. Returns family dict with invite_code."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    invite_code = secrets.token_urlsafe(8).upper()
    c.execute(
        "INSERT INTO families (name, creator_user_id, invite_code) VALUES (?,?,?)",
        (name, creator_id, invite_code)
    )
    family_id = c.lastrowid
    c.execute(
        "INSERT INTO family_members (family_id, user_id) VALUES (?,?)",
        (family_id, creator_id)
    )
    conn.commit()
    conn.close()
    return {"id": family_id, "name": name, "invite_code": invite_code}


def join_family(invite_code: str, user_id: int, username: str = None, display_name: str = None):
    """Join existing family by invite code. Returns family dict or None."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM families WHERE invite_code=?", (invite_code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    family_id, name = row
    try:
        c.execute(
            "INSERT OR IGNORE INTO family_members (family_id, user_id, username, display_name) VALUES (?,?,?,?)",
            (family_id, user_id, username, display_name)
        )
        conn.commit()
    except Exception:
        pass
    conn.close()
    return {"id": family_id, "name": name, "invite_code": invite_code}


def get_family_members(family_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, display_name FROM family_members WHERE family_id=?", (family_id,))
    members = [{"user_id": r[0], "username": r[1], "display_name": r[2]} for r in c.fetchall()]
    conn.close()
    return members


def get_user_families(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT f.id, f.name, f.invite_code FROM families f
                 JOIN family_members fm ON f.id = fm.family_id
                 WHERE fm.user_id=?""", (user_id,))
    families = [{"id": r[0], "name": r[1], "invite_code": r[2]} for r in c.fetchall()]
    conn.close()
    return families


def start_rollcall(family_id: int, threat_type: str) -> int:
    """Create a new rollcall event. Returns rollcall_id."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO rollcalls (family_id, threat_type) VALUES (?,?)",
        (family_id, threat_type)
    )
    rollcall_id = c.lastrowid
    members = get_family_members(family_id)
    for m in members:
        c.execute(
            "INSERT INTO rollcall_responses (rollcall_id, user_id, status) VALUES (?,?,'no_response')",
            (rollcall_id, m['user_id'])
        )
    conn.commit()
    conn.close()
    return rollcall_id


def record_rollcall_response(rollcall_id: int, user_id: int, status: str):
    """Record 'safe' or 'sos' response."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE rollcall_responses SET status=?, responded_at=? WHERE rollcall_id=? AND user_id=?",
        (status, datetime.now().isoformat(), rollcall_id, user_id)
    )
    conn.commit()
    conn.close()


def get_rollcall_status(rollcall_id: int) -> dict:
    """Get current rollcall summary."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT status, COUNT(*) FROM rollcall_responses WHERE rollcall_id=? GROUP BY status",
        (rollcall_id,)
    )
    counts = {r[0]: r[1] for r in c.fetchall()}
    c.execute("""SELECT rr.user_id, fm.display_name, fm.username, rr.status
                 FROM rollcall_responses rr
                 JOIN family_members fm ON rr.user_id = fm.user_id
                 WHERE rr.rollcall_id=?""", (rollcall_id,))
    details = [{"user_id": r[0], "name": r[1] or r[2] or str(r[0]), "status": r[3]}
               for r in c.fetchall()]
    conn.close()
    return {
        "safe": counts.get("safe", 0),
        "sos": counts.get("sos", 0),
        "no_response": counts.get("no_response", 0),
        "details": details
    }
