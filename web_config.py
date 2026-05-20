#!/usr/bin/env python3
"""
Sharon — web config UI.
Run: python3 web_config.py
Open: http://localhost:8422
"""
import json
import os
import re
import subprocess
import math as _math
import urllib.request
import urllib.parse as _urllib_parse
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
import threading
import concurrent.futures
from urllib.parse import parse_qs, urlparse

_shelter_cache: dict = {}   # {city_key: {"ts": float, "shelters": list}}

LOCKED_CHANNELS = {
    -1001223955273: {"title": "Повітряні Сили ЗС України", "username": "kpszsu", "id": -1001223955273}
}

# ── In-UI Chat Knowledge Base ─────────────────────────────────────────────────
CHAT_KB = {
    "uav": {
        "title": "🚁 БПЛА / Дрон-камікадзе",
        "text": "🚁 *ЗАГРОЗА БПЛА — ДІЙ ЗАРАЗ*\n\n✅ *НЕГАЙНО:*\n• Відійди від вікон — ляж на підлогу\n• Вимкни світло, закрий штори (перекриває оптику)\n• НЕ виходь надвір — дрон відстежує рух\n• Телефон на беззвучний, але НЕ вимикай\n\n🏠 *УКРИТТЯ (правило двох стін):*\nВанна кімната або коридор > підвал\nНЕ ховайся під сходами (ризик обвалу)\n\n💥 *ПІСЛЯ ВИБУХУ В РАДІУСІ 500м:*\n• Зачини вікна (хімічна загроза)\n• Не виходь 15 хв (можлива друга хвиля)\n• Зателефонуй: 101 або 112"
    },
    "ballistic": {
        "title": "🚀 Балістична ракета / Іскандер",
        "text": "🚀 *БАЛІСТИЧНА ЗАГРОЗА — СЕКУНДИ ВИРІШУЮТЬ*\n\n⚡ Час: 2–4 хвилини до удару\n\n✅ *ЯКЩО Є ЧАС:*\nПідвал або 1-й поверх, несучі стіни\n\n✅ *ЯКЩО НЕ ВСТИГ:*\n• Ляж у будь-яке заглиблення (канава, підземний перехід)\n• Відкрий рот (від вибухової хвилі)\n• Прикрий потилицю руками\n• Відвернись від напрямку загрози\n\n📵 НЕ знімай відео — йди в укриття"
    },
    "cruise": {
        "title": "✈️ Крилата ракета / Калібр",
        "text": "✈️ *КРИЛАТА РАКЕТА — УКРИЙСЯ*\n\n✅ *НЕГАЙНО:*\n• Підземний паркінг або підвал — мета №1\n• Від вікон якомога далі\n• Не стій у відкритих місцях\n\n⚠️ Kalibr летить на малій висоті — попередження може бути коротким\n\n🔇 Вимкни газ, відкрий вікно в іншій кімнаті (від вибухової хвилі)\n\n📞 Після відбою: 101 (ДСНС), 112"
    },
    "fab": {
        "title": "💣 Авіабомба FAB / Планер",
        "text": "💣 *FAB АВІАБОМБА — МАКСИМАЛЬНА ЗАГРОЗА*\n\n‼️ Правило двох стін НЕ ПРАЦЮЄ\n‼️ Потрібен ГЛИБОКИЙ підвал або багаторівневе бомбосховище\n\n✅ *НЕГАЙНО:*\n• Глибоке бомбосховище / метро / підземний паркінг\n• НЕ залишайся в квартирі — навіть на 1-му поверсі\n• Якщо немає укриття — відійди від будівель щонайменше 50м\n• Ляж у ямку/канаву, прикрий голову\n\n📞 112 або 101 — після удару"
    },
    "chemical": {
        "title": "☣️ Хімічна / Токсична загроза",
        "text": "☣️ *ХІМІЧНА ЗАГРОЗА — ГЕРМЕТИЗУЙ ПРИМІЩЕННЯ*\n\n🔴 Ознаки: незвичний запах, димова хмара, симптоми у людей\n\n✅ *НЕГАЙНО:*\n• Закрий ВСІ вікна і двері ГЕРМЕТИЧНО\n• Змочи тканину — прикрий рот і ніс\n• Піднімись вище (більшість газів важчі за повітря)\n• Заклей щілини скотчем якщо є\n\n🚫 *НЕ виходь без захисту*\n\n✅ *Якщо ти надворі:*\n• Тримайся з навітряного боку\n• Знімай одяг, рясно промивай шкіру водою\n\n📞 101 — одразу"
    },
    "rubble": {
        "title": "🆘 Під завалами / Будинок зруйновано",
        "text": "🆘 *ПІД ЗАВАЛАМИ — ЩО РОБИТИ*\n\n📱 *ЯКЩО ТИ ПІД ЗАВАЛАМИ:*\n• Стукай по трубах або бетону КОЖНІ 30 СЕК\n• Прикрий рот тканиною від пилу\n• Дихай спокійно — економ кисень\n• НЕ кричи постійно — втратиш сили\n\n👥 *ЯКЩО ШУКАЄШ ЛЮДИНУ:*\n• Зателефонуй 101 (ДСНС) — ПЕРШОЧЕРГОВО\n• Слухай кожні 2 хвилини: стукіт, голос\n• НЕ рухай великі уламки самостійно\n\n📞 101 або 112"
    },
    "allclear": {
        "title": "✅ Відбій тривоги",
        "text": "✅ *ВІДБІЙ — НЕБЕЗПЕКА МИНУЛА*\n\nПерш ніж виходити:\n• Зачекай 5–10 хвилин після офіційного відбою\n• Оглянь вулицю через вікно перед виходом\n• Не торкайся невідомих предметів на вулиці\n\n💬 Повідом рідних що ти в безпеці"
    },
    "panic": {
        "title": "😰 Технiка заземлення 5-4-3-2-1",
        "text": "😰 *ТЕХНIКА ЗАЗЕМЛЕННЯ (5-4-3-2-1)*\n\nКоли накриває паніка — зроби це:\n\n🟢 *1.* Назви 5 речей які ти БАЧИШ зараз\n🟢 *2.* Торкнись 4 різних поверхні поруч з тобою\n🟢 *3.* Прислухайся — назви 3 звуки які чуєш\n🟢 *4.* Відчуй 2 запахи або текстури\n🟢 *5.* Зроби 1 глибокий вдих... і повільний видих\n\n✅ Ти тут. Ти в безпеці. Продовжуй дихати рівно.\n\n💬 Зв'яжись з рідними — повідом що ти в безпеці."
    },
    "shelter": {
        "title": "🏠 Де ховатись — ієрархія укриттів",
        "text": "🏠 *ІЄРАРХІЯ УКРИТТІВ*\n\n1. Метро / глибокий підвал / бомбосховище\n2. Підземний паркінг\n3. 1-й поверх — ванна/коридор (від вікон)\n4. Будь-яке заглиблення надворі\n\n*Правило двох стін:*\nМіж тобою і вулицею — мінімум 2 несучі стіни\n\n*НЕ ховайся:*\n• Під сходами (ризик обвалу)\n• В ліфті (відключається при тривозі)\n• На верхніх поверхах\n\n⚠️ При загрозі FAB — правило двох стін не діє. Потрібен глибокий підвал."
    },
    "phones": {
        "title": "📞 Телефони екстрених служб",
        "text": "📞 *ЕКСТРЕНІ НОМЕРИ*\n\n101 — Пожежа / ДСНС\n102 — Поліція\n103 — Швидка допомога\n104 — Аварійна газова служба\n*112* — Єдина екстрена (всі три)\n\nПри виявленні НВП (нерозірваних боєприпасів):\n→ 101 або 102 — НЕ торкайся"
    },
    "channels": {
        "title": "📡 Як додати канал моніторингу",
        "text": "📡 *ДОДАТИ TELEGRAM-КАНАЛ*\n\n1. Знайди ID каналу:\n• Перешли повідомлення з каналу боту @userinfobot\n• Або @getmyid_bot → /start\n• ID виглядає як -1002187970584\n\n2. Встав ID у поле 'Канали моніторингу' на цій сторінці\n3. Натисни 'Перевірити' → потім 'Додати'\n4. Перезапусти сервіс\n\n🔍 *Де шукати:*\nПошук в Telegram: 'повітряна тривога кіровоград'\ntgstat.ua → фільтр 'Безпека'"
    },
    "unknown": {
        "title": "",
        "text": "❓ Не знайшов точної відповіді.\n\nСпробуй запитати про:\n• 🚁 БПЛА / дрон\n• 🚀 Балістична ракета / Іскандер\n• ✈️ Крилата ракета / Калібр\n• 💣 FAB авіабомба\n• ☣️ Хімічна загроза\n• 🆘 Під завалами\n• 😰 Паніка / заземлення\n• ✅ Відбій тривоги\n• 🏠 Де ховатись\n• 📞 Телефони екстрених служб\n• 📡 Як додати канал"
    }
}

def chat_match(question: str) -> dict:
    q = question.lower()
    if any(k in q for k in ['бпла','дрон','шахед','shahed','ланцет','uav','камікадз']):
        return CHAT_KB['uav']
    if any(k in q for k in ['балістич','iskander','іскандер','балістика','іскандер']):
        return CHAT_KB['ballistic']
    if any(k in q for k in ['крилат','калібр','kalibr','x-101','x-55','cruise']):
        return CHAT_KB['cruise']
    if any(k in q for k in ['фаб','авіабомб','fab','планер','glide']):
        return CHAT_KB['fab']
    if any(k in q for k in ['хімічн','chemical','токсич','газ','отруй','☣']):
        return CHAT_KB['chemical']
    if any(k in q for k in ['завал','зруйнов','trapped','rubble','під завал']):
        return CHAT_KB['rubble']
    if any(k in q for k in ['відбій','allclear','all clear','тривог','скінчил','скасов']):
        return CHAT_KB['allclear']
    if any(k in q for k in ['паніка','пані','calm','заземл','заспокою','5 речей','grounding','дихан']):
        return CHAT_KB['panic']
    if any(k in q for k in ['укриття','сховище','shelter','де сховат','де ховат','підвал','бомбосховищ']):
        return CHAT_KB['shelter']
    if any(k in q for k in ['телефон','101','102','103','112','дзвони','виклик','служба','екстрен']):
        return CHAT_KB['phones']
    if any(k in q for k in ['канал','channel','додати','знайти канал','tgstat','userinfobot','telegram']):
        return CHAT_KB['channels']
    return CHAT_KB['unknown']


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
PORT = 8422


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


_CONFIG_LOCK = threading.Lock()

def save_config(cfg: dict):
    tmp = CONFIG_PATH + ".tmp"
    # Detect bot_token change → clear Telethon session so new token works
    try:
        _old = json.loads(open(CONFIG_PATH, encoding="utf-8").read())
        _token_changed = _old.get("bot_token") != cfg.get("bot_token")
    except Exception:
        _token_changed = False
    with _CONFIG_LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    try:
        from pathlib import Path
        (Path(__file__).parent / "data" / ".reload_city").touch()
    except Exception:
        pass
    if _token_changed:
        try:
            from pathlib import Path
            session = Path(__file__).parent / "bot.session"
            if session.exists():
                session.unlink()
            (Path(__file__).parent / "data" / ".restart_bot").touch()
        except Exception:
            pass


def load_env() -> dict:
    env = {"TELEGRAM_API_ID": "", "TELEGRAM_API_HASH": "", "TELEGRAM_PHONE": ""}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    if k in env:
                        env[k] = v.strip()
    return env


def save_env(api_id: str, api_hash: str, phone: str):
    with open(ENV_PATH, "w") as f:
        f.write(f"TELEGRAM_API_ID={api_id}\n")
        f.write(f"TELEGRAM_API_HASH={api_hash}\n")
        f.write(f"TELEGRAM_PHONE={phone}\n")


def get_user_channels(cfg: dict) -> list:
    locked_ids = set(LOCKED_CHANNELS.keys())
    raw = cfg.get("channels", [])
    meta = cfg.get("channels_meta", {})
    result = []
    for ch_id in raw:
        if ch_id not in locked_ids:
            m = meta.get(str(ch_id), {})
            result.append({"id": ch_id, "title": m.get("title", str(ch_id)), "username": m.get("username", "")})
    return result


def resolve_via_bot_api(handle: str, bot_token: str) -> dict:
    handle = handle.strip()
    if not handle.startswith("@") and not handle.lstrip("-").isdigit():
        handle = "@" + handle
    url = f"https://api.telegram.org/bot{bot_token}/getChat?chat_id={urllib.request.quote(handle)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        raise ValueError(data.get("description", "Telegram error"))
    result = data["result"]
    raw_id = result["id"]
    if raw_id > 0:
        full_id = -(1000000000000 + raw_id)
    else:
        full_id = raw_id
    return {
        "ok": True,
        "id": full_id,
        "title": result.get("title", result.get("first_name", str(full_id))),
        "username": result.get("username", ""),
    }


