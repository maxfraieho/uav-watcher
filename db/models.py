"""
Local SQLite database for family groups, rollcall state, and threat events.
Zero external dependencies — all data stored locally for OPSEC.
"""
import sqlite3
import os
import secrets
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'families.db')


def _migrate_db(conn):
    c = conn.cursor()
    existing = {r[1] for r in c.execute("PRAGMA table_info(family_members)")}
    if "last_seen" not in existing:
        c.execute("ALTER TABLE family_members ADD COLUMN last_seen TIMESTAMP")
    if "ok_note" not in existing:
        c.execute("ALTER TABLE family_members ADD COLUMN ok_note TEXT")
    conn.commit()


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

    c.execute('''CREATE TABLE IF NOT EXISTS threat_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER,
        channel_name TEXT,
        message_text TEXT,
        threat_type TEXT,
        proximity_score INTEGER DEFAULT 1,
        location_terms TEXT,
        is_allclear INTEGER DEFAULT 0,
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS location_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        lat REAL,
        lon REAL,
        accuracy REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id)
    )''')

    conn.commit()
    _migrate_db(conn)
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
    c.execute(
        "SELECT user_id, username, display_name, last_seen, ok_note FROM family_members WHERE family_id=?",
        (family_id,)
    )
    members = [
        {"user_id": r[0], "username": r[1], "display_name": r[2],
         "name": r[2] or r[1] or str(r[0]),
         "last_seen": r[3], "ok_note": r[4]}
        for r in c.fetchall()
    ]
    conn.close()
    return members


def get_family_members_bulk(family_ids: list) -> dict:
    """Return {family_id: [member_dict, ...]} for all given family IDs in one query."""
    if not family_ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholders = ",".join("?" * len(family_ids))
    c.execute(
        f"SELECT family_id, user_id, username, display_name, last_seen, ok_note "
        f"FROM family_members WHERE family_id IN ({placeholders})",
        family_ids,
    )
    result: dict = {fid: [] for fid in family_ids}
    for row in c.fetchall():
        fid, uid, uname, dname, last_seen, ok_note = row
        result[fid].append({
            "family_id": fid,
            "user_id": uid,
            "username": uname,
            "display_name": dname,
            "name": dname or uname or str(uid),
            "last_seen": last_seen,
            "ok_note": ok_note,
        })
    conn.close()
    return result


def get_user_families(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT f.id, f.name, f.invite_code FROM families f
                 JOIN family_members fm ON f.id = fm.family_id
                 WHERE fm.user_id=?""", (user_id,))
    families = [{"id": r[0], "name": r[1], "invite_code": r[2]} for r in c.fetchall()]
    conn.close()
    return families


def update_last_seen(user_id: int, ok_note: str = None):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    if ok_note is not None:
        conn.execute(
            "UPDATE family_members SET last_seen=?, ok_note=? WHERE user_id=?",
            (now, ok_note, user_id)
        )
    else:
        conn.execute(
            "UPDATE family_members SET last_seen=? WHERE user_id=?",
            (now, user_id)
        )
    conn.commit()
    conn.close()


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
    c.executemany(
        "INSERT INTO rollcall_responses (rollcall_id, user_id, status) VALUES (?,?,'no_response')",
        [(rollcall_id, m['user_id']) for m in members],
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


def save_threat_event(channel_id: int, channel_name: str, text: str,
                      threat_type: str, proximity_score: int,
                      location_terms: list, is_allclear: bool = False,
                      detected_at: str | None = None):
    conn = sqlite3.connect(DB_PATH)
    now = detected_at or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        """INSERT INTO threat_events
           (channel_id, channel_name, message_text, threat_type,
            proximity_score, location_terms, is_allclear, detected_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (channel_id, channel_name, text[:500], threat_type,
         proximity_score, ",".join(location_terms), 1 if is_allclear else 0, now)
    )
    conn.commit()
    conn.close()


def get_recent_threats(hours: int = 6) -> list:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT channel_name, message_text, threat_type, proximity_score,
                  location_terms, is_allclear, detected_at
           FROM threat_events WHERE detected_at >= ? ORDER BY detected_at DESC LIMIT 50""",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [
        {"channel_name": r[0], "message_text": r[1], "threat_type": r[2],
         "proximity_score": r[3], "location_terms": r[4],
         "is_allclear": bool(r[5]), "detected_at": r[6]}
        for r in rows
    ]


def get_threat_stats(hours: int = 24) -> dict:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        """SELECT COUNT(*), SUM(is_allclear),
                  AVG(CASE WHEN is_allclear=0 THEN proximity_score END),
                  MAX(CASE WHEN is_allclear=0 THEN proximity_score END)
           FROM threat_events WHERE detected_at >= ?""",
        (cutoff,)
    ).fetchone()
    conn.close()
    total = row[0] or 0
    allclears = row[1] or 0
    return {
        "total": total,
        "allclears": int(allclears),
        "threats": total - int(allclears),
        "avg_proximity": round(row[2] or 0, 1),
        "max_proximity": row[3] or 0,
    }
