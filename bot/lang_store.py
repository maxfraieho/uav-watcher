import sqlite3
import os

_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "user_prefs.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS user_lang "
        "(user_id INTEGER PRIMARY KEY, lang TEXT NOT NULL DEFAULT uk)"
    )
    c.commit()
    return c


def get_lang(user_id: int) -> str:
    with _conn() as c:
        row = c.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)).fetchone()
        return row[0] if row else "uk"


def set_lang(user_id: int, lang: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO user_lang(user_id,lang) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang",
            (user_id, lang),
        )
        c.commit()