def restart_service():
    try:
        result = subprocess.run(
            ["sudo", "rc-service", "uav-watcher", "restart"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


# ── Cloudflare Tunnel ─────────────────────────────────────────────────────────
import signal
import socket as _socket
import string as _string
import random as _random

CLOUDFLARED_DIR = os.path.join(os.path.dirname(__file__), ".cloudflared")
_CF_TUNNEL_ID_FALLBACK = "c0413dca-1f1d-4176-be39-23e2c8f0754f"
CF_DOMAIN       = "your-domain.example"
CF_SUFFIX       = "-alert"
CF_TUNNEL_CFG   = "/tmp/Sharon-tunnel.yml"


def _cf_tunnel_id() -> str:
    """Read tunnel ID from config.json; fall back to hardcoded default."""
    try:
        return load_config().get("cf_tunnel_id") or _CF_TUNNEL_ID_FALLBACK
    except Exception:
        return _CF_TUNNEL_ID_FALLBACK


def cloudflared_ok():
    import shutil
    if not shutil.which("cloudflared"):
        return False
    if not os.path.isdir(CLOUDFLARED_DIR):
        return False
    creds = os.path.join(CLOUDFLARED_DIR, f"{_cf_tunnel_id()}.json")
    cert  = os.path.join(CLOUDFLARED_DIR, "cert.pem")
    return os.path.isfile(creds) and os.path.isfile(cert)


def tunnel_running():
    cfg = load_config()
    pid = cfg.get("tunnel_pid")
    if not pid:
        return False, None
    try:
        with open(f"/proc/{int(pid)}/status") as f:
            for line in f:
                if line.startswith("State:") and "Z" in line:
                    return False, None  # zombie — process is dead
        os.kill(int(pid), 0)
        return True, int(pid)
    except Exception:
        return False, None


def tunnel_prefix_available(prefix):
    # Wildcard DNS makes getaddrinfo useless; check our own stored URL instead
    cfg = load_config()
    current_url = cfg.get("tunnel_url", "")
    expected = f"{prefix}{CF_SUFFIX}.{CF_DOMAIN}"
    if expected in current_url:
        running, _ = tunnel_running()
        return not running   # same prefix but not running → available
    return True


def tunnel_route_dns(prefix):
    hostname = f"{prefix}{CF_SUFFIX}.{CF_DOMAIN}"
    cert     = os.path.join(CLOUDFLARED_DIR, "cert.pem")
    result   = subprocess.run(
        ["cloudflared", "tunnel",
         "--origincert", cert, "--config", "/dev/null",
         "route", "dns", _cf_tunnel_id(), hostname],
        capture_output=True, text=True, timeout=30
    )
    ok  = result.returncode == 0 or "Added CNAME" in (result.stdout + result.stderr)
    msg = (result.stdout + result.stderr).strip()
    return ok, msg


def tunnel_write_config(prefix):
    creds = os.path.join(CLOUDFLARED_DIR, f"{_cf_tunnel_id()}.json")
    cert  = os.path.join(CLOUDFLARED_DIR, "cert.pem")
    hostname = f"{prefix}{CF_SUFFIX}.{CF_DOMAIN}"
    cfg_text = (
        f"tunnel: {_cf_tunnel_id()}\n"
        f"credentials-file: {creds}\n"
        f"origincertpath: {cert}\n"
        "protocol: quic\n"
        "loglevel: warn\n"
        "no-autoupdate: true\n"
        "ingress:\n"
        f"  - hostname: {hostname}\n"
        f"    service: http://localhost:{PORT}\n"
        "  - service: http_status:404\n"
    )
    with open(CF_TUNNEL_CFG, "w") as f:
        f.write(cfg_text)


def tunnel_start(prefix):
    tunnel_write_config(prefix)
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--config", CF_TUNNEL_CFG, "run"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    url = f"https://{prefix}{CF_SUFFIX}.{CF_DOMAIN}"
    cfg = load_config()
    cfg["tunnel_pid"]    = proc.pid
    cfg["tunnel_prefix"] = prefix
    cfg["tunnel_url"]    = url
    save_config(cfg)
    return proc.pid, url


def tunnel_stop():
    cfg = load_config()
    pid = cfg.get("tunnel_pid")
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            import time as _t
            _t.sleep(0.3)
            os.kill(int(pid), signal.SIGKILL)  # force if still alive
        except Exception:
            pass
        try:
            os.waitpid(int(pid), os.WNOHANG)  # reap zombie
        except Exception:
            pass
    cfg["tunnel_pid"] = None
    save_config(cfg)
    try:
        os.remove(CF_TUNNEL_CFG)
    except FileNotFoundError:
        pass



def _haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = _math.radians(lat1), _math.radians(lat2)
    dp, dl = _math.radians(lat2 - lat1), _math.radians(lon2 - lon1)
    a = _math.sin(dp / 2) ** 2 + _math.cos(p1) * _math.cos(p2) * _math.sin(dl / 2) ** 2
    return R * 2 * _math.atan2(_math.sqrt(a), _math.sqrt(1 - a))


def geocode_city(city: str):
    """Return (lat, lon) for a city via Nominatim, or (None, None)."""
    try:
        q   = _urllib_parse.urlencode({"q": f"{city}, Ukraine", "format": "json", "limit": "1"})
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/search?{q}",
            headers={"User-Agent": "UAVWatcher/1.0 (shelter-lookup)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def query_shelters(lat: float, lon: float, radius: int = 3000) -> list:
    """Query Overpass API for public shelters near (lat, lon)."""
    import time
    cache_key = f"{lat:.4f},{lon:.4f}"
    cached = _shelter_cache.get(cache_key)
    if cached and time.time() - cached["ts"] < 3600:
        return cached["shelters"]

    overpass_q = (
        f"[out:json][timeout:30];"
        f"("
        f"  node[\"amenity\"=\"shelter\"](around:{radius},{lat},{lon});"
        f"  node[\"shelter_type\"~\".\"]( around:{radius},{lat},{lon});"
        f"  node[\"civil_protection\"=\"shelter\"](around:{radius},{lat},{lon});"
        f"  node[\"emergency\"=\"shelter\"](around:{radius},{lat},{lon});"
        f"  node[\"building\"=\"basement\"][\"access\"=\"yes\"](around:{radius},{lat},{lon});"
        f"  node[\"station\"=\"subway\"](around:{radius},{lat},{lon});"
        f"  way[\"amenity\"=\"parking\"][\"parking\"=\"underground\"](around:{radius},{lat},{lon});"
        f"  node[\"amenity\"=\"parking\"][\"parking\"=\"underground\"](around:{radius},{lat},{lon});"
        f");"
        f"out center;"
    )
    body = _urllib_parse.urlencode({"data": overpass_q}).encode()
    try:
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent":   "UAVWatcher/1.0 (shelter-lookup)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
    except Exception as exc:
        return [{"error": str(exc)}]

    shelters = []
    for el in result.get("elements", []):
        slat = el.get("lat", 0)
        slon = el.get("lon", 0)
        dist = int(_haversine(lat, lon, slat, slon))
        tags = el.get("tags", {})
        name = (
            tags.get("name")
            or tags.get("shelter_type")
            or tags.get("civil_protection")
            or ("Метро" if tags.get("station") == "subway" else None)
            or ("Підземний паркінг" if tags.get("parking") == "underground" else None)
            or "Укриття"
        )
        # Add shelter type label for metro/parking
        if tags.get("station") == "subway":
            shelter_type_label = "metro"
        elif tags.get("parking") == "underground":
            shelter_type_label = "underground_parking"
        else:
            shelter_type_label = tags.get("shelter_type", tags.get("civil_protection", "public"))
        addr = (tags.get("addr:street", "") + " " + tags.get("addr:housenumber", "")).strip()
        shelters.append({
            "dist":    dist,
            "name":    name,
            "addr":    addr or tags.get("description", ""),
            "type":    shelter_type_label,
            "lat":     slat,
            "lon":     slon,
            "osm_id":  el.get("id"),
        })
    shelters.sort(key=lambda x: x["dist"])
    shelters = shelters[:8]
    _shelter_cache[cache_key] = {"ts": time.time(), "shelters": shelters}
    return shelters


def send_sos_telegram(cfg: dict, lat, lon) -> bool:
    """Send SOS Telegram message with coordinates. Returns True on success."""
    token   = cfg.get("bot_token", "")
    chat_id = cfg.get("notify_chat_id")
    if not token or not chat_id:
        return False
    import time as _time
    ts       = _time.strftime("%H:%M %d.%m.%Y")
    city     = cfg.get("city", "невідомо")
    tun_url  = cfg.get("tunnel_url", "")
    coords   = f"{lat:.5f}, {lon:.5f}" if lat else "невідомо"
    maps_url = f"https://maps.google.com/?q={lat},{lon}" if lat else ""

    lines = [
        "\U0001F198 *SOS \u2014 \u041b\u044e\u0434\u0438\u043d\u0430 \u043f\u0456\u0434 \u0437\u0430\u0432\u0430\u043b\u043e\u043c!*",
        "",
        f"\U0001F4CD \u041a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u0438: `{coords}`",
    ]
    if maps_url:
        lines.append(f"\U0001F5FA [\u0412\u0456\u0434\u043a\u0440\u0438\u0442\u0438 \u043d\u0430 \u043a\u0430\u0440\u0442\u0456]({maps_url})")
    lines += [
        f"\U0001F3D9 \u041c\u0456\u0441\u0442\u043e: {city}",
        f"\u23F0 {ts}",
    ]
    if tun_url:
        lines.append(f"\U0001F517 [\u0412\u0435\u0431-\u0456\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441]({tun_url}/share)")
    lines += [
        "",
        "\u26A0\uFE0F \u0417\u0430\u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0443\u0439\u0442\u0435 \u0440\u044f\u0442\u0456\u0432\u043d\u0438\u043a\u0430\u043c: *101*",
    ]
    text = "\n".join(lines)
    body = json.dumps({
        "chat_id": chat_id, "text": text,
        "parse_mode": "Markdown", "disable_web_page_preview": True,
    }, ensure_ascii=False).encode()
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
        return result.get("ok", False)
    except Exception:
        return False


def send_sos_to_peers(cfg: dict, lat, lon):
    """POST SOS relay to all configured rescue_peers."""
    peers = cfg.get("rescue_peers", [])
    if not peers:
        return
    body = json.dumps({
        "lat": lat, "lon": lon,
        "city": cfg.get("city", ""),
        "tunnel_url": cfg.get("tunnel_url", ""),
    }, ensure_ascii=False).encode()
    def _post_peer(peer_url):
        try:
            url = peer_url.rstrip("/") + "/api/sos-relay"
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json",
                "User-Agent": "UAVWatcher-Rescue/1.0",
            })
            urllib.request.urlopen(req, timeout=8)
        except Exception:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(peers)) as executor:
        futures = [executor.submit(_post_peer, url) for url in peers]
        concurrent.futures.wait(futures, timeout=10)


def get_bot_info() -> tuple:
    """Return (username, t.me/username) from Telegram getMe, or (None, None)."""
    cfg   = load_config()
    token = cfg.get("bot_token", "")
    if not token:
        return None, None
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        if data.get("ok"):
            uname = data["result"].get("username", "")
            if uname:
                return uname, f"https://t.me/{uname}"
    except Exception:
        pass
    return None, None


def shelter_ai_query(user_msg: str, context: str) -> str:
    """Ask LLM proxy about shelters and safety. Returns AI reply text."""
    cfg     = load_config()
    base    = cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "").replace("/chat/completions", "").rstrip("/")
    api_key = cfg.get("llm_proxy_token") or cfg.get("goclaw_api_key", "")
    model   = cfg.get("llm_proxy_model") or cfg.get("goclaw_model", "gpt-4o-mini")
    url     = (base.rstrip("/") + "/chat/completions") if base else ""
    if not url:
        return "AI-консультант не налаштовано. Вкажіть LLM Proxy URL у налаштуваннях."
    system = (
        "Ти — асистент цивільної безпеки для жителів України. "
        "Допомагаєш знайти найближче укриття, пояснюєш правила поведінки під час повітряних тривог. "
        "Якщо є список укриттів — використовуй їх у відповіді. "
        "Рівні загрози: БАЛІСТИКА/РАКЕТИ — КРИТИЧНИЙ (підземне укриття негайно). "
        "ДРОНИ — ВИСОКИЙ (укриття або внутрішні кімнати). "
        "АРТИЛЕРІЯ — СЕРЕДНІЙ (укриття, подалі від вікон). "
        "ЗАГАЛЬНА ТРИВОГА — СЕРЕДНІЙ. Давай конкретні, практичні поради."
    )
    body = json.dumps({
        "model":    model,
        "messages": [
            {"role": "system",  "content": system},
            {"role": "user",    "content": f"{context}\n\n{user_msg}"},
        ],
        "max_tokens": 600,
    }, ensure_ascii=False).encode()
    try:
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent":    "curl/7.88.1",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        return result["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"Помилка AI: {exc}"


