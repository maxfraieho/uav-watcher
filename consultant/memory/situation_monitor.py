"""
consultant/memory/situation_monitor.py
Progressive threat monitor with 4 escalation levels.

Level 0 — no threat         → silent
Level 1 — watch             → notify every 30 min
Level 2 — alert (тривога)   → notify every 10 min + immediately on escalation
Level 3 — danger (бпла над  → notify every 5 min + immediately on escalation
          містом/вибухи)

Immediate escalation: if level rises from previous check → notify instantly.
"""
import json
import logging
import pathlib
import threading
import time

import httpx

from .channel_feed import get_recent_formatted, get_threat_count

log = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent

# Minimum seconds between repeat notifications per level
_MIN_INTERVAL = {
    1: 1800,  # 30 min  — watch
    2:  600,  # 10 min  — alert
    3:  300,  #  5 min  — danger
}

# How often to run the LLM check
INTERVAL_ALERT_SEC = 300    # 5 min when feed has threats
INTERVAL_QUIET_SEC = 1800   # 30 min when quiet

_state_lock        = threading.Lock()
_last_notified     = {1: 0.0, 2: 0.0, 3: 0.0}  # ts per level
_current_level     = 0  # last assessed level

# ── Prompt ───────────────────────────────────────────────────────────────────

_ASSESS_PROMPT = """\
Ти — тактичний аналітик цивільної безпеки. Нижче — повідомлення з Telegram-каналів
моніторингу за останні 2 години (хронологічно).

Визнач рівень ПОТОЧНОЇ загрози для міста Олександрія (Кіровоградська область):

РІВЕНЬ 0 — Загроз немає (відбій, тиша, тривоги тільки в далеких регіонах)
РІВЕНЬ 1 — Спостереження (БПЛА або ракети зафіксовано в Кіровоградській обл. або на підльоті, тривога НЕ оголошена для Олександрії)
РІВЕНЬ 2 — Тривога (оголошена повітряна тривога в Олександрійському районі, або БПЛА/ракети рухаються безпосередньо в бік Олександрії)
РІВЕНЬ 3 — Небезпека (БПЛА або ракети безпосередньо над Олександрією, або вибухи в місті / поруч з містом)

Враховуй час повідомлень. Останні повідомлення мають більшу вагу.

Відповідай СТРОГО у форматі (рівно 2 рядки):
LEVEL: <0, 1, 2 або 3>
REASON: <одне коротке речення по-українськи чому саме цей рівень>

--- ПОВІДОМЛЕННЯ ---
{feed_text}
"""

# ── Notification templates ────────────────────────────────────────────────────

def _build_message(level: int, reason: str, city: str) -> str:
    city_up = city.upper()
    if level == 1:
        return (
            f"⚠️ *СПОСТЕРЕЖЕННЯ — {city_up}*\n\n"
            f"{reason}\n\n"
            f"_Аналіз каналів_"
        )
    elif level == 2:
        return (
            f"\U0001f6a8 *ТРИВОГА — {city_up}* \U0001f6a8\n\n"
            f"{reason}\n\n"
            f"_Аналіз каналів_"
        )
    elif level == 3:
        return (
            f"\U0001f534\U0001f534\U0001f534 *НЕБЕЗПЕКА! ЗАГРОЗА НАД МІСТОМ* \U0001f534\U0001f534\U0001f534\n\n"
            f"{reason}\n\n"
            f"\U0001f4e2\U0001f4e2\U0001f4e2 *НЕГАЙНО В УКРИТТЯ!* \U0001f4e2\U0001f4e2\U0001f4e2\n\n"
            f"_Аналіз каналів_"
        )
    return ""

# ── Config / LLM / Telegram ───────────────────────────────────────────────────

def _get_config() -> dict:
    cfg_path = _HERE.parent.parent / "config.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _call_llm(feed_text: str) -> tuple[int, str]:
    """Returns (threat_level 0-3, reason_str)."""
    cfg   = _get_config()
    url   = (cfg.get("llm_proxy_url") or "").rstrip("/")
    token = cfg.get("llm_proxy_token") or "freecc"
    model = cfg.get("llm_proxy_model") or "docs-assistant-proxy"
    if not url:
        return 0, "no llm config"

    prompt = _ASSESS_PROMPT.format(feed_text=feed_text[:3000])
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(
                f"{url}/chat/completions",
                headers={"Authorization": f"Bearer {token}", "User-Agent": "curl/7.88.1"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 80,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning(f"[monitor] LLM error: {e}")
        return 0, f"LLM error: {e}"

    level  = 0
    reason = content[:200]
    for line in content.splitlines():
        line = line.strip()
        uline = line.upper()
        if uline.startswith("LEVEL:"):
            try:
                level = int(uline.split(":", 1)[1].strip()[0])
                level = max(0, min(3, level))
            except (ValueError, IndexError):
                pass
        elif uline.startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

    return level, reason


def _send_telegram(level: int, reason: str, cfg: dict) -> bool:
    token   = cfg.get("bot_token", "")
    chat_id = cfg.get("notify_chat_id", "")
    city    = cfg.get("city", "Олександрія")
    if not token or not chat_id:
        log.warning("[monitor] bot_token or notify_chat_id missing in config")
        return False

    msg = _build_message(level, reason, city)
    if not msg:
        return False

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            )
            resp.raise_for_status()
        log.info(f"[monitor] L{level} sent: {reason[:80]}")
        return True
    except Exception as e:
        log.error(f"[monitor] Telegram error: {e}")
        return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def _should_notify(new_level: int, prev_level: int) -> bool:
    """True if notification should be sent for this level."""
    if new_level == 0:
        return False
    now = time.time()
    with _state_lock:
        escalated = new_level > prev_level
        elapsed   = now - _last_notified[new_level]
        return escalated or (elapsed >= _min_interval(new_level))


def _min_interval(level: int) -> int:
    return _MIN_INTERVAL.get(level, 1800)


def _loop():
    global _current_level
    log.info(f"[monitor] Situation monitor started "
             f"(alert={INTERVAL_ALERT_SEC}s quiet={INTERVAL_QUIET_SEC}s)")
    time.sleep(90)  # let feed fill a bit

    while True:
        interval = INTERVAL_QUIET_SEC
        try:
            feed_text    = get_recent_formatted(limit=30, max_age_sec=7200)
            threat_count = get_threat_count(window_sec=3600)
            interval     = INTERVAL_ALERT_SEC if threat_count > 0 else INTERVAL_QUIET_SEC

            if not feed_text:
                log.debug("[monitor] Feed empty — skip")
            else:
                new_level, reason = _call_llm(feed_text)
                prev_level        = _current_level
                log.info(f"[monitor] Level {new_level} (prev {prev_level}): {reason[:80]}")

                if _should_notify(new_level, prev_level):
                    cfg = _get_config()
                    if _send_telegram(new_level, reason, cfg):
                        with _state_lock:
                            _last_notified[new_level] = time.time()

                _current_level = new_level

        except Exception as e:
            log.error(f"[monitor] loop error: {e}")

        time.sleep(interval)


def start_monitor() -> threading.Thread:
    t = threading.Thread(target=_loop, name="situation-monitor", daemon=True)
    t.start()
    return t
