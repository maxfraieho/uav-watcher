"""Situation watchdog — polls alerts.in.ua every 60s, writes situation_context.json.

Requires an API token from alerts.in.ua (free registration):
  https://alerts.in.ua — sign up and get a token.
Set it in config.json as: {"alerts_in_ua_token": "your-token"}
"""
import json
import logging
import pathlib
import threading
import time
import httpx

log = logging.getLogger(__name__)

ALERTS_API = "https://api.alerts.in.ua/v1/alerts/active.json"
POLL_INTERVAL = 60  # seconds
MAX_ALERTS = 10

_REGION_NAMES = {
    "Kyivska": "Київська", "Lvivska": "Львівська", "Kharkivska": "Харківська",
    "Odeska": "Одеська", "Dnipropetrovska": "Дніпропетровська",
    "Zaporizka": "Запорізька", "Khersonska": "Херсонська", "Mykolaivska": "Миколаївська",
    "Donetska": "Донецька", "Luhanska": "Луганська", "Sumska": "Сумська",
    "Chernihivska": "Чернігівська", "Poltavska": "Полтавська", "Vinnytska": "Вінницька",
    "Khmelnytska": "Хмельницька", "Zhytomyrska": "Житомирська", "Rivnenska": "Рівненська",
    "Volynska": "Волинська", "Ivano-Frankivska": "Івано-Франківська",
    "Zakarpatska": "Закарпатська", "Chernivtska": "Чернівецька",
    "Cherkaska": "Черкаська", "Kirovohradska": "Кіровоградська", "Ternopilska": "Тернопільська",
}


def _get_token(project_root: pathlib.Path) -> str:
    try:
        cfg = json.loads((project_root / "config.json").read_text(encoding="utf-8"))
        return cfg.get("alerts_in_ua_token", "")
    except Exception:
        return ""


def _fetch_situation(project_root: pathlib.Path) -> dict:
    """Fetch active alerts from alerts.in.ua (requires API token)."""
    token = _get_token(project_root)
    if not token:
        return {}  # No token configured — skip silently
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                ALERTS_API,
                headers={"User-Agent": "UAVWatcher/2.0", "X-API-Key": token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        log.warning(f"[watchdog] alerts.in.ua fetch failed: {e}")
        return {}

    alerts = data.get("alerts", [])
    active = [a for a in alerts if a.get("alert_type") == "air_raid"]

    regions = []
    for a in active[:MAX_ALERTS]:
        region = a.get("location_title", a.get("location", ""))
        region_ua = _REGION_NAMES.get(region, region)
        regions.append(region_ua)

    return {
        "ts": int(time.time()),
        "active_count": len(active),
        "regions": regions,
        "summary": _build_summary(active, regions),
    }


def _build_summary(active: list, regions: list) -> str:
    if not active:
        return "Активних повітряних тривог наразі немає."
    count = len(active)
    region_list = ", ".join(regions[:5])
    if len(regions) > 5:
        region_list += f" та ще {len(regions) - 5}"
    return f"Зараз активно {count} повітряних тривог: {region_list}."


def _write_context(ctx_path: pathlib.Path, data: dict):
    tmp = str(ctx_path) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        import os
        os.replace(tmp, str(ctx_path))
    except Exception as e:
        log.error(f"[watchdog] write failed: {e}")


def read_situation(project_root: pathlib.Path) -> str:
    """Read current situation summary for consultant context injection."""
    ctx_path = project_root / "situation_context.json"
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
        age = int(time.time()) - data.get("ts", 0)
        if age > 300:
            return ""
        return data.get("summary", "")
    except Exception:
        return ""


def start_watcher(project_root: pathlib.Path) -> threading.Thread:
    """Start background polling thread. Requires alerts_in_ua_token in config.json."""
    ctx_path = project_root / "situation_context.json"

    def _loop():
        log.info("[watchdog] Situation watcher started (alerts.in.ua, 60s interval)")
        token = _get_token(project_root)
        if not token:
            log.info("[watchdog] No alerts_in_ua_token in config.json — polling disabled. "
                     "Get a free token at https://alerts.in.ua")
        while True:
            try:
                data = _fetch_situation(project_root)
                if data:
                    _write_context(ctx_path, data)
                    log.info(f"[watchdog] {data.get('summary', '')}")
            except Exception as e:
                log.error(f"[watchdog] loop error: {e}")
            time.sleep(POLL_INTERVAL)

    t = threading.Thread(target=_loop, name="situation-watcher", daemon=True)
    t.start()
    return t
