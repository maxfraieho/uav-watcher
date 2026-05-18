"""
consultant/memory/summarizer.py
Background thread that periodically reads the channel feed and asks the AI
to generate a concise tactical situation summary.

Writes to: consultant/memory/channel_summary.json
Read by:   consultant/pipeline/nodes.py → retrieve_kb()

Interval: every SUMMARY_INTERVAL_SEC seconds (default 5 min).
Only runs if there are new messages since the last summary.
"""
import json
import logging
import pathlib
import threading
import time
import os

import httpx

from .channel_feed import get_recent_formatted, get_recent, get_threat_count

log = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent
SUMMARY_PATH = _HERE / "channel_summary.json"

SUMMARY_INTERVAL_SEC = 300   # 5 minutes
MAX_AGE_VALID_SEC    = 600   # summary is "fresh" for 10 min


# ── Prompt ───────────────────────────────────────────────────────────────────

_SUMMARIZE_PROMPT = """\
Ти — тактичний аналітик цивільної безпеки. Нижче — повідомлення з Telegram-каналів моніторингу повітряних тривог.

Склади КОРОТКЕ тактичне зведення (2-4 речення) українською мовою:
- Що відбувається прямо зараз (активні загрози / відбій)?
- Який тип загроз зафіксовано (БПЛА, ракети, FAB, загальна тривога)?
- Які регіони/міста згадуються?

Якщо немає активних загроз — напиши "Активних загроз не виявлено."
Відповідай ТІЛЬКИ текстом зведення, без заголовків і пояснень.

--- ПОВІДОМЛЕННЯ ---
{feed_text}
"""


# ── LLM call ─────────────────────────────────────────────────────────────────

def _get_llm_config() -> tuple[str, str, str]:
    """Read LLM config from config.json (project root)."""
    config_path = _HERE.parent.parent / "config.json"
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        url   = (cfg.get("llm_proxy_url")   or cfg.get("goclaw_url",  "")).rstrip("/")
        token = cfg.get("llm_proxy_token") or cfg.get("goclaw_api_key", "freecc")
        model = cfg.get("llm_proxy_model") or cfg.get("goclaw_model",  "docs-assistant-proxy")
        return url, token, model
    except Exception:
        return (
            os.getenv("PROXY_URL", "https://YOUR_PROXY_URL/v1").rstrip("/"),
            os.getenv("PROXY_TOKEN", "freecc"),
            os.getenv("PROXY_MODEL", "docs-assistant-proxy"),
        )


def _call_llm(feed_text: str) -> str | None:
    proxy_url, proxy_token, proxy_model = _get_llm_config()
    prompt = _SUMMARIZE_PROMPT.format(feed_text=feed_text[:3000])
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{proxy_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {proxy_token}",
                    "User-Agent": "curl/7.88.1",   # required by this proxy
                },
                json={
                    "model": proxy_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning(f"[summarizer] LLM call failed: {e}")
        return None


# ── Persist ───────────────────────────────────────────────────────────────────

def _write_summary(summary: str, threat_count: int):
    data = {
        "ts": int(time.time()),
        "summary": summary,
        "threat_count_1h": threat_count,
    }
    tmp = str(SUMMARY_PATH) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        import os as _os
        _os.replace(tmp, str(SUMMARY_PATH))
        log.info(f"[summarizer] Updated: {summary[:80]}...")
    except Exception as e:
        log.error(f"[summarizer] write failed: {e}")


def read_channel_summary(max_age_sec: int = MAX_AGE_VALID_SEC) -> str:
    """
    Read current channel summary.
    Returns empty string if file missing or too old.
    Called from pipeline/nodes.py → retrieve_kb().
    """
    try:
        data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        age = int(time.time()) - data.get("ts", 0)
        if age > max_age_sec:
            return ""
        summary = data.get("summary", "")
        count = data.get("threat_count_1h", 0)
        if count > 0:
            return f"{summary} (підтверджених загроз за останню годину: {count})"
        return summary
    except Exception:
        return ""


# ── Background thread ─────────────────────────────────────────────────────────

_last_message_count = 0


def _should_run() -> bool:
    """Only regenerate summary if there are new messages since last run."""
    global _last_message_count
    from .channel_feed import get_stats
    stats = get_stats()
    current = stats.get("total_messages", 0)
    if current > _last_message_count:
        _last_message_count = current
        return True
    return False


def _loop():
    log.info("[summarizer] Channel feed summarizer started "
             f"(interval: {SUMMARY_INTERVAL_SEC}s)")
    # Initial delay: let the feed collect some messages first
    time.sleep(30)

    while True:
        try:
            if _should_run():
                feed_text = get_recent_formatted(limit=30, max_age_sec=7200)
                if feed_text:
                    summary = _call_llm(feed_text)
                    if summary:
                        threat_count = get_threat_count(window_sec=3600)
                        _write_summary(summary, threat_count)
                    else:
                        log.debug("[summarizer] LLM returned None — skipping")
                else:
                    log.debug("[summarizer] No recent feed messages — skipping")
            else:
                log.debug("[summarizer] No new messages — skipping")
        except Exception as e:
            log.error(f"[summarizer] loop error: {e}")

        time.sleep(SUMMARY_INTERVAL_SEC)


def start_summarizer() -> threading.Thread:
    """
    Start background summarizer thread.
    Called from consultant/main.py lifespan().
    """
    t = threading.Thread(target=_loop, name="channel-summarizer", daemon=True)
    t.start()
    return t