def _call_consultant(message: str, session_id: str = "web") -> str | None:
    """Call RAG consultant service (localhost:8770). Returns reply or None on failure."""
    import urllib.request as _ureq
    import json as _json
    try:
        payload = _json.dumps({"message": message, "session_id": session_id}).encode()
        req = _ureq.Request(
            "http://localhost:8770/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with _ureq.urlopen(req, timeout=30) as r:
            result = _json.loads(r.read())
            return result.get("reply") or None
    except Exception:
        return None


def cf_random_prefix(n=5):
    return "".join(_random.choices(_string.ascii_lowercase, k=n))


SHARE_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sharon — Укриття & Тривоги</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.topbar{background:#1e293b;padding:12px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #334155}
.logo{font-size:22px}
.site-title{font-weight:700;font-size:1.05rem;color:#f8fafc}
.city-badge{margin-left:auto;background:#0ea5e9;color:#fff;border-radius:20px;padding:3px 12px;font-size:.78rem}
.container{max-width:600px;margin:0 auto;padding:16px}
.card{background:#1e293b;border-radius:12px;padding:16px;margin-bottom:14px;border:1px solid #334155}
.card-title{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;margin-bottom:10px}
.status-row{display:flex;align-items:center;gap:8px}
.dot{width:10px;height:10px;border-radius:50%;background:#22c55e;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.status-text{font-size:.95rem;color:#e2e8f0}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:none;border-radius:8px;padding:11px 18px;font-size:.95rem;font-weight:600;cursor:pointer;transition:opacity .15s}
.btn:hover{opacity:.85}
.btn-tg{background:#0088cc;color:#fff;width:100%}
.btn-geo{background:#334155;color:#e2e8f0;width:100%}
.btn-send{background:#0ea5e9;color:#fff;padding:9px 16px}
.tg-note{font-size:.8rem;color:#94a3b8;margin-top:8px;text-align:center}
.shelter-list{list-style:none;margin-top:8px}
.shelter-item{background:#0f172a;border-radius:8px;padding:10px 12px;margin-bottom:6px;display:flex;gap:10px;align-items:flex-start}
.shelter-dist{background:#334155;border-radius:6px;padding:2px 8px;font-size:.78rem;white-space:nowrap;color:#94a3b8;margin-top:2px}
.shelter-name{font-weight:600;font-size:.9rem;margin-bottom:2px}
.shelter-addr{font-size:.78rem;color:#94a3b8}
.shelter-map{font-size:.78rem;color:#38bdf8;text-decoration:none;display:inline-block;margin-top:3px}
.no-shelter{color:#f59e0b;font-size:.88rem;padding:8px 0}
.chat-messages{max-height:280px;overflow-y:auto;margin-bottom:10px;display:flex;flex-direction:column;gap:8px}
.msg{padding:9px 12px;border-radius:8px;font-size:.88rem;line-height:1.45}
.msg-user{background:#1d4ed8;align-self:flex-end;max-width:85%;border-radius:8px 8px 2px 8px}
.msg-ai{background:#334155;align-self:flex-start;max-width:85%;border-radius:8px 8px 8px 2px}
.chat-input-row{display:flex;gap:8px}
.chat-input{flex:1;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;padding:9px 12px;font-size:.88rem;resize:none}
.chat-input:focus{outline:none;border-color:#0ea5e9}
.loading{color:#94a3b8;font-size:.8rem;text-align:center;padding:6px}
.threat-hint{font-size:.78rem;color:#64748b;margin-top:6px}

/* ── Rescue signal ── */
.rescue-card{border-color:#7f1d1d;transition:border-color .3s,background .3s}
.rescue-card.armed{background:#1c0a0a;border-color:#dc2626;animation:rescue-pulse 2s infinite}
.rescue-card.sos-active{background:#1a0000;border-color:#ef4444}
@keyframes rescue-pulse{0%,100%{border-color:#dc2626}50%{border-color:#f87171}}
.rescue-hint{font-size:.82rem;color:#94a3b8;margin-bottom:12px;line-height:1.5}
.btn-arm{background:#7f1d1d;color:#fca5a5;width:100%;font-size:1rem;padding:14px;letter-spacing:.04em}
.btn-arm:hover{background:#991b1b}
.btn-sos{background:#dc2626;color:#fff;width:100%;font-size:1.05rem;padding:14px;margin-bottom:8px;animation:sos-blink 1s infinite}
@keyframes sos-blink{0%,100%{background:#dc2626}50%{background:#ef4444}}
.btn-disarm{background:#1e293b;color:#94a3b8;width:100%;border:1px solid #334155}
.rescue-status-row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.rescue-dot{width:12px;height:12px;border-radius:50%;background:#dc2626;flex-shrink:0;animation:pulse 1s infinite}
.rescue-status-text{font-size:.9rem;color:#fca5a5}
.countdown-bar{height:4px;background:#334155;border-radius:2px;margin-bottom:10px;overflow:hidden}
.countdown-fill{height:100%;background:#dc2626;transition:width 1s linear;border-radius:2px}
.sos-overlay{position:fixed;inset:0;background:#1a0000;z-index:999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px}
.sos-title{font-size:3rem;font-weight:900;color:#ef4444;letter-spacing:.15em;animation:sos-blink 0.6s infinite}
.sos-coords-box{background:#2d0000;border:1px solid #dc2626;border-radius:10px;padding:12px 20px;text-align:center}
.sos-coords-text{font-family:monospace;font-size:.9rem;color:#fca5a5}
.sos-maps-link{color:#f87171;text-decoration:none;font-size:.82rem;display:block;margin-top:6px}
.sos-sent-badge{background:#166534;color:#86efac;border-radius:6px;padding:6px 14px;font-size:.8rem}
.btn-cancel-sos{background:#334155;color:#e2e8f0;border-radius:8px;padding:12px 28px;font-size:.95rem;font-weight:600;border:none;cursor:pointer}
.manual-trigger{background:none;border:1px dashed #475569;color:#64748b;border-radius:6px;padding:6px 12px;font-size:.75rem;cursor:pointer;margin-top:6px;width:100%}
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">&#9889;</span>
  <div>
    <div class="site-title">Sharon</div>
  </div>
  <span class="city-badge" id="cityBadge">{{CITY}}</span>
</div>
<div class="container">

  <!-- Status card -->
  <div class="card">
    <div class="card-title">Статус моніторингу</div>
    <div class="status-row">
      <div class="dot"></div>
      <div class="status-text">Активний · {{CHANNEL_COUNT}} каналів відслідковується</div>
    </div>
  </div>

  <!-- Telegram card -->
  <div class="card">
    <div class="card-title">Отримувати сповіщення</div>
    <button class="btn btn-tg" id="tgBtn" onclick="connectTg()">
      &#9992;&#65039; Підключити Telegram бот
    </button>
    <p class="tg-note" id="tgNote"></p>
  </div>

  <!-- Shelter card -->
  <div class="card">
    <div class="card-title">&#127968; Найближчі укриття</div>
    <button class="btn btn-geo" id="geoBtn" onclick="findShelters()">
      &#128205; Визначити місцезнаходження
    </button>
    <ul class="shelter-list" id="shelterList"></ul>
  </div>

  <!-- AI chat card -->
  <div class="card">
    <div class="card-title">&#129302; AI-консультант (безпека)</div>
    <div class="chat-messages" id="chatMessages">
      <div class="msg msg-ai">Вітаю! Я можу допомогти знайти найближче укриття та пояснити правила поведінки під час тривоги. Спитайте мене про безпеку або натисніть кнопку визначення місця &#8593;</div>
    </div>
    <div class="chat-input-row">
      <textarea class="chat-input" id="chatInput" rows="2" placeholder="Запитайте про укриття, тривогу..."></textarea>
      <button class="btn btn-send" onclick="sendChat()">&#10148;</button>
    </div>
    <div class="threat-hint">БАЛІСТИКА = критичний рівень · ДРОНИ = високий · АРТИЛЕРІЯ = середній</div>
  </div>

  <!-- Rescue signal card -->
  <div class="card rescue-card" id="rescueCard">
    <div class="card-title">&#9888;&#65039; Сигнал рятувальника</div>
    <div id="rescueIdle">
      <p class="rescue-hint">Увімкніть захист перед входом у небезпечну зону. При ударі та нерухомості 30+ с — автоматично подасть звуковий сигнал SOS та надішле координати рятувальникам і сусіднім станціям Sharon.</p>
      <button class="btn btn-arm" onclick="armRescue()">&#128737;&#65039; Увімкнути захист</button>
    </div>
    <div id="rescueArmed" style="display:none">
      <div class="rescue-status-row">
        <div class="rescue-dot"></div>
        <div class="rescue-status-text" id="rescueStatusText">Захист активний — очікування удару</div>
      </div>
      <div class="countdown-bar" id="countdownBarWrap" style="display:none">
        <div class="countdown-fill" id="countdownFill" style="width:100%"></div>
      </div>
      <button class="btn btn-sos" onclick="triggerSOS()">&#128680; НАДІСЛАТИ SOS ЗАРАЗ</button>
      <button class="btn btn-disarm" onclick="disarmRescue()">Вимкнути захист</button>
      <button class="manual-trigger" onclick="triggerSOS()">Немає руху датчика — надіслати вручну</button>
    </div>
  </div>

  <!-- SOS full-screen overlay (shown when SOS active) -->
  <div class="sos-overlay" id="sosOverlay" style="display:none">
    <div class="sos-title">S&#183;O&#183;S</div>
    <div class="sos-coords-box">
      <div class="sos-coords-text" id="sosCoordsText">Визначення координат...</div>
      <a class="sos-maps-link" id="sosMapsLink" href="#" target="_blank">&#128205; Відкрити на Google Maps</a>
    </div>
    <div id="sosSentBadge" style="display:none" class="sos-sent-badge">&#10003; Сигнал надіслано</div>
    <button class="btn-cancel-sos" onclick="cancelSOS()">Скасувати SOS</button>
  </div>

</div>
<script>
let _shelterContext = '';

async function connectTg() {
  const btn = document.getElementById('tgBtn');
  const note = document.getElementById('tgNote');
  btn.disabled = true;
  btn.textContent = 'Завантаження...';
  try {
    const r = await fetch('/api/bot-info');
    const d = await r.json();
    if (d.username) {
      btn.textContent = '@' + d.username;
      btn.onclick = () => window.open(d.url + '?start=subscribe', '_blank');
      note.textContent = 'Натисніть кнопку, потім надішліть /start боту щоб отримувати сповіщення';
    } else {
      btn.textContent = 'Бот не налаштований';
    }
  } catch(e) {
    btn.textContent = `Помилка з'єднання`;
  }
}

async function findShelters() {
  const btn = document.getElementById('geoBtn');
  const list = document.getElementById('shelterList');
  btn.disabled = true;
  btn.textContent = '⏳ Визначення...';
  list.innerHTML = '';

  if (!navigator.geolocation) {
    list.innerHTML = '<li class="no-shelter">Geolocation не підтримується браузером</li>';
    btn.disabled = false; btn.textContent = '📍 Визначити місцезнаходження';
    return;
  }

  navigator.geolocation.getCurrentPosition(async pos => {
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;
    btn.textContent = `📍 ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    try {
      const r  = await fetch('/api/shelter', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lat, lon})
      });
      const d = await r.json();
      if (!d.shelters || d.shelters.length === 0) {
        list.innerHTML = '<li class="no-shelter">⚠️ Укриттів у базі OSM не знайдено поблизу. Зверніться до місцевої влади або використовуйте підвальні приміщення.</li>';
        _shelterContext = `Координати користувача: ${lat.toFixed(5)}, ${lon.toFixed(5)}. Укриттів у базі OSM не знайдено в радіусі 3 км.`;
      } else {
        _shelterContext = `Координати користувача: ${lat.toFixed(5)}, ${lon.toFixed(5)}. Знайдені укриття:
` +
          d.shelters.map(s => `- ${s.name} (${s.dist}м): ${s.addr || 'адреса невідома'}`).join('
');
        d.shelters.forEach(s => {
          const li = document.createElement('li');
          li.className = 'shelter-item';
          li.innerHTML = `
            <span class="shelter-dist">${s.dist}м</span>
            <div>
              <div class="shelter-name">${s.name}</div>
              ${s.addr ? `<div class="shelter-addr">${s.addr}</div>` : ''}
              <a class="shelter-map" href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lon}&zoom=18" target="_blank">&#128205; Показати на карті</a>
            </div>`;
          list.appendChild(li);
        });
      }
      addMsg('ai', `Знайдено ${d.shelters ? d.shelters.length : 0} укриттів поблизу. Ви можете уточнити у чаті нижче ⬇`);
    } catch(e) {
      list.innerHTML = '<li class="no-shelter">Помилка запиту до сервера</li>';
    }
    btn.disabled = false;
  }, err => {
    list.innerHTML = '<li class="no-shelter">⚠️ Доступ до геолокації відхилено. Введіть своє місце у чаті.</li>';
    btn.disabled = false;
    btn.textContent = '📍 Визначити місцезнаходження';
  });
}

function addMsg(role, text) {
  const box = document.getElementById('chatMessages');
  const d   = document.createElement('div');
  d.className = `msg msg-${role}`;
  d.textContent = text;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

async function sendChat() {
  const inp = document.getElementById('chatInput');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  addMsg('user', msg);
  const loading = document.createElement('div');
  loading.className = 'loading';
  loading.textContent = '⏳ Думаю...';
  document.getElementById('chatMessages').appendChild(loading);
  try {
    const r = await fetch('/api/shelter-chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg, context: _shelterContext})
    });
    const d = await r.json();
    loading.remove();
    addMsg('ai', d.reply || 'Помилка відповіді');
  } catch(e) {
    loading.remove();
    addMsg('ai', `Помилка зв'язку з сервером`);
  }
}

document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// ── Rescue signal ─────────────────────────────────────────────────────────────
let _armed = false, _sosActive = false;
let _userLat = null, _userLon = null;
let _peakAccel = 0, _lastImpact = null, _quietSince = null;
let _sosTimerId = null, _countdownSec = 30, _countdownRemain = 30;
let _audioCtx = null;

function armRescue() {
  _armed = true;
  document.getElementById('rescueIdle').style.display = 'none';
  document.getElementById('rescueArmed').style.display = '';
  document.getElementById('rescueCard').classList.add('armed');
  setRescueStatus('Захист активний — очікування удару');

  // Grab location silently
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      p => { _userLat = p.coords.latitude; _userLon = p.coords.longitude; },
      () => {}
    );
  }

  // Start motion watch
  if (typeof DeviceMotionEvent !== 'undefined') {
    if (typeof DeviceMotionEvent.requestPermission === 'function') {
      DeviceMotionEvent.requestPermission()
        .then(r => { if (r === 'granted') window.addEventListener('devicemotion', _onMotion); })
        .catch(() => {});
    } else {
      window.addEventListener('devicemotion', _onMotion);
    }
  }
}

function disarmRescue() {
  _armed = false;
  _lastImpact = null; _quietSince = null;
  clearInterval(_sosTimerId);
  window.removeEventListener('devicemotion', _onMotion);
  document.getElementById('rescueIdle').style.display = '';
  document.getElementById('rescueArmed').style.display = 'none';
  document.getElementById('countdownBarWrap').style.display = 'none';
  document.getElementById('rescueCard').classList.remove('armed');
}

function setRescueStatus(txt) {
  document.getElementById('rescueStatusText').textContent = txt;
}

function _onMotion(e) {
  if (!_armed || _sosActive) return;
  const a = e.accelerationIncludingGravity;
  if (!a) return;
  const mag = Math.sqrt((a.x||0)**2 + (a.y||0)**2 + (a.z||0)**2);

  if (mag > 22 && !_lastImpact) {
    _lastImpact = Date.now();
    _quietSince = null;
    setRescueStatus('⚠️ Удар виявлено — 30 с нерухомості → SOS');
  }

  if (_lastImpact) {
    if (mag < 2.5) {
      if (!_quietSince) { _quietSince = Date.now(); _startCountdown(); }
    } else if (mag > 5) {
      _quietSince = null;
      _cancelCountdown();
      setRescueStatus('Захист активний — рух виявлено, чекаю удару');
      _lastImpact = null;
    }
  }
}

function _startCountdown() {
  _countdownRemain = _countdownSec;
  const bar = document.getElementById('countdownFill');
  const wrap = document.getElementById('countdownBarWrap');
  wrap.style.display = '';
  bar.style.width = '100%';
  setRescueStatus(`SOS через ${_countdownRemain}с...`);
  clearInterval(_sosTimerId);
  _sosTimerId = setInterval(() => {
    _countdownRemain--;
    bar.style.width = (_countdownRemain / _countdownSec * 100) + '%';
    setRescueStatus(`SOS через ${_countdownRemain}с...`);
    if (_countdownRemain <= 0) { clearInterval(_sosTimerId); triggerSOS(); }
  }, 1000);
}

function _cancelCountdown() {
  clearInterval(_sosTimerId);
  document.getElementById('countdownBarWrap').style.display = 'none';
}

async function triggerSOS() {
  if (_sosActive) return;
  _sosActive = true;
  clearInterval(_sosTimerId);
  window.removeEventListener('devicemotion', _onMotion);

  // Show overlay
  const overlay = document.getElementById('sosOverlay');
  overlay.style.display = 'flex';
  document.getElementById('rescueCard').classList.add('sos-active');

  // Get final coords
  if (navigator.geolocation && !_userLat) {
    await new Promise(resolve => navigator.geolocation.getCurrentPosition(
      p => { _userLat = p.coords.latitude; _userLon = p.coords.longitude; resolve(); },
      () => resolve(), {timeout: 5000}
    ));
  }

  if (_userLat) {
    document.getElementById('sosCoordsText').textContent = `${_userLat.toFixed(5)}, ${_userLon.toFixed(5)}`;
    document.getElementById('sosMapsLink').href = `https://maps.google.com/?q=${_userLat},${_userLon}`;
  } else {
    document.getElementById('sosCoordsText').textContent = 'Координати недоступні';
    document.getElementById('sosMapsLink').style.display = 'none';
  }

  // Audio SOS
  _startSOSAudio();

  // Flash screen repeatedly
  _flashScreen();

  // Notify server
  try {
    const r = await fetch('/api/sos', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({lat: _userLat, lon: _userLon})
    });
    const d = await r.json();
    if (d.ok) {
      document.getElementById('sosSentBadge').style.display = '';
    }
  } catch(e) {}
}

function cancelSOS() {
  _sosActive = false;
  _armed = false;
  _stopSOSAudio();
  document.getElementById('sosOverlay').style.display = 'none';
  document.getElementById('rescueCard').classList.remove('armed','sos-active');
  document.getElementById('rescueArmed').style.display = 'none';
  document.getElementById('rescueIdle').style.display = '';
  _lastImpact = null; _quietSince = null;
}

function _startSOSAudio() {
  try {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    _sosLoop();
  } catch(e) {}
}

function _stopSOSAudio() {
  if (_audioCtx) { try { _audioCtx.close(); } catch(e) {} _audioCtx = null; }
}

function _sosLoop() {
  if (!_sosActive || !_audioCtx) return;
  const ctx = _audioCtx;
  const dot = 0.18, dash = 0.5, gap = 0.12, lg = 0.45, wg = 1.2;

  function beep(t, dur) {
    const osc = ctx.createOscillator();
    const g   = ctx.createGain();
    osc.type = 'square';
    osc.frequency.value = 900;
    g.gain.setValueAtTime(0.001, t);
    g.gain.exponentialRampToValueAtTime(0.85, t + 0.01);
    g.gain.setValueAtTime(0.85, t + dur - 0.02);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.connect(g); g.connect(ctx.destination);
    osc.start(t); osc.stop(t + dur);
  }

  let t = ctx.currentTime;
  for (let i = 0; i < 3; i++) { beep(t, dot); t += dot + gap; } t += lg;
  for (let i = 0; i < 3; i++) { beep(t, dash); t += dash + gap; } t += lg;
  for (let i = 0; i < 3; i++) { beep(t, dot); t += dot + gap; } t += wg;

  const total = (t - ctx.currentTime) * 1000;
  setTimeout(() => { if (_sosActive) _sosLoop(); }, total);
}

function _flashScreen() {
  if (!_sosActive) return;
  document.body.style.background = '#400';
  setTimeout(() => {
    if (_sosActive) { document.body.style.background = '#0f172a'; setTimeout(_flashScreen, 600); }
    else document.body.style.background = '#0f172a';
  }, 400);
}
</script>

</body>
</html>"""

HTML = """<!DOCTYPE html>
<html lang="uk" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sharon — Налаштування</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    /* Stitch: Tactical Operations Terminal palette */
    --bg: #060810;
    --surface: #0f172a;
    --surface-low: #191b24;
    --elevated: #0b0e16;
    --border: #1e293b;
    --border-focus: #38bdf8;
    --text: #e1e1ee;
    --muted: #e0c0b1;
    --dim: #a78b7d;
    --accent: #f97316;
    --primary: #ffb690;
    --blue: #7bd0ff;
    --red-vivid: #f43f5e;
    --green: #10b981;
    --font: 'Barlow Condensed', sans-serif;
    --mono: 'JetBrains Mono', monospace;
  }
  body {
    background-color: var(--bg);
    background-image: radial-gradient(circle, #1e293b 1px, transparent 1px);
    background-size: 24px 24px;
    color: var(--text);
    font-family: var(--mono);
    font-size: 13px;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* ── TOPBAR ── */
  .topbar {
    background: rgba(6,8,16,0.95);
    border-bottom: 1px solid var(--border-focus);
    padding: 0 16px;
    height: 56px;
    display: flex;
    align-items: center;
    gap: 8px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
  }
  @media (min-width: 640px) { .topbar { padding: 0 24px; gap: 12px; height: 64px; } }

  .dot {
    width: 14px; height: 14px; flex-shrink: 0; position: relative;
    display: flex; align-items: center; justify-content: center;
  }
  .dot::before {
    content: ''; width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); animation: reticle 2s infinite;
    position: relative; z-index: 1;
  }
  @keyframes reticle {
    0%   { box-shadow: 0 0 0 0 rgba(249,115,22,0.7); }
    70%  { box-shadow: 0 0 0 10px rgba(249,115,22,0); }
    100% { box-shadow: 0 0 0 0 rgba(249,115,22,0); }
  }

  .topbar-title {
    font-family: var(--font); font-size: 15px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase; color: var(--text);
    white-space: nowrap;
  }
  @media (min-width: 640px) { .topbar-title { font-size: 20px; } }

  .topbar-sub {
    font-family: var(--mono); font-size: 10px; color: var(--dim);
    margin-left: 2px; display: none;
  }
  @media (min-width: 900px) { .topbar-sub { display: inline; } }

  .status-pill {
    margin-left: auto; padding: 3px 10px; border-radius: 2px;
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase; white-space: nowrap; flex-shrink: 0;
  }
  .status-pill.ok  { background: rgba(5,46,22,0.6);  border: 1px solid #166534; color: #4ade80; }
  .status-pill.err { background: rgba(69,10,10,0.6); border: 1px solid #991b1b; color: #fca5a5; }

  /* ── LAYOUT ── */
  .layout {
    display: flex; flex-direction: column;
    max-width: 1200px; margin: 0 auto;
    padding: 16px; gap: 16px; align-items: stretch;
  }
  @media (min-width: 768px) {
    .layout { flex-direction: row; padding: 24px; align-items: flex-start; }
  }
  .col-main { width: 100%; flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
  .col-side  { width: 100%; display: flex; flex-direction: column; gap: 16px; }
  @media (min-width: 768px) { .col-side { width: 300px; flex-shrink: 0; } }

  /* ── CARDS ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--accent);
    border-radius: 2px; overflow: hidden;
  }
  /* Section navigation */
  .section-nav {
    position: sticky; top: 0; z-index: 100;
    background: rgba(10,10,15,0.96); backdrop-filter: blur(8px);
    border-bottom: 1px solid rgba(245,158,11,0.18);
    display: flex; gap: 4px; padding: 8px 16px; flex-wrap: wrap;
    margin: -4px -4px 20px -4px;
  }
  .section-nav a {
    color: rgba(255,255,255,0.55); text-decoration: none;
    padding: 5px 11px; border-radius: 6px; font-size: 12px;
    transition: all 0.15s; border: 1px solid transparent; white-space: nowrap;
  }
  .section-nav a:hover { color: #f59e0b; border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.08); }
  .sec-divider {
    margin: 28px 0 16px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex; align-items: center; gap: 10px;
  }
  .sec-divider::before { content:''; width:3px; height:15px; border-radius:2px; background:var(--sc,#f59e0b); }
  .sec-divider span { font-size:10px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:rgba(255,255,255,0.3); }
  .ollama-st { display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:6px; margin:8px 0; font-size:13px; }
  .ollama-st.check { background:rgba(99,102,241,0.1); color:#a5b4fc; }
  .ollama-st.ok    { background:rgba(16,185,129,0.1);  color:#34d399; }
  .ollama-st.fail  { background:rgba(239,68,68,0.08);  color:#f87171; }
  .m-opt { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border:1px solid rgba(255,255,255,0.1); border-radius:8px; margin:4px 0; cursor:pointer; transition:all .15s; }
  .m-opt:hover { border-color:#f59e0b; background:rgba(245,158,11,0.06); }
  .m-opt .mn { font-weight:600; font-size:13px; }
  .m-opt .mm { font-size:11px; color:rgba(255,255,255,0.4); }

  .card-header {
    padding: 11px 16px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
    background: rgba(0,0,0,0.22);
  }
  .card-title {
    font-family: var(--font); font-size: 12px; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted);
  }
  .card-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

  /* ── FORMS ── */
  label {
    display: block; font-family: var(--mono); font-size: 9px; font-weight: 600;
    color: var(--dim); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 5px;
  }
  input[type=text], input[type=tel], input[type=password], textarea {
    width: 100%; padding: 9px 12px;
    background: var(--elevated); border: 1px solid var(--border); border-radius: 2px;
    color: var(--text); font-family: var(--mono); font-size: 16px;
    outline: none; transition: border-color 0.15s, box-shadow 0.15s;
  }
  @media (min-width: 768px) {
    input[type=text], input[type=tel], input[type=password], textarea { font-size: 12px; }
  }
  input:focus, textarea:focus {
    border-color: var(--border-focus);
    box-shadow: 0 0 0 1px var(--border-focus);
  }
  input::placeholder, textarea::placeholder { color: rgba(167,139,125,0.45); }
  textarea { resize: vertical; min-height: 70px; line-height: 1.5; }

  /* ── BUTTONS ── */
  .btn {
    height: 40px; padding: 0 18px; border-radius: 2px; border: none;
    font-family: var(--font); font-size: 13px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    cursor: pointer; transition: opacity 0.12s, transform 0.1s, background 0.15s;
    white-space: nowrap; min-height: 44px;
  }
  .btn:active { transform: scale(0.96); }
  .btn-primary { background: var(--accent); color: #060810; }
  .btn-primary:hover { opacity: 0.88; }
  .btn-ghost  { background: transparent; border: 1px solid var(--border-focus); color: var(--border-focus); }
  .btn-ghost:hover  { background: rgba(56,189,248,0.1); }
  .btn-danger { background: transparent; border: 1px solid #991b1b; color: #f87171; }
  .btn-danger:hover { background: rgba(153,27,27,0.15); }
  .btn-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  /* ── HINTS ── */
  .hint { font-family: var(--mono); font-size: 10px; color: var(--dim); line-height: 1.7; }
  .hint a { color: var(--primary); text-decoration: none; }
  .hint a:hover { text-decoration: underline; }
  .hint code {
    background: var(--bg); padding: 1px 5px; border-radius: 1px;
    font-size: 10px; color: var(--blue); border: 1px solid var(--border);
  }

  /* ── STEPS ── */
  .step-list { display: flex; flex-direction: column; gap: 10px; }
  .step { display: flex; gap: 10px; align-items: flex-start; }
  .step-num {
    width: 22px; height: 22px; border-radius: 2px;
    background: rgba(249,115,22,0.15); border: 1px solid rgba(249,115,22,0.35);
    display: flex; align-items: center; justify-content: center;
    font-family: var(--mono); font-size: 10px; font-weight: 700; color: var(--accent);
    flex-shrink: 0;
  }
  .step-text { font-family: var(--mono); font-size: 11px; color: rgba(225,225,238,0.65); line-height: 1.6; }
  .step-text a { color: var(--blue); text-decoration: none; }
  .step-text a:hover { text-decoration: underline; }
  .step-text code { background: var(--bg); padding: 1px 5px; border-radius: 1px; color: var(--blue); border: 1px solid var(--border); }

  /* ── FLASH ── */
  .flash { padding: 10px 14px; border-radius: 2px; font-family: var(--mono); font-size: 11px; margin-bottom: 4px; }
  .flash.ok  { background: rgba(5,46,22,0.5);  border: 1px solid #166534; color: #4ade80; }
  .flash.err { background: rgba(69,10,10,0.5); border: 1px solid #991b1b; color: #fca5a5; }

  /* ── MISC ── */
  .separator { height: 1px; background: var(--border); }
  .tag { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 2px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); font-family: var(--mono); font-size: 10px; color: var(--dim); }
  .channel-id { font-family: var(--mono); font-size: 11px; color: var(--blue); }

  /* ── CHANNEL LIST ── */
  .ch-total { font-family: var(--mono); font-size: 10px; color: var(--primary); font-weight: 600; }
  .ch-section { padding: 10px 16px; }
  .ch-section-label { font-family: var(--font); font-size: 10px; font-weight: 700; letter-spacing: 0.16em; color: var(--dim); text-transform: uppercase; margin-bottom: 10px; }
  .ch-divider { height: 1px; background: var(--border); }

  .ch-row {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border: 1px solid var(--border); border-radius: 2px;
    margin-bottom: 6px; background: var(--bg); transition: border-color 0.15s;
  }
  .ch-row:hover { border-color: var(--border-focus); }
  .ch-row:last-child { margin-bottom: 0; }
  .ch-locked { opacity: 0.85; }

  /* Stitch-style pulse: box-shadow animation */
  .ch-pulse { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .ch-pulse-amber { background: var(--accent); animation: pulse-amber 2s infinite; }
  .ch-pulse-green  { background: var(--green);  animation: pulse-green  2s infinite; }
  @keyframes pulse-amber { 0%{box-shadow:0 0 0 0 rgba(249,115,22,0.7)} 70%{box-shadow:0 0 0 8px rgba(249,115,22,0)} 100%{box-shadow:0 0 0 0 rgba(249,115,22,0)} }
  @keyframes pulse-green  { 0%{box-shadow:0 0 0 0 rgba(16,185,129,0.7)} 70%{box-shadow:0 0 0 8px rgba(16,185,129,0)} 100%{box-shadow:0 0 0 0 rgba(16,185,129,0)} }

  .ch-info { flex: 1; min-width: 0; }
  .ch-name   { display: block; font-family: var(--mono); font-size: 12px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ch-handle { display: block; font-family: var(--mono); font-size: 10px; color: var(--dim); margin-top: 2px; }
  .ch-badge-sys {
    padding: 2px 8px; border-radius: 2px;
    background: rgba(249,115,22,0.15); border: 1px solid rgba(249,115,22,0.35);
    font-family: var(--font); font-size: 10px; font-weight: 700; color: var(--accent);
    letter-spacing: 0.14em; flex-shrink: 0; text-transform: uppercase;
  }
  .ch-remove {
    background: none; border: none; color: var(--dim); cursor: pointer;
    font-size: 16px; line-height: 1; padding: 2px 4px; transition: color 0.15s;
    flex-shrink: 0; min-width: 36px; min-height: 36px;
    display: flex; align-items: center; justify-content: center;
  }
  .ch-remove:hover { color: #f87171; }
  .ch-add-wrap { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
  .ch-add-row  { display: flex; gap: 8px; }
  .ch-input {
    flex: 1; min-width: 0; padding: 9px 12px;
    background: var(--elevated); border: 1px solid var(--border); border-radius: 2px;
    color: var(--text); font-family: var(--mono); font-size: 16px;
    outline: none; transition: border-color 0.15s;
  }
  @media (min-width: 768px) { .ch-input { font-size: 12px; } }
  .ch-input:focus { border-color: var(--border-focus); box-shadow: 0 0 0 1px var(--border-focus); }
  .ch-input::placeholder { color: rgba(167,139,125,0.45); }
  .ch-btn { height: 40px; min-height: 44px; font-size: 11px; }

  .ch-preview {
    background: var(--surface-low); border: 1px solid var(--border-focus);
    border-radius: 2px; padding: 10px 12px; display: flex; align-items: center; gap: 10px;
  }
  .ch-preview-name { font-family: var(--mono); font-size: 12px; color: var(--text); flex: 1; }
  .ch-preview-id   { font-family: var(--mono); font-size: 10px; color: var(--dim); }

  /* ── DETAILS/SUMMARY ── */
  details { border: none; }
  details[open] summary { color: var(--primary); }
  summary.steps-toggle {
    cursor: pointer; font-family: var(--font); font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.14em; color: var(--dim);
    list-style: none; display: flex; align-items: center; gap: 6px;
    padding: 4px 0; transition: color 0.15s; user-select: none;
  }
  summary.steps-toggle::before { content: '▶'; font-size: 8px; transition: transform 0.2s; display: inline-block; }
  details[open] summary.steps-toggle::before { transform: rotate(90deg); }
  summary.steps-toggle:hover { color: var(--text); }

  .test-ok  { background: rgba(5,46,22,0.5);  border: 1px solid #166534; color: #4ade80; padding: 8px 12px; border-radius: 2px; font-family: var(--mono); font-size: 10px; }
  .test-err { background: rgba(69,10,10,0.5); border: 1px solid #991b1b; color: #fca5a5; padding: 8px 12px; border-radius: 2px; font-family: var(--mono); font-size: 10px; }

  /* ── LANGUAGE SELECTOR ── */
  .lang-sel {
    display: flex; gap: 1px; margin-left: 6px;
    overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none;
    flex-shrink: 1;
  }
  .lang-sel::-webkit-scrollbar { display: none; }
  .lang-btn {
    background: none; border: none; cursor: pointer; font-size: 17px;
    padding: 3px 3px; border-radius: 2px; opacity: 0.35;
    transition: opacity 0.15s, transform 0.1s; line-height: 1;
    flex-shrink: 0; min-width: 32px; min-height: 32px;
    display: flex; align-items: center; justify-content: center;
  }
  .lang-btn:hover { opacity: 0.85; transform: scale(1.1); }
  .lang-btn.active { opacity: 1; }

  /* ── RTL ── */
  [dir="rtl"] .layout { flex-direction: column; }
  @media (min-width: 768px) { [dir="rtl"] .layout { flex-direction: row-reverse; } }
  [dir="rtl"] .topbar       { flex-direction: row-reverse; }
  [dir="rtl"] .lang-sel     { margin-left: 0; margin-right: 6px; }
  [dir="rtl"] .card-header  { flex-direction: row-reverse; }
  [dir="rtl"] .card-body    { direction: rtl; }
  [dir="rtl"] .btn-row      { flex-direction: row-reverse; }
  [dir="rtl"] .step         { flex-direction: row-reverse; }
  [dir="rtl"] .ch-row       { flex-direction: row-reverse; }
  [dir="rtl"] .ch-add-row   { flex-direction: row-reverse; }
  [dir="rtl"] .ch-section   { text-align: right; }
  [dir="rtl"] label         { text-align: right; }
  [dir="rtl"] input, [dir="rtl"] textarea { text-align: right; direction: rtl; }
  [dir="rtl"] .hint         { text-align: right; }
  [dir="rtl"] .step-text    { text-align: right; }

  /* ── CHAT TOGGLE BTN ── */
  .chat-toggle-btn {
    background: none; border: 1px solid rgba(56,189,248,0.2); border-radius: 4px;
    color: var(--blue); cursor: pointer; padding: 0 8px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    transition: background 0.15s, border-color 0.15s;
    height: 40px; min-width: 48px; flex-shrink: 0; gap: 1px;
  }
  .chat-toggle-btn .cat-icon { font-size: 20px; line-height: 1; }
  .chat-toggle-btn .cat-label { font-size: 9px; font-family: var(--mono); letter-spacing: 0.05em; opacity: 0.7; }
  .chat-toggle-btn:hover { background: rgba(56,189,248,0.1); border-color: var(--blue); }
  .chat-toggle-btn.active { background: rgba(249,115,22,0.15); border-color: var(--accent); color: var(--accent); }

  /* ── CHAT PANEL ── */
  .chat-panel {
    position: fixed; top: 0; right: 0; bottom: 0;
    width: 380px; background: #0c1018;
    border-left: 1px solid var(--border-focus);
    border-top: 2px solid var(--accent);
    display: flex; flex-direction: column; z-index: 300;
    transform: translateX(105%);
    transition: transform 0.28s cubic-bezier(0.2,0,0,1);
    box-shadow: -4px 0 24px rgba(0,0,0,0.5);
  }
  @media (max-width: 640px) {
    .chat-panel {
      width: 100%; top: auto; height: 72vh;
      border-left: none; border-top: 2px solid var(--accent);
      transform: translateY(105%);
      transition: transform 0.28s cubic-bezier(0.2,0,0,1);
    }
    .chat-panel.open { transform: translateY(0); }
  }
  @media (min-width: 641px) { .chat-panel.open { transform: translateX(0); } }

  .chat-header {
    padding: 12px 16px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
    background: rgba(0,0,0,0.25); flex-shrink: 0;
  }
  .chat-header-icon { color: var(--accent); display: flex; }
  .chat-header-title {
    font-family: var(--font); font-size: 12px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); flex: 1;
  }
  .chat-header-sub { font-family: var(--mono); font-size: 9px; color: var(--dim); }
  .chat-close {
    background: none; border: none; color: var(--dim); cursor: pointer;
    font-size: 14px; padding: 6px 8px; border-radius: 2px; line-height: 1;
    min-width: 32px; min-height: 32px; display: flex; align-items: center; justify-content: center;
    transition: color 0.15s;
  }
  .chat-close:hover { color: var(--text); }

  .chat-messages {
    flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px;
    scrollbar-width: thin; scrollbar-color: var(--border) transparent;
  }
  .chat-msg {
    max-width: 88%; padding: 10px 13px; border-radius: 2px;
    font-family: var(--mono); font-size: 11px; line-height: 1.65;
  }
  .chat-msg-user {
    background: rgba(249,115,22,0.1); border: 1px solid rgba(249,115,22,0.22);
    color: var(--primary); align-self: flex-end;
  }
  .chat-msg-bot {
    background: var(--surface); border: 1px solid var(--border);
    color: var(--text); align-self: flex-start; white-space: pre-wrap;
  }
  .chat-msg-bot strong { color: #fff; font-weight: 600; }
  .chat-msg-title {
    font-family: var(--font); font-size: 11px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent);
    margin-bottom: 6px; display: block;
  }

  .chat-chips {
    padding: 8px 12px 4px; display: flex; flex-wrap: wrap; gap: 5px;
    border-top: 1px solid var(--border); flex-shrink: 0; background: rgba(0,0,0,0.1);
  }
  .chat-chip {
    font-family: var(--font); font-size: 10px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    padding: 5px 9px; border-radius: 2px; border: none;
    background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.2);
    color: var(--blue); cursor: pointer; transition: background 0.15s, transform 0.1s;
    white-space: nowrap;
  }
  .chat-chip:hover  { background: rgba(56,189,248,0.16); }
  .chat-chip:active { transform: scale(0.96); }

  .chat-input-row {
    display: flex; gap: 8px; padding: 10px 12px;
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
  .chat-text-input {
    flex: 1; padding: 9px 12px; background: var(--elevated);
    border: 1px solid var(--border); border-radius: 2px;
    color: var(--text); font-family: var(--mono); font-size: 16px; outline: none;
    transition: border-color 0.15s;
  }
  @media (min-width: 768px) { .chat-text-input { font-size: 12px; } }
  .chat-text-input:focus { border-color: var(--border-focus); }
  .chat-text-input::placeholder { color: rgba(167,139,125,0.4); }
  .chat-send-btn { height: 40px; width: 44px; padding: 0; font-size: 15px; min-height: 44px; flex-shrink: 0; }

  /* ── TYPING INDICATOR ── */
  .chat-typing { display: inline-flex; gap: 5px; align-items: center; padding: 4px 2px; }
  .chat-typing span {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--dim); display: inline-block;
    animation: typing-bounce 1.2s ease-in-out infinite;
  }
  .chat-typing span:nth-child(2) { animation-delay: 0.2s; }
  .chat-typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
    30% { transform: translateY(-7px); opacity: 1; }
  }

  /* Overlay backdrop on mobile */
  .chat-backdrop {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 299;
  }
  .chat-backdrop.show { display: block; }
</style>
</head>
<body>
<div class="topbar">
  <button class="chat-toggle-btn" onclick="toggleChat()" id="chat-toggle-btn" title="Шарон — кризовий гід">
    <span class="cat-icon">🐱</span>
    <span class="cat-label">Шарон</span>
  </button>
    <div class="dot"></div>
  <span class="topbar-title" data-i18n="title">UAV WATCHER</span>
  <span class="topbar-sub" data-i18n="subtitle">— система моніторингу БПЛА-загроз</span>
  <span class="status-pill {status_class}" data-state="{status_class}" data-i18n-state="status">{status_text}</span>
  <div class="lang-sel" id="lang-sel">
    <button class="lang-btn active" onclick="switchLang('uk')" title="Українська" data-lang="uk">🇺🇦</button>
    <button class="lang-btn" onclick="switchLang('en')" title="English" data-lang="en">🇬🇧</button>
    <button class="lang-btn" onclick="switchLang('de')" title="Deutsch" data-lang="de">🇩🇪</button>
    <button class="lang-btn" onclick="switchLang('fr')" title="Français" data-lang="fr">🇫🇷</button>
    <button class="lang-btn" onclick="switchLang('pl')" title="Polski" data-lang="pl">🇵🇱</button>
    <button class="lang-btn" onclick="switchLang('es')" title="Español" data-lang="es">🇪🇸</button>
    <button class="lang-btn" onclick="switchLang('tr')" title="Türkçe" data-lang="tr">🇹🇷</button>
    <button class="lang-btn" onclick="switchLang('ar')" title="العربية" data-lang="ar">🇸🇦</button>
    <button class="lang-btn" onclick="switchLang('fa')" title="فارسی" data-lang="fa">🇮🇷</button>
  </div>
</div>

<div class="layout">
  <div class="col-main">

    {flash_html}

    <nav class="section-nav">
      <a href="#sec-monitor">&#128225; Моніторинг</a>
      <a href="#sec-telegram">&#128241; Telegram</a>
      <a href="#sec-ai">&#129302; AI</a>
      <a href="#sec-system">&#9881; Система</a>
      <a href="#sec-security">&#128274; Безпека</a>
    </nav>

    <div id="sec-monitor" class="sec-divider" style="--sc:#3b82f6"><span>&#128225; Моніторинг міста та каналів</span></div>

    <!-- CITY CONFIG -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_city">🏙 Місто моніторингу</span></div>
      <form method="POST" action="/save-city">
      <div class="card-body">
        <div>
          <label>Швидкий вибір</label>
          <select name="preset" onchange="applyCityPreset(this.value)" style="width:100%;padding:8px;border-radius:6px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:.9rem">
            <option value="">— вручну —</option>
            {preset_options}
          </select>
        </div>
        <div>
          <label data-i18n="lbl_city">Назва міста</label>
          <input type="text" name="city" id="f_city" value="{city}" placeholder="Олександрія">
        </div>
        <div>
          <label data-i18n="lbl_region">Область</label>
          <input type="text" name="city_region" id="f_city_region" value="{city_region}" placeholder="Кіровоградська область">
        </div>
        <div>
          <label data-i18n="lbl_keywords">Ключові слова (через кому)</label>
          <input type="text" name="city_keywords" id="f_city_keywords" value="{city_keywords}" placeholder="Олександрія, Олександрійськ">
          <div class="hint" style="margin-top:5px" data-i18n="hint_keywords">Слова для попередньої фільтрації — якщо жодне не знайдено в тексті, AI не викликається.</div>
        </div>
        <div style="display:flex;gap:10px;margin-top:2px">
          <div style="flex:1"><label>Широта</label><input type="number" step="0.0001" name="city_lat" id="f_city_lat" value="{city_lat}" placeholder="48.6681"></div>
          <div style="flex:1"><label>Довгота</label><input type="number" step="0.0001" name="city_lon" id="f_city_lon" value="{city_lon}" placeholder="33.117"></div>
          <div style="flex:0 0 110px"><label>Радіус км</label><input type="number" name="city_radius_km" id="f_city_radius_km" value="{city_radius_km}" placeholder="30"></div>
        </div>
        <div class="hint" style="margin-top:4px">Порожні координати — визначаться автоматично через геокодер.</div>
        <script>
        var _CITY_PRESETS = {city_preset_js};
        function applyCityPreset(name) {
          if (!name) return;
          var p = _CITY_PRESETS[name];
          if (!p) return;
          document.getElementById('f_city').value = p.name;
          document.getElementById('f_city_region').value = p.region;
          document.getElementById('f_city_keywords').value = p.keywords.join(', ');
          document.getElementById('f_city_lat').value = p.lat;
          document.getElementById('f_city_lon').value = p.lon;
          document.getElementById('f_city_radius_km').value = p.radius_km;
        }
        </script>
        <div class="btn-row">
          <button type="submit" class="btn btn-primary" data-i18n="btn_save">Зберегти</button>
        </div>
      </div>
      </form>
    </div>

    <!-- CHANNELS -->
    <div class="card" id="channels-card">
      <div class="card-header" style="justify-content:space-between">
        <span class="card-title" data-i18n="card_channels">📡 Канали моніторингу</span>
        <span class="ch-total" id="ch-total"><span id="ch-total-num">{channel_total}</span> <span data-i18n="active">активних</span></span>
      </div>
      <div style="padding:0">

        <div class="ch-section">
          <div class="ch-section-label" data-i18n="sys_channel_label">🔒 СИСТЕМНИЙ — ЗАВЖДИ АКТИВНИЙ</div>
          <div class="ch-row ch-locked">
            <span class="ch-pulse ch-pulse-green"></span>
            <div class="ch-info">
              <span class="ch-name">Повітряні Сили ЗС України</span>
              <span class="ch-handle">@kpszsu · -1001223955273</span>
            </div>
            <span class="ch-badge-sys" title="Системний канал — завжди активний, не видаляється">SYSTEM ✓</span>
          </div>
        </div>

        <div class="ch-divider"></div>

        <div class="ch-section">
          <div class="ch-section-label"><span data-i18n="user_channels_label">📻 ВАШІ КАНАЛИ</span> <span id="user-ch-count" style="font-weight:400;opacity:0.6">{user_channel_count}</span></div>
          <div id="user-channels-list">
            {user_channels_html}
          </div>

          <div class="ch-add-wrap">
            <div class="ch-add-row">
              <input type="text" id="ch-input" class="ch-input" placeholder="@username або -1001234567890"
                data-i18n-placeholder="ch_placeholder"
              onkeydown="if(event.key==='Enter'){resolveChannel()}">
              <button class="btn btn-ghost ch-btn" onclick="resolveChannel()" id="ch-resolve-btn" style="white-space:nowrap" data-i18n="btn_check">Перевірити</button>
            </div>
            <div id="ch-preview" class="ch-preview" style="display:none"></div>
          </div>
        </div>

        <div class="ch-divider"></div>
        <div class="ch-section" style="padding-bottom:14px">
          <div class="hint">Знайти ID каналу: відкрий web.telegram.org → будь-який канал → число в URL після <code>-100</code>. Або напиши <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a> і перешли повідомлення з каналу.</div>
        </div>

      </div>
    </div>

    <div id="sec-telegram" class="sec-divider" style="--sc:#06b6d4"><span>&#128241; Telegram налаштування</span></div>

    <!-- TELEGRAM CREDENTIALS -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_tg_user">🔑 Telegram User Bot (Telethon)</span></div>
      <form method="POST" action="/save-env">
      <div class="card-body">
        <div class="step-list">
          <div class="step">
            <div class="step-num">1</div>
            <div class="step-text">Відкрий <a href="https://my.telegram.org/apps" target="_blank">my.telegram.org/apps</a>, увійди під своїм номером телефону</div>
          </div>
          <div class="step">
            <div class="step-num">2</div>
            <div class="step-text">Створи додаток (або використай існуючий). Скопіюй <code>App api_id</code> і <code>App api_hash</code></div>
          </div>
          <div class="step">
            <div class="step-num">3</div>
            <div class="step-text">Введи дані нижче — це телефон і ключі того Telegram-акаунту, від якого читатимуться канали</div>
          </div>
        </div>
        <div class="separator"></div>
        <div>
          <label data-i18n="lbl_phone">Номер телефону</label>
          <input type="tel" name="phone" value="{phone}" placeholder="+380501234567">
        </div>
        <div>
          <label>API ID</label>
          <input type="text" name="api_id" value="{api_id}" placeholder="12345678">
        </div>
        <div>
          <label>API Hash</label>
          <input type="text" name="api_hash" value="{api_hash}" placeholder="0a1b2c3d4e5f...">
        </div>
        <div class="btn-row">
          <button type="submit" class="btn btn-primary" data-i18n="btn_save">Зберегти</button>
          <span class="hint">Після збереження потрібно запустити <code>python3 auth.py</code> в терміналі для авторизації сесії</span>
        </div>
      </div>
      </form>
    </div>

  </div>

  <div class="col-side">

    <!-- USER ID INSTRUCTION -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_notify">📲 Куди надсилати сповіщення</span></div>
      <div class="card-body">
        <div class="hint" style="margin-bottom:10px;line-height:1.7">Сповіщення надходять у твій особистий чат із ботом. Потрібно спочатку <strong style="color:rgba(255,255,255,0.75)">відкрити свого бота в Telegram і натиснути /start</strong> — без цього кроку бот не зможе писати тобі.</div>
        <div class="step-list">
          <div class="step">
            <div class="step-num">1</div>
            <div class="step-text">Знайди свого бота в Telegram (по username який ти вказав у BotFather) → натисни <code>/start</code></div>
          </div>
          <div class="step">
            <div class="step-num">2</div>
            <div class="step-text">Дізнайся свій User ID — напиши <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a> або <a href="https://t.me/getmyid_bot" target="_blank">@getmyid_bot</a> → <code>/start</code></div>
          </div>
          <div class="step">
            <div class="step-num">3</div>
            <div class="step-text">Бот відповість числом — це твій <code>Chat ID</code>. Введи його нижче.</div>
          </div>
        </div>
        <div class="separator"></div>
        <form method="POST" action="/save-notify">
          <div>
            <label data-i18n="lbl_notify_id">Notify Chat ID (твій Telegram User ID)</label>
            <input type="text" name="notify_chat_id" value="{notify_chat_id}" placeholder="123456789">
          </div>
          <div class="btn-row" style="margin-top:8px">
            <button type="submit" class="btn btn-primary" style="height:30px;font-size:10px;" data-i18n="btn_save_chatid">Зберегти Chat ID</button>
          </div>
        </form>
      </div>
    </div>

    <div id="sec-system" class="sec-divider" style="--sc:#10b981"><span>&#9881; Система та сервіс</span></div>

    <!-- SERVICE CONTROL -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_service">⚙ Сервіс</span></div>
      <div class="card-body">
        <form method="POST" action="/restart">
          <button type="submit" class="btn btn-ghost" style="width:100%" data-i18n="btn_restart">↺ Перезапустити сервіс</button>
        </form>
        <div class="hint" data-i18n="hint_restart">Після зміни конфігурації або каналів — перезапусти сервіс.</div>
        <div class="separator"></div>
        <div class="hint">
          <strong style="color:rgba(255,255,255,0.6)" data-i18n="cur_state">Поточний стан:</strong><br>
          City: <code>{city}</code><br>
          Channels: <code>{channel_count}</code><br>
          Model: <code>{model}</code>
        </div>
      </div>
    </div>


    <div id="sec-ai" class="sec-divider" style="--sc:#f59e0b"><span>&#129302; AI / LLM Proxy</span></div>

    <!-- LLM PROXY SETTINGS -->
    <div class="card">
      <div class="card-header"><span class="card-title">&#129302; AI Proxy — LLM налаштування</span></div>
      <div class="card-body">
        <div class="hint" style="margin-bottom:12px">OpenAI-сумісний проксі для AI-консультанта. Вкажіть базову URL (без <code>/chat/completions</code>). Локальна модель без інтернету: <b>Ollama</b> URL=<code>http://localhost:11434/v1</code>, Token=<code>ollama</code>, Model=<code>qwen2:1.5b</code>.</div>
        <form method="POST" action="/save-llm">
          <div class="field-group">
            <label class="field-label">Proxy URL</label>
            <input class="input" name="llm_proxy_url" value="{llm_proxy_url}" placeholder="https://YOUR_PROXY_URL/v1">
          </div>
          <div class="field-group">
            <label class="field-label">API Token</label>
            <input class="input" type="password" name="llm_proxy_token" value="{llm_proxy_token}" placeholder="your-token (або freecc для публічного проксі)">
          </div>
          <div class="field-group">
            <label class="field-label">Model</label>
            <input class="input" name="llm_proxy_model" value="{llm_proxy_model}" placeholder="gpt-4o-mini">
          </div>
          <button type="submit" class="btn btn-primary">&#10003; Зберегти AI налаштування</button>
        </form>
      </div>
    </div>



    <!-- OLLAMA LOCAL MODEL -->
    <div class="card">
      <div class="card-header"><span class="card-title">&#127981; Ollama — локальна офлайн-модель</span></div>
      <div class="card-body">
        <div class="hint" style="margin-bottom:12px">
          Запусти AI без інтернету. <a href="https://ollama.ai" target="_blank" rel="noopener" style="color:#f59e0b">ollama.ai</a> — безкоштовно для Linux, Mac, Windows, Android (Termux).
          Моделі: <b>qwen2:0.5b</b> (400MB, слабкий пристрій), <b>qwen2:1.5b</b> (900MB), <b>phi3:mini</b> (2.2GB).
        </div>
        <div id="ollama-status" class="ollama-st check" style="display:none"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn" onclick="checkOllama()" id="ollama-check-btn">&#128269; Перевірити Ollama</button>
        </div>
        <div id="ollama-models" style="display:none">
          <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-bottom:8px">Оберіть модель (клік — встановить у налаштуваннях):</div>
          <div class="m-opt" onclick="selectOllamaModel('qwen2:0.5b','400MB')">
            <span class="mn">qwen2:0.5b</span><span class="mm">~400MB RAM • мінімальний пристрій</span>
          </div>
          <div class="m-opt" onclick="selectOllamaModel('qwen2:1.5b','900MB')">
            <span class="mn">qwen2:1.5b</span><span class="mm">~900MB RAM • рекомендовано</span>
          </div>
          <div class="m-opt" onclick="selectOllamaModel('phi3:mini','2.2GB')">
            <span class="mn">phi3:mini</span><span class="mm">~2.2GB RAM • якісніші відповіді</span>
          </div>
          <div class="m-opt" onclick="selectOllamaModel('llama3.2:1b','1.3GB')">
            <span class="mn">llama3.2:1b</span><span class="mm">~1.3GB RAM • Meta</span>
          </div>
        </div>
        <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:8px">
          Команди: <code>ollama serve</code> (запустити) &nbsp;|&nbsp; <code>ollama pull qwen2:1.5b</code> (завантажити)
        </div>
      </div>
    </div>

    <div id="sec-security" class="sec-divider" style="--sc:#ef4444"><span>&#128274; Безпека та доступ</span></div>

    <!-- SECURITY — admin password -->
    <div class="card">
      <div class="card-header"><span class="card-title">&#128274; Захист адмін-панелі</span></div>
      <div class="card-body">
        <div class="hint" style="margin-bottom:12px">HTTP Basic Auth для цієї сторінки. Якщо пароль порожній — захист вимкнено. /share та AI-чат доступні без пароля.</div>
        <form method="POST" action="/save-password">
          <div class="field-group">
            <label class="field-label">Новий пароль</label>
            <input class="input" type="password" name="admin_password" placeholder="залиш порожнім щоб вимкнути захист">
          </div>
          <div class="field-group">
            <label class="field-label">Підтвердити пароль</label>
            <input class="input" type="password" name="admin_password_confirm" placeholder="повтори пароль">
          </div>
          <button type="submit" class="btn btn-primary">&#128274; Зберегти пароль</button>
        </form>
        <div class="hint" style="margin-top:8px;color:rgba(239,68,68,0.8)">&#9888; Якщо забудеш пароль — відредагуй config.json на сервері (SSH).</div>
      </div>
    </div>

    <!-- BOT TOKEN -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_bot">🤖 Telegram Bot — сповіщувач</span></div>
      <div class="card-body">

        <details open>
          <summary class="steps-toggle" data-i18n="step_botfather_toggle">Як створити бота через BotFather</summary>
          <div class="steps-body">
            <div class="step-list" style="margin-top:10px">
              <div class="step">
                <div class="step-num">1</div>
                <div class="step-text">Відкрий Telegram і знайди бота <a href="https://t.me/BotFather" target="_blank">@BotFather</a> — натисни <code>/start</code></div>
              </div>
              <div class="step">
                <div class="step-num">2</div>
                <div class="step-text">Надішли команду <code>/newbot</code></div>
              </div>
              <div class="step">
                <div class="step-num">3</div>
                <div class="step-text">Введи назву бота (будь-яку, наприклад <code>Мій Sharon</code>)</div>
              </div>
              <div class="step">
                <div class="step-num">4</div>
                <div class="step-text">Введи username бота — латиницею, повинен закінчуватись на <code>_bot</code> (наприклад <code>my_uav_bot</code>)</div>
              </div>
              <div class="step">
                <div class="step-num">5</div>
                <div class="step-text">BotFather надішле токен вигляду <code>1234567890:AAEfzH9...</code> — скопіюй його</div>
              </div>
              <div class="step step-warn">
                <div class="step-num" style="background:rgba(239,68,68,0.15);border-color:rgba(239,68,68,0.35);color:var(--red)">!</div>
                <div class="step-text" style="color:rgba(255,120,120,0.85)">Знайди свого нового бота в Telegram і натисни <code>/start</code> — інакше бот не зможе надсилати тобі повідомлення</div>
              </div>
            </div>
          </div>
        </details>

        <div class="separator" style="margin:4px 0"></div>

        <form method="POST" action="/save-bot" id="bot-form">
          <div>
            <label>Bot Token</label>
            <input type="text" name="bot_token" value="{bot_token}" placeholder="1234567890:AAEfzH9fq4jM81gy...">
          </div>
          <div class="btn-row" style="margin-top:10px">
            <button type="submit" class="btn btn-primary" style="height:30px;font-size:10px;" data-i18n="btn_save_token">Зберегти токен</button>
            <button type="button" class="btn btn-ghost" style="height:30px;font-size:10px;" onclick="sendTest()" data-i18n="btn_test">▶ Тест</button>
          </div>
          <div id="test-result" style="margin-top:8px;display:none"></div>
        </form>

      </div>
    </div>

    <!-- TUNNEL / PUBLIC SHARE -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_tunnel">🔗 Публічний доступ</span></div>
      <div class="card-body">

        <div id="tun-unavail" style="display:none">
          <div class="hint" data-i18n="hint_tunnel_unavail">cloudflared не встановлено або облікові дані відсутні у папці <code>.cloudflared/</code>.</div>
        </div>

        <div id="tun-stopped">
          <div class="hint" style="margin-bottom:10px;line-height:1.7" data-i18n="hint_tunnel">Поділись посиланням з родиною — вони отримають сповіщення через ваш сервіс.</div>
          <div>
            <label data-i18n="lbl_prefix">Префікс URL</label>
            <div style="display:flex;gap:6px;margin-bottom:6px">
              <input type="text" id="tun-prefix" placeholder="kyiv" maxlength="20" oninput="tunUpdatePreview()"
                style="flex:1;padding:7px 10px;background:var(--elevated);border:1px solid var(--border);border-radius:3px;color:var(--text);font-family:var(--mono);font-size:12px;outline:none;transition:border-color .15s"
                onfocus="this.style.borderColor='var(--border2)'" onblur="this.style.borderColor='var(--border)'">
              <button class="btn btn-ghost" style="height:34px;font-size:18px;padding:0 10px" onclick="tunGenPrefix()" title="Згенерувати">⚂</button>
            </div>
          </div>
          <div class="hint" style="margin-bottom:8px">URL: <code id="tun-preview" style="color:var(--accent)">?????-alert.your-domain.example</code></div>
          <div id="tun-check-res" style="display:none;margin-bottom:8px"></div>
          <div class="btn-row" style="margin-bottom:4px">
            <button class="btn btn-primary" style="height:30px;font-size:10px" onclick="tunStart()" id="tun-start-btn" data-i18n="btn_tunnel_start">Запустити тунель</button>
            <button class="btn btn-ghost" style="height:30px;font-size:10px" onclick="tunCheck()" data-i18n="btn_prefix_check">Перевірити</button>
          </div>
          <div id="tun-start-err" style="display:none;margin-top:6px"></div>
        </div>

        <div id="tun-active" style="display:none">
          <div class="hint" style="margin-bottom:8px">🟢 <span data-i18n="tunnel_active">Тунель активний</span></div>
          <div style="text-align:center;margin-bottom:10px">
            <div id="tun-qr" style="display:inline-block;background:#fff;padding:8px;border-radius:4px"></div>
          </div>
          <div style="text-align:center;margin-bottom:10px;word-break:break-all">
            <a id="tun-url-link" href="#" target="_blank" style="font-family:var(--mono);font-size:10px;color:var(--accent);text-decoration:none" id="tun-url-display"></a>
          </div>
          <button class="btn btn-danger" style="height:30px;font-size:10px;width:100%" onclick="tunStop()" data-i18n="btn_tunnel_stop">Зупинити тунель</button>
        </div>

      </div>
    </div>


  </div>
</div>
<script>
// ── Channel management ──────────────────────────────────────────────────
let resolvedChannel = null;

async function resolveChannel() {
  const input = document.getElementById('ch-input');
  const preview = document.getElementById('ch-preview');
  const btn = document.getElementById('ch-resolve-btn');
  const val = input.value.trim();
  if (!val) return;

  btn.disabled = true;
  btn.textContent = '...';
  preview.style.display = 'none';
  resolvedChannel = null;

  try {
    const r = await fetch('/resolve-channel', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({handle: val})
    });
    const d = await r.json();
    if (d.ok) {
      resolvedChannel = d;
      preview.style.display = 'flex';
      preview.innerHTML = `
        <span class="ch-pulse ch-pulse-green" style="flex-shrink:0"></span>
        <span class="ch-preview-name">${d.title}</span>
        <span class="ch-preview-id">${d.username ? '@'+d.username+' · ' : ''}${d.id}</span>
        <button class="btn btn-primary ch-btn" onclick="addChannel()" style="height:28px;font-size:10px">+ Додати</button>`;
    } else {
      preview.style.display = 'flex';
      preview.innerHTML = `<span style="font-family:var(--mono);font-size:11px;color:var(--red)">${d.error}</span>`;
    }
  } catch(e) {
    preview.style.display = 'flex';
    preview.innerHTML = `<span style="font-family:var(--mono);font-size:11px;color:var(--red)">Помилка з'єднання</span>`;
  }
  btn.disabled = false;
  btn.textContent = (T[currentLang] || T['uk']).btn_check;
}

async function addChannel() {
  if (!resolvedChannel) return;
  const r = await fetch('/add-channel', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(resolvedChannel)
  });
  const d = await r.json();
  if (d.ok) {
    document.getElementById('ch-input').value = '';
    document.getElementById('ch-preview').style.display = 'none';
    resolvedChannel = null;
    refreshChannels();
  }
}

async function removeChannel(id) {
  const r = await fetch('/remove-channel', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: id})
  });
  const d = await r.json();
  if (d.ok) refreshChannels();
}

async function refreshChannels() {
  const r = await fetch('/api/channels');
  const d = await r.json();
  const list = document.getElementById('user-channels-list');
  const count = document.getElementById('user-ch-count');
  const total = document.getElementById('ch-total');
  const _t = T[currentLang] || T['uk'];
  list.innerHTML = d.user_channels.map(ch => channelRow(ch)).join('') || `<div style="padding:6px 0;font-family:var(--mono);font-size:10px;color:var(--dim)">${_t.no_channels}</div>`;
  count.textContent = d.user_channels.length;
  total.innerHTML = `<span id="ch-total-num">${d.user_channels.length + d.locked_count}</span> ${_t.active}`;
}

function channelRow(ch) {
  const handle = ch.username ? `@${ch.username} · ` : '';
  return `<div class="ch-row">
    <span class="ch-pulse ch-pulse-green"></span>
    <div class="ch-info">
      <span class="ch-name">${ch.title || ch.id}</span>
      <span class="ch-handle">${handle}${ch.id}</span>
    </div>
    <button class="ch-remove" onclick="removeChannel(${ch.id})" title="Видалити">×</button>
  </div>`;
}

// ── Test notification ────────────────────────────────────────────────────
async function sendTest() {
  const btn = event.target;
  const res = document.getElementById('test-result');
  btn.disabled = true;
  btn.textContent = '...';
  res.style.display = 'none';
  try {
    const r = await fetch('/send-test', {method:'POST'});
    const d = await r.json();
    res.style.display = 'block';
    res.className = d.ok ? 'test-ok' : 'test-err';
    res.textContent = d.message;
  } catch(e) {
    res.style.display = 'block';
    res.className = 'test-err';
    res.textContent = (T[currentLang] || T['uk']).err_connection;
  }
  btn.disabled = false;
  btn.textContent = (T[currentLang] || T['uk']).btn_test;
}

// ── Tunnel management ─────────────────────────────────────────────────────────
function tunUpdatePreview() {
  const v = (document.getElementById('tun-prefix').value.trim().toLowerCase() || '?????');
  document.getElementById('tun-preview').textContent = v + '-alert.your-domain.example';
}
function tunGenPrefix() {
  const p = Array.from({length:5}, () => 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random()*26)]).join('');
  document.getElementById('tun-prefix').value = p;
  tunUpdatePreview();
  document.getElementById('tun-check-res').style.display = 'none';
}
function _tunShowCheck(ok, msg) {
  const el = document.getElementById('tun-check-res');
  el.style.display = 'block';
  el.className = ok ? 'test-ok' : 'test-err';
  el.textContent = msg;
}
async function tunCheck() {
  const prefix = document.getElementById('tun-prefix').value.trim().toLowerCase();
  if (!prefix || !/^[a-z0-9-]{2,20}$/.test(prefix)) {
    _tunShowCheck(false, 'Тільки латинські літери, цифри і дефіс (2-20 символів)');
    return false;
  }
  _tunShowCheck(true, '...');
  try {
    const r = await fetch('/tunnel-check', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prefix})});
    const d = await r.json();
    if (!d.ok) { _tunShowCheck(false, d.error || 'Помилка'); return false; }
    if (d.conflict) { _tunShowCheck(false, d.hostname + ' — вже зайнято'); return false; }
    _tunShowCheck(true, d.hostname + ' — доступно ✓');
    return true;
  } catch(e) { _tunShowCheck(false, `Помилка з'єднання`); return false; }
}
async function tunStart() {
  const prefix = document.getElementById('tun-prefix').value.trim().toLowerCase();
  if (!prefix) { tunGenPrefix(); return; }
  const btn = document.getElementById('tun-start-btn');
  const errEl = document.getElementById('tun-start-err');
  btn.disabled = true; btn.textContent = '...'; errEl.style.display = 'none';
  try {
    const r = await fetch('/tunnel-start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prefix})});
    const d = await r.json();
    if (d.ok) {
      setTimeout(tunLoadStatus, 3000);
    } else {
      errEl.style.display = 'block'; errEl.className = 'test-err'; errEl.textContent = d.error;
      btn.disabled = false;
      btn.textContent = (T[currentLang]||T['uk']).btn_tunnel_start;
    }
  } catch(e) {
    errEl.style.display = 'block'; errEl.className = 'test-err';
    errEl.textContent = (T[currentLang]||T['uk']).err_connection;
    btn.disabled = false;
    btn.textContent = (T[currentLang]||T['uk']).btn_tunnel_start;
  }
}
async function tunStop() {
  await fetch('/tunnel-stop', {method:'POST'});
  tunLoadStatus();
}
async function tunLoadStatus() {
  try {
    const r = await fetch('/api/tunnel');
    const d = await r.json();
    const unavail = document.getElementById('tun-unavail');
    const stopped = document.getElementById('tun-stopped');
    const active  = document.getElementById('tun-active');
    if (!d.available) {
      unavail.style.display='block'; stopped.style.display='none'; active.style.display='none'; return;
    }
    unavail.style.display='none';
    if (d.running && d.url) {
      stopped.style.display='none'; active.style.display='block';
      const link = document.getElementById('tun-url-link');
      link.textContent = d.url; link.href = d.url;
      const qrEl = document.getElementById('tun-qr');
      qrEl.innerHTML = '';
      if (typeof QRCode !== 'undefined') {
        new QRCode(qrEl, {text: d.url, width: 160, height: 160, colorDark:'#000000', colorLight:'#ffffff'});
      }
    } else {
      active.style.display='none'; stopped.style.display='block';
      if (d.prefix) { document.getElementById('tun-prefix').value = d.prefix; tunUpdatePreview(); }
      const btn = document.getElementById('tun-start-btn');
      btn.disabled = false;
      btn.textContent = (T[currentLang]||T['uk']).btn_tunnel_start;
    }
  } catch(e) { console.error('tunLoadStatus', e); }
}

// ── CHAT CONSULTANT ──────────────────────────────────────────────────────────
let _chatOpen = false;
const _CHAT_WELCOME = `Привіт. Я Шарон — моніторю {city} 24/7.\nЯ тут, щоб ти вижив.\n\nПитай про загрози, укриття або що робити прямо зараз.`;

function toggleChat() {
  _chatOpen = !_chatOpen;
  const panel = document.getElementById('chat-panel');
  const btn   = document.getElementById('chat-toggle-btn');
  const bdrop = document.getElementById('chat-backdrop');
  panel.classList.toggle('open', _chatOpen);
  btn.classList.toggle('active', _chatOpen);
  bdrop.classList.toggle('show', _chatOpen);
  if (_chatOpen) {
    if (document.getElementById('chat-messages').children.length === 0) {
      _chatAddMsg('bot', '', _CHAT_WELCOME);
    }
    setTimeout(function(){ document.getElementById('chat-input').focus(); }, 320);
  }
}

function _mdToHtml(s) {
  // strip meta-label lines and hallucinated URLs the LLM may echo
  s = s.replace(/^\s*\[[^\]]+\][\s:]*(?:https?:\/\/\S+)?\s*$/mg, '').trim();
  s = s.replace(/^\s*\[[^\]]+\][\s:]*(?:https?:\/\/\S+)?\s*$/mg, '').trim();
  // strip bare URLs on their own line
  s = s.replace(/^\s*https?:\/\/\S+\s*$/mg, '').trim();
  // escape HTML to prevent XSS
  s = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // ### / ## / # headers -> bold
  s = s.replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>');
  // **bold**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // *text* -> italic
  s = s.replace(/\*([^*\\n]+)\*/g, '<strong>$1</strong>');
  // list items: "- text" at line start -> bullet
  s = s.replace(/^-\s+(.+)$/gm, '• $1');
  // paragraph breaks and newlines
  s = s.replace(/\\n\\n/g, '<br><br>').replace(/\\n/g, '<br>');
  return s;
}
function _chatAddMsg(role, title, text) {
  var msgs = document.getElementById('chat-messages');
  var div  = document.createElement('div');
  div.className = 'chat-msg chat-msg-' + role;
  if (title) {
    var t = document.createElement('span');
    t.className = 'chat-msg-title';
    t.textContent = title;
    div.appendChild(t);
  }
  var body = document.createElement('span');
  if (role === 'bot') {
    body.innerHTML = _mdToHtml(text);
  } else {
    body.textContent = text;
  }
  div.appendChild(body);
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

async function sendChat() {
  var inp = document.getElementById('chat-input');
  var q   = inp.value.trim();
  if (!q) return;
  inp.value = '';
  inp.disabled = true;
  _chatAddMsg('user', '', q);
  document.getElementById('chat-chips').style.display = 'none';
  var msgs = document.getElementById('chat-messages');
  var typing = document.createElement('div');
  typing.className = 'chat-msg chat-msg-bot';
  typing.innerHTML = '<div class="chat-typing"><span></span><span></span><span></span></div>';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;
  try {
    var r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({q: q, session_id: (function(){
        var sid = localStorage.getItem('sharon_sid');
        if (!sid) { sid = 'web-' + Math.random().toString(36).slice(2,10); localStorage.setItem('sharon_sid', sid); }
        return sid;
      })()})
    });
    var d = await r.json();
    typing.remove();
    _chatAddMsg('bot', d.title || '', d.text || d.error || 'Помилка');
  } catch(e) {
    typing.remove();
    _chatAddMsg('bot', '', "Помилка з\'єднання. Спробуй ще раз.");
  } finally {
    inp.disabled = false;
    inp.focus();
  }
}

function sendChip(text) {
  document.getElementById('chat-input').value = text;
  sendChat();
}

tunLoadStatus();

// ── i18n ─────────────────────────────────────────────────────────────────────
const T = {
  uk: {
    title: `UAV WATCHER`, subtitle: `— система моніторингу БПЛА-загроз`,
    status_running: `● запущено`, status_stopped: `● зупинено`,
    card_city: `🏙 Місто моніторингу`, card_channels: `📡 Канали моніторингу`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Куди надсилати сповіщення`,
    card_service: `⚙ Сервіс`, card_bot: `🤖 Telegram Bot — сповіщувач`,
    lbl_city: `Назва міста`, lbl_region: `Область`,
    lbl_keywords: `Ключові слова (через кому)`, lbl_phone: `Номер телефону`,
    lbl_notify_id: `Notify Chat ID (твій Telegram User ID)`,
    btn_save: `Зберегти`, btn_check: `Перевірити`, btn_test: `▶ Тест`,
    btn_restart: `↺ Перезапустити сервіс`, btn_save_chatid: `Зберегти Chat ID`,
    btn_save_token: `Зберегти токен`,
    hint_keywords: `Слова для попередньої фільтрації — якщо жодне не знайдено в тексті, AI не викликається.`,
    hint_restart: `Після зміни конфігурації або каналів — перезапусти сервіс.`,
    sys_channel_label: `🔒 СИСТЕМНИЙ — ЗАВЖДИ АКТИВНИЙ`,
    user_channels_label: `📻 ВАШІ КАНАЛИ`,
    no_channels: `— немає власних каналів —`, active: `активних`,
    step_botfather_toggle: `Як створити бота через BotFather`,
    cur_state: `Поточний стан:`, ch_placeholder: `@username або -1001234567890`,
    err_connection: `Помилка з'єднання`,
    card_tunnel: `🔗 Публічний доступ`,
    hint_tunnel: `Поділись посиланням з родиною — вони отримають сповіщення через ваш сервіс.`,
    hint_tunnel_unavail: `cloudflared не встановлено або облікові дані відсутні.`,
    lbl_prefix: `Префікс URL`,
    btn_tunnel_start: `Запустити тунель`,
    btn_tunnel_stop: `Зупинити тунель`,
    btn_prefix_check: `Перевірити`,
    tunnel_active: `Тунель активний`,
  },
  en: {
    title: `UAV WATCHER`, subtitle: `— UAV threat monitoring system`,
    status_running: `● running`, status_stopped: `● stopped`,
    card_city: `🏙 Monitoring city`, card_channels: `📡 Monitoring channels`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Where to send notifications`,
    card_service: `⚙ Service`, card_bot: `🤖 Telegram Bot — notifier`,
    lbl_city: `City name`, lbl_region: `Region`,
    lbl_keywords: `Keywords (comma separated)`, lbl_phone: `Phone number`,
    lbl_notify_id: `Notify Chat ID (your Telegram User ID)`,
    btn_save: `Save`, btn_check: `Check`, btn_test: `▶ Test`,
    btn_restart: `↺ Restart service`, btn_save_chatid: `Save Chat ID`,
    btn_save_token: `Save token`,
    hint_keywords: `Pre-filter words — if none found in message, AI is not called.`,
    hint_restart: `After changing config or channels — restart the service.`,
    sys_channel_label: `🔒 SYSTEM — ALWAYS ACTIVE`,
    user_channels_label: `📻 YOUR CHANNELS`,
    no_channels: `— no custom channels —`, active: `active`,
    step_botfather_toggle: `How to create a bot via BotFather`,
    cur_state: `Current state:`, ch_placeholder: `@username or -1001234567890`,
    err_connection: `Connection error`,
    card_tunnel: `🔗 Public access`,
    hint_tunnel: `Share the link with your family — they'll get alerts through your service.`,
    hint_tunnel_unavail: `cloudflared is not installed or credentials are missing.`,
    lbl_prefix: `URL prefix`,
    btn_tunnel_start: `Start tunnel`,
    btn_tunnel_stop: `Stop tunnel`,
    btn_prefix_check: `Check`,
    tunnel_active: `Tunnel active`,
  },
  de: {
    title: `UAV WATCHER`, subtitle: `— UAV-Bedrohungsüberwachungssystem`,
    status_running: `● läuft`, status_stopped: `● gestoppt`,
    card_city: `🏙 Überwachungsstadt`, card_channels: `📡 Überwachungskanäle`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Wo Benachrichtigungen senden`,
    card_service: `⚙ Dienst`, card_bot: `🤖 Telegram Bot — Benachrichtiger`,
    lbl_city: `Stadtname`, lbl_region: `Region`,
    lbl_keywords: `Schlüsselwörter (kommagetrennt)`, lbl_phone: `Telefonnummer`,
    lbl_notify_id: `Benachrichtigungs-Chat-ID (Telegram User ID)`,
    btn_save: `Speichern`, btn_check: `Prüfen`, btn_test: `▶ Test`,
    btn_restart: `↺ Dienst neustarten`, btn_save_chatid: `Chat-ID speichern`,
    btn_save_token: `Token speichern`,
    hint_keywords: `Vorfilter-Wörter — wenn keines im Text gefunden, wird KI nicht aufgerufen.`,
    hint_restart: `Nach Konfig- oder Kanaländerungen — Dienst neustarten.`,
    sys_channel_label: `🔒 SYSTEM — IMMER AKTIV`,
    user_channels_label: `📻 DEINE KANÄLE`,
    no_channels: `— keine eigenen Kanäle —`, active: `aktiv`,
    step_botfather_toggle: `So erstellt man einen Bot via BotFather`,
    cur_state: `Aktueller Status:`, ch_placeholder: `@username oder -1001234567890`,
    err_connection: `Verbindungsfehler`,
    card_tunnel: `🔗 Öffentlicher Zugang`,
    hint_tunnel: `Teile den Link mit deiner Familie — sie erhalten Benachrichtigungen über deinen Dienst.`,
    hint_tunnel_unavail: `cloudflared nicht installiert oder Anmeldedaten fehlen.`,
    lbl_prefix: `URL-Präfix`,
    btn_tunnel_start: `Tunnel starten`,
    btn_tunnel_stop: `Tunnel stoppen`,
    btn_prefix_check: `Prüfen`,
    tunnel_active: `Tunnel aktiv`,
  },
  fr: {
    title: `UAV WATCHER`, subtitle: `— système de surveillance des menaces UAV`,
    status_running: `● en cours`, status_stopped: `● arrêté`,
    card_city: `🏙 Ville surveillée`, card_channels: `📡 Canaux de surveillance`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Où envoyer les notifications`,
    card_service: `⚙ Service`, card_bot: `🤖 Telegram Bot — notificateur`,
    lbl_city: `Nom de la ville`, lbl_region: `Région`,
    lbl_keywords: `Mots-clés (séparés par des virgules)`, lbl_phone: `Numéro de téléphone`,
    lbl_notify_id: `Chat ID de notification (votre User ID Telegram)`,
    btn_save: `Enregistrer`, btn_check: `Vérifier`, btn_test: `▶ Test`,
    btn_restart: `↺ Redémarrer le service`, btn_save_chatid: `Enregistrer Chat ID`,
    btn_save_token: `Enregistrer le token`,
    hint_keywords: `Mots de pré-filtre — si aucun trouvé dans le message, l'IA n'est pas appelée.`,
    hint_restart: `Après modification de la config ou des canaux — redémarrez le service.`,
    sys_channel_label: `🔒 SYSTÈME — TOUJOURS ACTIF`,
    user_channels_label: `📻 VOS CANAUX`,
    no_channels: `— aucun canal personnalisé —`, active: `actif`,
    step_botfather_toggle: `Comment créer un bot via BotFather`,
    cur_state: `État actuel :`, ch_placeholder: `@username ou -1001234567890`,
    err_connection: `Erreur de connexion`,
    card_tunnel: `🔗 Accès public`,
    hint_tunnel: `Partagez le lien avec votre famille — ils recevront des alertes via votre service.`,
    hint_tunnel_unavail: `cloudflared non installé ou identifiants manquants.`,
    lbl_prefix: `Préfixe URL`,
    btn_tunnel_start: `Démarrer le tunnel`,
    btn_tunnel_stop: `Arrêter le tunnel`,
    btn_prefix_check: `Vérifier`,
    tunnel_active: `Tunnel actif`,
  },
  pl: {
    title: `UAV WATCHER`, subtitle: `— system monitorowania zagrożeń UAV`,
    status_running: `● działa`, status_stopped: `● zatrzymany`,
    card_city: `🏙 Monitorowane miasto`, card_channels: `📡 Kanały monitorowania`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Gdzie wysyłać powiadomienia`,
    card_service: `⚙ Usługa`, card_bot: `🤖 Telegram Bot — powiadamiacz`,
    lbl_city: `Nazwa miasta`, lbl_region: `Region`,
    lbl_keywords: `Słowa kluczowe (oddzielone przecinkami)`, lbl_phone: `Numer telefonu`,
    lbl_notify_id: `Notify Chat ID (twój Telegram User ID)`,
    btn_save: `Zapisz`, btn_check: `Sprawdź`, btn_test: `▶ Test`,
    btn_restart: `↺ Uruchom ponownie usługę`, btn_save_chatid: `Zapisz Chat ID`,
    btn_save_token: `Zapisz token`,
    hint_keywords: `Słowa do wstępnego filtrowania — jeśli żadne nie zostanie znalezione, AI nie jest wywoływane.`,
    hint_restart: `Po zmianie konfiguracji lub kanałów — uruchom ponownie usługę.`,
    sys_channel_label: `🔒 SYSTEMOWY — ZAWSZE AKTYWNY`,
    user_channels_label: `📻 TWOJE KANAŁY`,
    no_channels: `— brak własnych kanałów —`, active: `aktywnych`,
    step_botfather_toggle: `Jak utworzyć bota przez BotFather`,
    cur_state: `Aktualny stan:`, ch_placeholder: `@username lub -1001234567890`,
    err_connection: `Błąd połączenia`,
    card_tunnel: `🔗 Dostęp publiczny`,
    hint_tunnel: `Udostępnij link rodzinie — otrzymają powiadomienia przez Twój serwis.`,
    hint_tunnel_unavail: `cloudflared nie jest zainstalowany lub brakuje danych.`,
    lbl_prefix: `Prefiks URL`,
    btn_tunnel_start: `Uruchom tunel`,
    btn_tunnel_stop: `Zatrzymaj tunel`,
    btn_prefix_check: `Sprawdź`,
    tunnel_active: `Tunel aktywny`,
  },
  es: {
    title: `UAV WATCHER`, subtitle: `— sistema de monitoreo de amenazas UAV`,
    status_running: `● ejecutando`, status_stopped: `● detenido`,
    card_city: `🏙 Ciudad de monitoreo`, card_channels: `📡 Canales de monitoreo`,
    card_tg_user: `🔑 Telegram User Bot (Telethon)`,
    card_notify: `📲 Dónde enviar notificaciones`,
    card_service: `⚙ Servicio`, card_bot: `🤖 Telegram Bot — notificador`,
    lbl_city: `Nombre de ciudad`, lbl_region: `Región`,
    lbl_keywords: `Palabras clave (separadas por comas)`, lbl_phone: `Número de teléfono`,
    lbl_notify_id: `Chat ID de notificación (tu User ID de Telegram)`,
    btn_save: `Guardar`, btn_check: `Verificar`, btn_test: `▶ Prueba`,
    btn_restart: `↺ Reiniciar servicio`, btn_save_chatid: `Guardar Chat ID`,
    btn_save_token: `Guardar token`,
    hint_keywords: `Palabras de prefiltro — si ninguna se encuentra en el mensaje, la IA no se llama.`,
    hint_restart: `Después de cambiar la configuración o canales — reinicia el servicio.`,
    sys_channel_label: `🔒 SISTEMA — SIEMPRE ACTIVO`,
    user_channels_label: `📻 TUS CANALES`,
    no_channels: `— sin canales personalizados —`, active: `activos`,
    step_botfather_toggle: `Cómo crear un bot a través de BotFather`,
    cur_state: `Estado actual:`, ch_placeholder: `@username o -1001234567890`,
    err_connection: `Error de conexión`,
    card_tunnel: `🔗 Acceso público`,
    hint_tunnel: `Comparte el enlace con tu familia — recibirán alertas a través de tu servicio.`,
    hint_tunnel_unavail: `cloudflared no está instalado o faltan credenciales.`,
    lbl_prefix: `Prefijo URL`,
    btn_tunnel_start: `Iniciar túnel`,
    btn_tunnel_stop: `Detener túnel`,
    btn_prefix_check: `Verificar`,
    tunnel_active: `Túnel activo`,
  },
  tr: {
    title: `UAV WATCHER`, subtitle: `— İHA tehdit izleme sistemi`,
    status_running: `● çalışıyor`, status_stopped: `● durduruldu`,
    card_city: `🏙 İzleme şehri`, card_channels: `📡 İzleme kanalları`,
    card_tg_user: `🔑 Telegram Kullanıcı Botu (Telethon)`,
    card_notify: `📲 Bildirimler nereye gönderilsin`,
    card_service: `⚙ Servis`, card_bot: `🤖 Telegram Bot — bildirimci`,
    lbl_city: `Şehir adı`, lbl_region: `Bölge`,
    lbl_keywords: `Anahtar kelimeler (virgülle ayrılmış)`, lbl_phone: `Telefon numarası`,
    lbl_notify_id: `Bildirim Chat ID'si (Telegram Kullanıcı ID'niz)`,
    btn_save: `Kaydet`, btn_check: `Kontrol et`, btn_test: `▶ Test`,
    btn_restart: `↺ Servisi yeniden başlat`, btn_save_chatid: `Chat ID'yi kaydet`,
    btn_save_token: `Token'ı kaydet`,
    hint_keywords: `Ön filtre kelimeleri — mesajda hiçbiri bulunamazsa, AI çağrılmaz.`,
    hint_restart: `Yapılandırma veya kanallar değiştirildiğinde — servisi yeniden başlatın.`,
    sys_channel_label: `🔒 SİSTEM — HER ZAMAN AKTİF`,
    user_channels_label: `📻 KANALLARINIZ`,
    no_channels: `— özel kanal yok —`, active: `aktif`,
    step_botfather_toggle: `BotFather aracılığıyla nasıl bot oluşturulur`,
    cur_state: `Mevcut durum:`, ch_placeholder: `@username veya -1001234567890`,
    err_connection: `Bağlantı hatası`,
    card_tunnel: `🔗 Genel erişim`,
    hint_tunnel: `Bağlantıyı ailenle paylaş — servisin üzerinden uyarı alacaklar.`,
    hint_tunnel_unavail: `cloudflared yüklü değil veya kimlik bilgileri eksik.`,
    lbl_prefix: `URL öneki`,
    btn_tunnel_start: `Tüneli başlat`,
    btn_tunnel_stop: `Tüneli durdur`,
    btn_prefix_check: `Kontrol et`,
    tunnel_active: `Tünel aktif`,
  },
  ar: {
    title: `UAV WATCHER`, subtitle: `— نظام مراقبة تهديدات الطائرات بدون طيار`,
    status_running: `● يعمل`, status_stopped: `● متوقف`,
    card_city: `🏙 مدينة المراقبة`, card_channels: `📡 قنوات المراقبة`,
    card_tg_user: `🔑 روبوت مستخدم تيليغرام (Telethon)`,
    card_notify: `📲 أين ترسل الإشعارات`,
    card_service: `⚙ الخدمة`, card_bot: `🤖 روبوت تيليغرام — المُشعِر`,
    lbl_city: `اسم المدينة`, lbl_region: `المنطقة`,
    lbl_keywords: `الكلمات المفتاحية (مفصولة بفواصل)`, lbl_phone: `رقم الهاتف`,
    lbl_notify_id: `معرّف المحادثة للإشعارات (User ID تيليغرام)`,
    btn_save: `حفظ`, btn_check: `تحقق`, btn_test: `▶ اختبار`,
    btn_restart: `↺ إعادة تشغيل الخدمة`, btn_save_chatid: `حفظ معرّف المحادثة`,
    btn_save_token: `حفظ الرمز`,
    hint_keywords: `كلمات للتصفية المسبقة — إذا لم تُعثر على أي منها في الرسالة، لا يُستدعى الذكاء الاصطناعي.`,
    hint_restart: `بعد تغيير الإعدادات أو القنوات — أعد تشغيل الخدمة.`,
    sys_channel_label: `🔒 قناة النظام — نشطة دائماً`,
    user_channels_label: `📻 قنواتك`,
    no_channels: `— لا توجد قنوات مخصصة —`, active: `نشطة`,
    step_botfather_toggle: `كيفية إنشاء روبوت عبر BotFather`,
    cur_state: `الحالة الحالية:`, ch_placeholder: `@username أو -1001234567890`,
    err_connection: `خطأ في الاتصال`,
    card_tunnel: `🔗 الوصول العام`,
    hint_tunnel: `شارك الرابط مع عائلتك — سيتلقون التنبيهات عبر خدمتك.`,
    hint_tunnel_unavail: `cloudflared غير مثبت أو بيانات الاعتماد مفقودة.`,
    lbl_prefix: `بادئة URL`,
    btn_tunnel_start: `تشغيل النفق`,
    btn_tunnel_stop: `إيقاف النفق`,
    btn_prefix_check: `تحقق`,
    tunnel_active: `النفق نشط`,
  },
  fa: {
    title: `UAV WATCHER`, subtitle: `— سیستم پایش تهدیدات پهپادی`,
    status_running: `● در حال اجرا`, status_stopped: `● متوقف`,
    card_city: `🏙 شهر پایش`, card_channels: `📡 کانال‌های پایش`,
    card_tg_user: `🔑 ربات کاربری تلگرام (Telethon)`,
    card_notify: `📲 کجا اعلان‌ها ارسال شوند`,
    card_service: `⚙ سرویس`, card_bot: `🤖 ربات تلگرام — اعلان‌دهنده`,
    lbl_city: `نام شهر`, lbl_region: `استان`,
    lbl_keywords: `کلیدواژه‌ها (با کاما جدا شده)`, lbl_phone: `شماره تلفن`,
    lbl_notify_id: `شناسه چت اعلان (User ID تلگرام شما)`,
    btn_save: `ذخیره`, btn_check: `بررسی`, btn_test: `▶ آزمون`,
    btn_restart: `↺ راه‌اندازی مجدد سرویس`, btn_save_chatid: `ذخیره شناسه چت`,
    btn_save_token: `ذخیره توکن`,
    hint_keywords: `کلمات برای فیلتر اولیه — اگر هیچ‌کدام در پیام یافت نشد، هوش مصنوعی فراخوانی نمی‌شود.`,
    hint_restart: `پس از تغییر تنظیمات یا کانال‌ها — سرویس را راه‌اندازی مجدد کنید.`,
    sys_channel_label: `🔒 کانال سیستم — همیشه فعال`,
    user_channels_label: `📻 کانال‌های شما`,
    no_channels: `— کانال سفارشی وجود ندارد —`, active: `فعال`,
    step_botfather_toggle: `چگونه یک ربات از طریق BotFather بسازیم`,
    cur_state: `وضعیت فعلی:`, ch_placeholder: `@username یا -1001234567890`,
    err_connection: `خطای اتصال`,
    card_tunnel: `🔗 دسترسی عمومی`,
    hint_tunnel: `پیوند را با خانواده‌ات به اشتراک بگذار — از طریق سرویس شما هشدار دریافت می‌کنند.`,
    hint_tunnel_unavail: `cloudflared نصب نشده یا اطلاعات ورود موجود نیست.`,
    lbl_prefix: `پیشوند URL`,
    btn_tunnel_start: `شروع تونل`,
    btn_tunnel_stop: `توقف تونل`,
    btn_prefix_check: `بررسی`,
    tunnel_active: `تونل فعال`,
  },
};

let currentLang = 'uk';

function applyLang(lang) {
  const t = T[lang] || T['uk'];
  currentLang = lang;
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === 'ar' || lang === 'fa') ? 'rtl' : 'ltr';

  document.querySelectorAll('[data-i18n]').forEach(function(el) {
    const k = el.dataset.i18n;
    if (t[k] !== undefined) el.textContent = t[k];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
    const k = el.dataset.i18nPlaceholder;
    if (t[k] !== undefined) el.placeholder = t[k];
  });
  // Status pill
  document.querySelectorAll('[data-i18n-state]').forEach(function(el) {
    el.textContent = el.dataset.state === 'ok' ? t.status_running : t.status_stopped;
  });
  // ch-total
  const tn = document.getElementById('ch-total-num');
  const tc = document.getElementById('ch-total');
  if (tn && tc) tc.innerHTML = `<span id="ch-total-num">${tn.textContent}</span> ${t.active}`;
  // active lang button
  document.querySelectorAll('.lang-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.lang === lang);
  });
  localStorage.setItem('uav-lang', lang);
}

function switchLang(lang) { applyLang(lang); }

// auto-detect on load
(function() {
  var saved = localStorage.getItem('uav-lang');
  var bl = (navigator.language || 'uk').slice(0, 2);
  var avail = Object.keys(T);
  applyLang(saved || (avail.indexOf(bl) >= 0 ? bl : 'uk'));
})();
function checkOllama() {
  var btn = document.getElementById('ollama-check-btn');
  var st = document.getElementById('ollama-status');
  st.className = 'ollama-st check'; st.textContent = '⏳ Перевіряємо Ollama...'; st.style.display = 'flex';
  btn.disabled = true;
  fetch('/api/check-ollama')
    .then(r => r.json())
    .then(d => {
      btn.disabled = false;
      if (d.running) {
        st.className = 'ollama-st ok';
        st.textContent = '✅ Ollama запущено! ' + (d.version || '');
        document.getElementById('ollama-models').style.display = 'block';
      } else {
        st.className = 'ollama-st fail';
        st.textContent = '❌ Ollama не знайдено. Встанови: curl -fsSL https://ollama.ai/install.sh | sh';
      }
    })
    .catch(() => {
      btn.disabled = false;
      st.className = 'ollama-st fail';
      st.textContent = '❌ Помилка перевірки. Ollama не запущено.';
    });
}

function selectOllamaModel(model, ram) {
  document.querySelector('input[name="llm_proxy_url"]').value = 'http://localhost:11434/v1';
  document.querySelector('input[name="llm_proxy_token"]').value = 'ollama';
  document.querySelector('input[name="llm_proxy_model"]').value = model;
  var st = document.getElementById('ollama-status');
  st.className = 'ollama-st ok'; st.style.display = 'flex';
  st.textContent = '✅ Модель ' + model + ' вибрана (' + ram + '). Збережи налаштування!';
  window.scrollTo({top: document.getElementById('sec-ai').offsetTop - 60, behavior: 'smooth'});
}

</script>

<div class="chat-backdrop" id="chat-backdrop" onclick="toggleChat()"></div>
<div id="chat-panel" class="chat-panel">
  <div class="chat-header">
    <span class="chat-header-icon" style="font-size:18px;line-height:1">🐱</span>
    <span class="chat-header-title">Шарон</span>
    <span class="chat-header-sub">Я тут, щоб ти вижив</span>
    <button class="chat-close" onclick="toggleChat()">✕</button>
  </div>
  <div class="chat-messages" id="chat-messages"></div>
  <div class="chat-chips" id="chat-chips">
    <button class="chat-chip" onclick="sendChip('БПЛА дрон')">🚁 БПЛА</button>
    <button class="chat-chip" onclick="sendChip('Балістична ракета')">🚀 Балістика</button>
    <button class="chat-chip" onclick="sendChip('Крилата ракета')">✈️ Крилата</button>
    <button class="chat-chip" onclick="sendChip('FAB авіабомба')">💣 FAB</button>
    <button class="chat-chip" onclick="sendChip('Хімічна загроза')">☣️ Хімічна</button>
    <button class="chat-chip" onclick="sendChip('Під завалами')">🆘 Завали</button>
    <button class="chat-chip" onclick="sendChip('Паніка заспокоїтись')">😰 Паніка</button>
    <button class="chat-chip" onclick="sendChip('Відбій тривоги')">✅ Відбій</button>
    <button class="chat-chip" onclick="sendChip('Де ховатись укриття')">🏠 Укриття</button>
    <button class="chat-chip" onclick="sendChip('Телефони екстрені')">📞 Телефони</button>
  </div>
  <div class="chat-input-row">
    <input class="chat-text-input" id="chat-input" type="text" placeholder="Запитай про загрозу..."
      onkeydown="if(event.key==='Enter')sendChat()">
    <button class="btn btn-primary chat-send-btn" onclick="sendChat()">▶</button>
  </div>
</div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default access logs

    def send_page(self, flash=None, flash_type="ok"):
        cfg = load_config()
        env = load_env()
        try:
            result = subprocess.run(["sudo", "rc-service", "uav-watcher", "status"],
                                     capture_output=True, text=True, timeout=5)
            running = "started" in result.stdout or "running" in result.stdout
        except Exception:
            running = False

        flash_html = ""
        if flash:
            flash_html = f'<div class="flash {flash_type}">{flash}</div>'

        keywords_str = ", ".join(cfg.get("city_keywords", []))
        user_chs = get_user_channels(cfg)

        def _ch_row(ch):
            handle = f"@{ch['username']} · " if ch.get("username") else ""
            return (
                f'<div class="ch-row">'
                f'<span class="ch-pulse ch-pulse-green"></span>'
                f'<div class="ch-info">'
                f'<span class="ch-name">{ch["title"]}</span>'
                f'<span class="ch-handle">{handle}{ch["id"]}</span>'
                f'</div>'
                f'<button class="ch-remove" onclick="removeChannel({ch["id"]})" title="Видалити">×</button>'
                f'</div>'
            )

        user_channels_html = "".join(_ch_row(ch) for ch in user_chs) if user_chs else \
            '<div style="padding:6px 0;font-family:var(--mono);font-size:10px;color:var(--dim)">— немає власних каналів —</div>'

        import re as _re
        vars_ = {
            "status_class": "ok" if running else "err",
            "status_text": "● запущено" if running else "● зупинено",
            "flash_html": flash_html,
            "city": cfg.get("city", ""),
            "city_region": cfg.get("city_region", ""),
            "city_keywords": keywords_str,
            "city_lat": str(cfg.get("city_lat", "")),
            "city_lon": str(cfg.get("city_lon", "")),
            "city_radius_km": str(cfg.get("city_radius_km", 30)),
            "preset_options": "\n".join(
                f'<option value="{p["name"]}">{p["name"]} ({p["region"]})</option>'
                for p in (json.load(open(os.path.join(os.path.dirname(__file__), "data", "city_presets.json")))
                          if os.path.exists(os.path.join(os.path.dirname(__file__), "data", "city_presets.json")) else [])
            ),
            "city_preset_js": json.dumps(
                {p["name"]: p for p in (json.load(open(os.path.join(os.path.dirname(__file__), "data", "city_presets.json")))
                                        if os.path.exists(os.path.join(os.path.dirname(__file__), "data", "city_presets.json")) else [])},
                ensure_ascii=False
            ),
            "phone": env.get("TELEGRAM_PHONE", ""),
            "api_id": env.get("TELEGRAM_API_ID", ""),
            "api_hash": env.get("TELEGRAM_API_HASH", ""),
            "notify_chat_id": str(cfg.get("notify_chat_id", "")),
            "bot_token": cfg.get("bot_token", ""),
            "channel_count": str(len(cfg.get("channels", []))),
            "model": cfg.get("llm_proxy_model") or cfg.get("goclaw_model", ""),
            "llm_proxy_url": (cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "").replace("/chat/completions", "")).rstrip("/"),
            "llm_proxy_token": cfg.get("llm_proxy_token") or cfg.get("goclaw_api_key", ""),
            "llm_proxy_model": cfg.get("llm_proxy_model") or cfg.get("goclaw_model", ""),
            "user_channels_html": user_channels_html,
            "user_channel_count": str(len(user_chs)),
            "channel_total": str(len(user_chs) + len(LOCKED_CHANNELS)),
        }
        html = _re.sub(r'\{([a-z_]+)\}', lambda m: vars_.get(m.group(1), m.group(0)), HTML)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html.encode())

    def redirect(self, path="/", flash=None, flash_type="ok"):
        from urllib.parse import quote
        params = ""
        if flash:
            params = f"?flash={quote(flash)}&ft={flash_type}"
        self.send_response(303)
        self.send_header("Location", path + params)
        self.end_headers()

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode()

    def send_share_page(self):
        cfg = load_config()
        city = cfg.get("city", "Місто")
        ch_count = len(cfg.get("channels", [])) + len(LOCKED_CHANNELS)
        html = SHARE_HTML.replace("{{CITY}}", city).replace("{{CHANNEL_COUNT}}", str(ch_count))
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # Public routes — no auth required
        if path == "/share":
            self.send_share_page()
            return
        if path == "/api/bot-info":
            uname, url = get_bot_info()
            self.send_json({"username": uname, "url": url})
            return
        if path == "/api/tunnel":
            running, pid = tunnel_running()
            cfg = load_config()
            self.send_json({
                "available": cloudflared_ok(),
                "running": running,
                "pid": pid,
                "url": cfg.get("tunnel_url", ""),
                "prefix": cfg.get("tunnel_prefix", ""),
            })
            return
        if path == "/api/channels":
            cfg = load_config()
            user_chs = get_user_channels(cfg)
            self.send_json({"user_channels": user_chs, "locked_count": len(LOCKED_CHANNELS)})
            return
        if path == "/api/check-ollama":
            try:
                import urllib.request as _ur
                with _ur.urlopen("http://localhost:11434/api/version", timeout=2) as r:
                    v = json.loads(r.read())
                self.send_json({"running": True, "version": v.get("version","")})
            except Exception:
                self.send_json({"running": False})
            return
        # All remaining GET routes require admin auth
        if not self._require_admin_auth():
            return
        params = parse_qs(parsed.query)
        flash = params.get("flash", [None])[0]
        ft = params.get("ft", ["ok"])[0]
        self.send_page(flash, ft)

    def send_json(self, data: dict, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_admin_auth(self) -> bool:
        """Check Basic Auth for admin routes. Returns True if OK, sends 401 if not."""
        import base64
        cfg = load_config()
        password = cfg.get("admin_password", "")
        if not password:
            return True  # No password set — open access
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8", errors="replace")
                _, pwd = decoded.split(":", 1)
                if pwd == password:
                    return True
            except Exception:
                pass
        body = b"<h1>401 Unauthorized</h1><p>Enter admin password.</p>"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Sharon Admin"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_POST(self):
        body = self.read_body()
        data = parse_qs(body)
        get = lambda k: data.get(k, [""])[0].strip()

        path = urlparse(self.path).path
        # Form POSTs are always admin
        if "application/json" not in self.headers.get("Content-Type", ""):
            if not self._require_admin_auth():
                return

        # JSON API endpoints (Content-Type: application/json)
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            _PUBLIC_JSON = {"/api/shelter", "/api/shelter-chat", "/api/chat",
                            "/api/sos", "/api/sos-relay", "/api/check-ollama"}
            if path not in _PUBLIC_JSON and not self._require_admin_auth():
                return
            try:
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {}
            cfg = load_config()

            if path == "/resolve-channel":
                handle = payload.get("handle", "").strip()
                token = cfg.get("bot_token", "")
                if not token:
                    self.send_json({"ok": False, "error": "Спочатку збережіть Bot Token"})
                    return
                if not handle:
                    self.send_json({"ok": False, "error": "Введіть username або ID"})
                    return
                try:
                    result = resolve_via_bot_api(handle, token)
                    if result["id"] in LOCKED_CHANNELS:
                        self.send_json({"ok": False, "error": "Цей канал вже є в системному списку"})
                    else:
                        self.send_json(result)
                except Exception as e:
                    self.send_json({"ok": False, "error": f"Не знайдено: {str(e)[:80]}"})
                return

            if path == "/add-channel":
                ch_id = int(payload.get("id", 0))
                title = str(payload.get("title", str(ch_id)))
                username = str(payload.get("username", ""))
                if ch_id in LOCKED_CHANNELS:
                    self.send_json({"ok": False, "error": "Системний канал"})
                    return
                channels = cfg.get("channels", [])
                if ch_id not in channels:
                    channels.append(ch_id)
                    cfg["channels"] = channels
                meta = cfg.setdefault("channels_meta", {})
                meta[str(ch_id)] = {"title": title, "username": username}
                save_config(cfg)
                self.send_json({"ok": True})
                return

            if path == "/api/sos":
                lat = payload.get("lat")
                lon = payload.get("lon")
                cfg = load_config()
                tg_ok = send_sos_telegram(cfg, lat, lon)
                send_sos_to_peers(cfg, lat, lon)
                self.send_json({"ok": True, "tg_sent": tg_ok})
                return

            if path == "/api/sos-relay":
                # Incoming SOS from a peer Sharon instance
                lat      = payload.get("lat")
                lon      = payload.get("lon")
                src_city = payload.get("city", "невідома")
                src_url  = payload.get("tunnel_url", "")
                cfg      = load_config()
                token    = cfg.get("bot_token", "")
                chat_id  = cfg.get("notify_chat_id")
                if token and chat_id:
                    coords = f"{lat:.5f}, {lon:.5f}" if lat else "невідомо"
                    maps_url = f"https://maps.google.com/?q={lat},{lon}" if lat else ""
                    text = (
                        "\U0001F198 *SOS-ретрансляція \u2014 \u041b\u044e\u0434\u0438\u043d\u0430 \u043f\u0456\u0434 \u0437\u0430\u0432\u0430\u043b\u043e\u043c!*\n\n"
                        f"\U0001F4CD `{coords}`\n"
                    )
                    if maps_url:
                        text += f"\U0001F5FA [\u041a\u0430\u0440\u0442\u0430]({maps_url})\n"
                    text += f"\U0001F4E1 \u0414\u0436\u0435\u0440\u0435\u043b\u043e: {src_city}"
                    if src_url:
                        text += f" ([\u043f\u043e\u0441\u0438\u043b\u0430\u043d\u043d\u044f]({src_url}/share))"
                    text += "\n\n\u26A0\uFE0F \u0417\u0430\u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0443\u0439\u0442\u0435: *101*"
                    body = json.dumps({
                        "chat_id": chat_id, "text": text,
                        "parse_mode": "Markdown", "disable_web_page_preview": True,
                    }, ensure_ascii=False).encode()
                    try:
                        req = urllib.request.Request(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            data=body, headers={"Content-Type": "application/json"},
                        )
                        urllib.request.urlopen(req, timeout=10)
                    except Exception:
                        pass
                self.send_json({"ok": True})
                return

            if path == "/api/check-ollama":
                try:
                    import urllib.request as _ur
                    with _ur.urlopen("http://localhost:11434/api/version", timeout=2) as r:
                        v = json.loads(r.read())
                    self.send_json({"running": True, "version": v.get("version","")})
                except Exception:
                    self.send_json({"running": False})
                return

            if path == "/api/shelter":
                lat = payload.get("lat")
                lon = payload.get("lon")
                if lat is None or lon is None:
                    self.send_json({"ok": False, "error": "lat/lon required"}, 400)
                    return
                try:
                    shelters = query_shelters(float(lat), float(lon))
                    self.send_json({"ok": True, "shelters": shelters})
                except Exception as exc:
                    self.send_json({"ok": False, "error": str(exc)})
                return

            if path == "/api/shelter-chat":
                user_msg = payload.get("message", "").strip()
                context  = payload.get("context", "").strip()
                if not user_msg:
                    self.send_json({"ok": False, "error": "message required"}, 400)
                    return
                session_id = payload.get("session_id", "web")
                reply = _call_consultant(user_msg, session_id)
                if not reply:
                    reply = shelter_ai_query(user_msg, context)
                self.send_json({"ok": True, "reply": reply})
                return

            if path == "/api/chat":
                q = payload.get("q", "").strip()
                if not q:
                    self.send_json({"ok": False, "error": "q required"}, 400)
                    return
                session_id = payload.get("session_id", "web-chat")
                consultant_reply = _call_consultant(q, session_id)
                if consultant_reply:
                    self.send_json({"ok": True, "reply": consultant_reply, "text": consultant_reply})
                else:
                    self.send_json(chat_match(q))
                return


            if path == "/tunnel-check":
                import re as _re2
                prefix = payload.get("prefix", "").strip().lower()
                if not _re2.match(r'^[a-z0-9\-]{2,20}$', prefix):
                    self.send_json({"ok": False, "error": "Невірний формат: тільки a-z, 0-9, дефіс, 2-20 символів"})
                    return
                conflict = not tunnel_prefix_available(prefix)
                self.send_json({"ok": True, "conflict": conflict,
                                "hostname": f"{prefix}{CF_SUFFIX}.{CF_DOMAIN}"})
                return

            if path == "/tunnel-start":
                import re as _re3
                prefix = payload.get("prefix", "").strip().lower()
                if not _re3.match(r'^[a-z0-9\-]{2,20}$', prefix):
                    self.send_json({"ok": False, "error": "Невірний формат префіксу"})
                    return
                if not cloudflared_ok():
                    self.send_json({"ok": False, "error": "cloudflared не налаштовано"})
                    return
                ok_dns, dns_msg = tunnel_route_dns(prefix)
                if not ok_dns:
                    self.send_json({"ok": False, "error": f"DNS помилка: {dns_msg[:100]}"})
                    return
                pid, url = tunnel_start(prefix)
                self.send_json({"ok": True, "url": url, "pid": pid})
                return

            if path == "/tunnel-stop":
                tunnel_stop()
                self.send_json({"ok": True})
                return

            if path == "/remove-channel":
                ch_id = int(payload.get("id", 0))
                if ch_id in LOCKED_CHANNELS:
                    self.send_json({"ok": False, "error": "Системний канал не можна видалити"})
                    return
                channels = cfg.get("channels", [])
                cfg["channels"] = [c for c in channels if c != ch_id]
                meta = cfg.get("channels_meta", {})
                meta.pop(str(ch_id), None)
                save_config(cfg)
                self.send_json({"ok": True})
                return

        if path == "/send-test":
            import urllib.request
            cfg = load_config()
            token = cfg.get("bot_token", "")
            chat_id = cfg.get("notify_chat_id", "")
            if not token or not chat_id:
                self.send_json({"ok": False, "message": "Збережіть Bot Token та Chat ID перед тестуванням"})
                return
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = json.dumps({
                    "chat_id": chat_id,
                    "text": "✅ Sharon — тестове повідомлення. Бот налаштовано правильно!",
                    "parse_mode": "Markdown"
                }).encode()
                req = urllib.request.Request(url, data=payload,
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    result = json.loads(resp.read())
                if result.get("ok"):
                    self.send_json({"ok": True, "message": "✓ Тестове повідомлення надіслано! Перевір Telegram."})
                else:
                    self.send_json({"ok": False, "message": f"Telegram: {result.get('description', 'помилка')}"})
            except Exception as e:
                self.send_json({"ok": False, "message": f"Помилка: {str(e)[:120]}"})
            return

        try:
            cfg = load_config()

            if path == "/save-city":
                preset_name = get("preset")
                if preset_name:
                    try:
                        _pp = os.path.join(os.path.dirname(__file__), "data", "city_presets.json")
                        _presets = json.load(open(_pp))
                        _p = next((x for x in _presets if x["name"] == preset_name), None)
                        if _p:
                            cfg["city"] = _p["name"]
                            cfg["city_region"] = _p["region"]
                            cfg["city_keywords"] = _p["keywords"]
                            cfg["city_lat"] = _p["lat"]
                            cfg["city_lon"] = _p["lon"]
                            cfg["city_radius_km"] = _p["radius_km"]
                    except Exception as _e:
                        log.warning(f"preset load error: {_e}")
                else:
                    cfg["city"] = get("city")
                    cfg["city_region"] = get("city_region")
                    kw_raw = get("city_keywords")
                    cfg["city_keywords"] = [k.strip() for k in kw_raw.split(",") if k.strip()]
                    try:
                        _lat = get("city_lat").strip()
                        _lon = get("city_lon").strip()
                        if _lat and _lon:
                            cfg["city_lat"] = float(_lat)
                            cfg["city_lon"] = float(_lon)
                        else:
                            _glat, _glon = geocode_city(cfg["city"])
                            if _glat is not None:
                                cfg["city_lat"] = _glat
                                cfg["city_lon"] = _glon
                    except Exception:
                        pass
                    try:
                        _r = get("city_radius_km").strip()
                        if _r:
                            cfg["city_radius_km"] = int(_r)
                    except Exception:
                        pass
                save_config(cfg)
                self.redirect(flash="✓ Місто збережено")

            elif path == "/save-channels":
                lines = get("channels").splitlines()
                ids = []
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            ids.append(int(line))
                        except ValueError:
                            pass
                cfg["channels"] = ids
                save_config(cfg)
                self.redirect(flash=f"✓ Збережено {len(ids)} канал(ів)")

            elif path == "/save-env":
                save_env(get("api_id"), get("api_hash"), get("phone"))
                self.redirect(flash="✓ Credentials збережено. Запустіть auth.py для авторизації.")

            elif path == "/save-notify":
                try:
                    cfg["notify_chat_id"] = int(get("notify_chat_id"))
                    save_config(cfg)
                    self.redirect(flash="✓ Chat ID збережено")
                except ValueError:
                    self.redirect(flash="✗ Невірний Chat ID", flash_type="err")

            elif path == "/save-bot":
                cfg["bot_token"] = get("bot_token")
                save_config(cfg)
                self.redirect(flash="✓ Bot token збережено")

            elif path == "/save-llm":
                base_url = get("llm_proxy_url").strip().rstrip("/")
                cfg["llm_proxy_url"]   = base_url
                cfg["llm_proxy_token"] = get("llm_proxy_token").strip()
                cfg["llm_proxy_model"] = get("llm_proxy_model").strip() or "gpt-4o-mini"
                # Keep goclaw_* in sync for backward compat with classifier
                cfg["goclaw_url"]      = base_url + "/chat/completions" if base_url else ""
                cfg["goclaw_api_key"]  = cfg["llm_proxy_token"]
                cfg["goclaw_model"]    = cfg["llm_proxy_model"]
                save_config(cfg)
                self.redirect(flash="✓ AI Proxy налаштування збережено")

            elif path == "/save-password":
                new_pw   = get("admin_password").strip()
                confirm  = get("admin_password_confirm").strip()
                if new_pw != confirm:
                    self.redirect(flash="✗ Паролі не співпадають", flash_type="err")
                    return
                cfg["admin_password"] = new_pw
                save_config(cfg)
                msg = "✓ Пароль встановлено" if new_pw else "✓ Захист паролем вимкнено"
                self.redirect(flash=msg)

            elif path == "/restart":
                ok, msg = restart_service()
                if ok:
                    self.redirect(flash="✓ Сервіс перезапущено")
                else:
                    self.redirect(flash=f"✗ Помилка: {msg[:80]}", flash_type="err")

            else:
                self.redirect()

        except Exception as e:
            self.redirect(flash=f"✗ Помилка: {e}", flash_type="err")


if __name__ == "__main__":
    print(f"Sharon Config UI → http://localhost:{PORT}")
    class ReusableServer(ThreadingHTTPServer):
        allow_reuse_address = True
    server = ReusableServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
