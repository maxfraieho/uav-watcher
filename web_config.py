#!/usr/bin/env python3
"""
UAV Watcher — web config UI.
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
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

_shelter_cache: dict = {}   # {city_key: {"ts": float, "shelters": list}}

LOCKED_CHANNELS = {
    -1001223955273: {"title": "Повітряні Сили ЗС України", "username": "kpszsu", "id": -1001223955273}
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
PORT = 8422


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


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
CF_TUNNEL_ID    = "c0413dca-1f1d-4176-be39-23e2c8f0754f"
CF_DOMAIN       = "exodus.pp.ua"
CF_SUFFIX       = "-alert"
CF_TUNNEL_CFG   = "/tmp/uav-watcher-tunnel.yml"


def cloudflared_ok():
    import shutil
    if not shutil.which("cloudflared"):
        return False
    if not os.path.isdir(CLOUDFLARED_DIR):
        return False
    creds = os.path.join(CLOUDFLARED_DIR, f"{CF_TUNNEL_ID}.json")
    cert  = os.path.join(CLOUDFLARED_DIR, "cert.pem")
    return os.path.isfile(creds) and os.path.isfile(cert)


def tunnel_running():
    cfg = load_config()
    pid = cfg.get("tunnel_pid")
    if not pid:
        return False, None
    try:
        os.kill(int(pid), 0)
        return True, int(pid)
    except (ProcessLookupError, PermissionError, ValueError):
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
         "route", "dns", CF_TUNNEL_ID, hostname],
        capture_output=True, text=True, timeout=30
    )
    ok  = result.returncode == 0 or "Added CNAME" in (result.stdout + result.stderr)
    msg = (result.stdout + result.stderr).strip()
    return ok, msg


def tunnel_write_config(prefix):
    creds = os.path.join(CLOUDFLARED_DIR, f"{CF_TUNNEL_ID}.json")
    cert  = os.path.join(CLOUDFLARED_DIR, "cert.pem")
    hostname = f"{prefix}{CF_SUFFIX}.{CF_DOMAIN}"
    cfg_text = (
        f"tunnel: {CF_TUNNEL_ID}\n"
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
        f"  node[\"shelter_type\"~\".\"](around:{radius},{lat},{lon});"
        f"  node[\"civil_protection\"=\"shelter\"](around:{radius},{lat},{lon});"
        f"  node[\"emergency\"=\"shelter\"](around:{radius},{lat},{lon});"
        f"  node[\"building\"=\"basement\"][\"access\"=\"yes\"](around:{radius},{lat},{lon});"
        f");"
        f"out body;"
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
            or "Укриття"
        )
        addr = (tags.get("addr:street", "") + " " + tags.get("addr:housenumber", "")).strip()
        shelters.append({
            "dist":    dist,
            "name":    name,
            "addr":    addr or tags.get("description", ""),
            "type":    tags.get("shelter_type", tags.get("civil_protection", "public")),
            "lat":     slat,
            "lon":     slon,
            "osm_id":  el.get("id"),
        })
    shelters.sort(key=lambda x: x["dist"])
    shelters = shelters[:8]
    _shelter_cache[cache_key] = {"ts": time.time(), "shelters": shelters}
    return shelters


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
    """Ask goclaw about shelters and safety. Returns AI reply text."""
    cfg     = load_config()
    url     = cfg.get("goclaw_url", "")
    api_key = cfg.get("goclaw_api_key", "")
    model   = cfg.get("goclaw_model", "gpt-4o-mini")
    if not url:
        return "AI-консультант не налаштовано."
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

def cf_random_prefix(n=5):
    return "".join(_random.choices(_string.ascii_lowercase, k=n))


SHARE_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UAV Watcher — Укриття & Тривоги</title>
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
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">&#9889;</span>
  <div>
    <div class="site-title">UAV Watcher</div>
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
    btn.textContent = 'Помилка з\'єднання';
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
    addMsg('ai', 'Помилка зв\'язку з сервером');
  }
}

document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
</script>
</body>
</html>"""

HTML = """<!DOCTYPE html>
<html lang="uk" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UAV Watcher — Налаштування</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0b0e; --surface: #111318; --elevated: #191c23;
    --border: rgba(255,255,255,0.09); --border2: rgba(255,255,255,0.14);
    --text: rgba(255,255,255,0.92); --muted: rgba(255,255,255,0.38);
    --dim: rgba(255,255,255,0.22);
    --amber: #f59e0b; --red: #ef4444; --green: #22c55e;
    --font: 'IBM Plex Sans', sans-serif; --mono: 'JetBrains Mono', monospace;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; min-height: 100vh; padding: 0; }
  .topbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; height: 44px; display: flex; align-items: center; gap: 10px; }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--amber); }
  .topbar-title { font-family: var(--mono); font-size: 12px; font-weight: 600; letter-spacing: 0.1em; }
  .topbar-sub { font-family: var(--mono); font-size: 10px; color: var(--muted); margin-left: 4px; }
  .status-pill { margin-left: auto; padding: 3px 10px; border-radius: 20px; font-family: var(--mono); font-size: 10px; font-weight: 600; }
  .status-pill.ok { background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3); color: var(--green); }
  .status-pill.err { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3); color: var(--red); }

  .layout { display: flex; gap: 0; max-width: 1100px; margin: 0 auto; padding: 32px 24px; gap: 24px; align-items: flex-start; }
  .col-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
  .col-side { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; gap: 20px; }

  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
  .card-header { padding: 12px 16px 10px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
  .card-title { font-family: var(--mono); font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
  .card-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

  label { display: block; font-family: var(--mono); font-size: 10px; font-weight: 500; color: var(--dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 5px; }
  input[type=text], input[type=tel], input[type=password], textarea {
    width: 100%; padding: 7px 10px; background: var(--elevated);
    border: 1px solid var(--border); border-radius: 3px;
    color: var(--text); font-family: var(--mono); font-size: 12px;
    outline: none; transition: border-color 0.15s;
  }
  input:focus, textarea:focus { border-color: var(--border2); }
  input::placeholder, textarea::placeholder { color: rgba(255,255,255,0.18); }
  textarea { resize: vertical; min-height: 70px; line-height: 1.5; }

  .btn { height: 34px; padding: 0 16px; border-radius: 3px; border: none; font-family: var(--mono); font-size: 11px; font-weight: 600; cursor: pointer; transition: opacity 0.12s; }
  .btn-primary { background: var(--amber); color: #000; }
  .btn-primary:hover { opacity: 0.88; }
  .btn-ghost { background: transparent; border: 1px solid var(--border2); color: var(--muted); }
  .btn-ghost:hover { color: var(--text); border-color: rgba(255,255,255,0.25); }
  .btn-danger { background: transparent; border: 1px solid rgba(239,68,68,0.35); color: var(--red); }
  .btn-row { display: flex; gap: 8px; align-items: center; }

  .hint { font-family: var(--mono); font-size: 10px; color: var(--muted); line-height: 1.6; }
  .hint a { color: var(--amber); text-decoration: none; }
  .hint a:hover { text-decoration: underline; }
  .hint code { background: var(--elevated); padding: 1px 5px; border-radius: 2px; font-size: 10px; }

  .step-list { display: flex; flex-direction: column; gap: 8px; }
  .step { display: flex; gap: 10px; align-items: flex-start; }
  .step-num { width: 20px; height: 20px; border-radius: 50%; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 9px; font-weight: 600; color: var(--amber); flex-shrink: 0; margin-top: 1px; }
  .step-text { font-family: var(--mono); font-size: 11px; color: rgba(255,255,255,0.65); line-height: 1.55; }
  .step-text code { background: var(--elevated); padding: 1px 5px; border-radius: 2px; color: rgba(180,220,160,0.85); }

  .flash { padding: 10px 14px; border-radius: 3px; font-family: var(--mono); font-size: 11px; margin-bottom: 4px; }
  .flash.ok { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.25); color: var(--green); }
  .flash.err { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25); color: var(--red); }

  .separator { height: 1px; background: var(--border); }
  .tag { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 2px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); font-family: var(--mono); font-size: 10px; color: var(--dim); }
  .channel-id { font-family: var(--mono); font-size: 11px; color: rgba(180,220,160,0.75); }

  /* ── Channel list ── */
  .ch-total { font-family: var(--mono); font-size: 10px; color: var(--amber); font-weight: 600; }
  .ch-section { padding: 10px 16px; }
  .ch-section-label { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: 0.14em; color: var(--dim); text-transform: uppercase; margin-bottom: 8px; }
  .ch-divider { height: 1px; background: var(--border); }
  .ch-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .ch-row:last-child { border-bottom: none; }
  .ch-locked { opacity: 0.85; }
  .ch-pulse { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; position: relative; }
  .ch-pulse::after { content:''; position:absolute; inset:-3px; border-radius:50%; animation: pulse 2.4s ease-in-out infinite; }
  .ch-pulse-amber { background: var(--amber); }
  .ch-pulse-amber::after { background: rgba(245,158,11,0.25); }
  .ch-pulse-green { background: var(--green); }
  .ch-pulse-green::after { background: rgba(34,197,94,0.2); }
  @keyframes pulse { 0%,100%{transform:scale(1);opacity:0.5} 50%{transform:scale(2.2);opacity:0} }
  .ch-info { flex: 1; min-width: 0; }
  .ch-name { display: block; font-family: var(--mono); font-size: 11px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ch-handle { display: block; font-family: var(--mono); font-size: 9px; color: var(--dim); margin-top: 1px; }
  .ch-badge-sys { padding: 2px 7px; border-radius: 2px; background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3); font-family: var(--mono); font-size: 9px; font-weight: 700; color: var(--amber); letter-spacing: 0.1em; flex-shrink: 0; }
  .ch-remove { background: none; border: none; color: var(--dim); cursor: pointer; font-size: 14px; line-height: 1; padding: 0 2px; transition: color 0.15s; flex-shrink: 0; }
  .ch-remove:hover { color: var(--red); }
  .ch-add-wrap { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
  .ch-add-row { display: flex; gap: 8px; }
  .ch-input { flex: 1; min-width: 0; padding: 7px 10px; background: var(--elevated); border: 1px solid var(--border); border-radius: 3px; color: var(--text); font-family: var(--mono); font-size: 11px; outline: none; transition: border-color 0.15s; }
  .ch-input:focus { border-color: var(--border2); }
  .ch-input::placeholder { color: rgba(255,255,255,0.18); }
  .ch-btn { height: 34px; font-size: 10px; }
  .ch-preview { background: var(--elevated); border: 1px solid var(--border2); border-radius: 3px; padding: 8px 12px; display: flex; align-items: center; gap: 10px; }
  .ch-preview-name { font-family: var(--mono); font-size: 11px; color: var(--text); flex: 1; }
  .ch-preview-id { font-family: var(--mono); font-size: 9px; color: var(--dim); }

  details { border: none; }
  details[open] summary { color: var(--amber); }
  summary.steps-toggle { cursor: pointer; font-family: var(--mono); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); list-style: none; display: flex; align-items: center; gap: 6px; padding: 4px 0; transition: color 0.15s; user-select: none; }
  summary.steps-toggle::before { content: '▶'; font-size: 8px; transition: transform 0.2s; display: inline-block; }
  details[open] summary.steps-toggle::before { transform: rotate(90deg); }
  summary.steps-toggle:hover { color: rgba(255,255,255,0.7); }
  .test-ok  { background: rgba(34,197,94,0.1);  border: 1px solid rgba(34,197,94,0.25);  color: var(--green); padding: 7px 10px; border-radius: 3px; font-family: var(--mono); font-size: 10px; }
  .test-err { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.25);  color: var(--red);   padding: 7px 10px; border-radius: 3px; font-family: var(--mono); font-size: 10px; }

  @media (max-width: 750px) { .layout { flex-direction: column; } .col-side { width: 100%; } }

  /* ── Language selector ── */
  .lang-sel { display: flex; gap: 2px; margin-left: 10px; }
  .lang-btn { background: none; border: none; cursor: pointer; font-size: 15px; padding: 1px 3px; border-radius: 3px; opacity: 0.45; transition: opacity 0.15s, transform 0.1s; line-height: 1; }
  .lang-btn:hover { opacity: 0.9; transform: scale(1.12); }
  .lang-btn.active { opacity: 1; }

  /* ── RTL support ── */
  [dir="rtl"] .layout { flex-direction: row-reverse; flex-wrap: wrap; }
  [dir="rtl"] .topbar { flex-direction: row-reverse; }
  [dir="rtl"] .topbar-sub { margin-left: 0; margin-right: 4px; }
  [dir="rtl"] .lang-sel { margin-left: 0; margin-right: 10px; }
  [dir="rtl"] .card-header { flex-direction: row-reverse; }
  [dir="rtl"] .card-body { direction: rtl; }
  [dir="rtl"] .btn-row { flex-direction: row-reverse; }
  [dir="rtl"] .step { flex-direction: row-reverse; }
  [dir="rtl"] .ch-row { flex-direction: row-reverse; }
  [dir="rtl"] .ch-add-row { flex-direction: row-reverse; }
  [dir="rtl"] .ch-section { text-align: right; }
  [dir="rtl"] label { text-align: right; }
  [dir="rtl"] input, [dir="rtl"] textarea { text-align: right; direction: rtl; }
  [dir="rtl"] .hint { text-align: right; }
  [dir="rtl"] .step-text { text-align: right; }
  @media (max-width: 750px) { [dir="rtl"] .layout { flex-direction: column; } }
</style>
</head>
<body>
<div class="topbar">
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

    <!-- CITY CONFIG -->
    <div class="card">
      <div class="card-header"><span class="card-title" data-i18n="card_city">🏙 Місто моніторингу</span></div>
      <form method="POST" action="/save-city">
      <div class="card-body">
        <div>
          <label data-i18n="lbl_city">Назва міста</label>
          <input type="text" name="city" value="{city}" placeholder="Олександрія">
        </div>
        <div>
          <label data-i18n="lbl_region">Область</label>
          <input type="text" name="city_region" value="{city_region}" placeholder="Кіровоградська область">
        </div>
        <div>
          <label data-i18n="lbl_keywords">Ключові слова (через кому)</label>
          <input type="text" name="city_keywords" value="{city_keywords}" placeholder="Олександрія, Олександрійськ">
          <div class="hint" style="margin-top:5px" data-i18n="hint_keywords">Слова для попередньої фільтрації — якщо жодне не знайдено в тексті, AI не викликається.</div>
        </div>
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
            <span class="ch-pulse ch-pulse-amber"></span>
            <div class="ch-info">
              <span class="ch-name">Повітряні Сили ЗС України</span>
              <span class="ch-handle">@kpszsu · -1001223955273</span>
            </div>
            <span class="ch-badge-sys">SYSTEM</span>
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
                <div class="step-text">Введи назву бота (будь-яку, наприклад <code>Мій UAV Watcher</code>)</div>
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
          <div class="hint" style="margin-bottom:8px">URL: <code id="tun-preview" style="color:var(--amber)">?????-alert.exodus.pp.ua</code></div>
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
            <a id="tun-url-link" href="#" target="_blank" style="font-family:var(--mono);font-size:10px;color:var(--amber);text-decoration:none" id="tun-url-display"></a>
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
  document.getElementById('tun-preview').textContent = v + '-alert.exodus.pp.ua';
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
  } catch(e) { _tunShowCheck(false, 'Помилка з\'єднання'); return false; }
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
</script>
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
            "phone": env.get("TELEGRAM_PHONE", ""),
            "api_id": env.get("TELEGRAM_API_ID", ""),
            "api_hash": env.get("TELEGRAM_API_HASH", ""),
            "notify_chat_id": str(cfg.get("notify_chat_id", "")),
            "bot_token": cfg.get("bot_token", ""),
            "channel_count": str(len(cfg.get("channels", []))),
            "model": cfg.get("goclaw_model", ""),
            "user_channels_html": user_channels_html,
            "user_channel_count": str(len(user_chs)),
            "channel_total": str(len(user_chs) + len(LOCKED_CHANNELS)),
        }
        html = _re.sub(r'\{([a-z_]+)\}', lambda m: vars_.get(m.group(1), m.group(0)), HTML)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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

    def do_POST(self):
        body = self.read_body()
        data = parse_qs(body)
        get = lambda k: data.get(k, [""])[0].strip()

        path = urlparse(self.path).path

        # JSON API endpoints (Content-Type: application/json)
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
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
                reply = shelter_ai_query(user_msg, context)
                self.send_json({"ok": True, "reply": reply})
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
                    "text": "✅ UAV Watcher — тестове повідомлення. Бот налаштовано правильно!",
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
                cfg["city"] = get("city")
                cfg["city_region"] = get("city_region")
                kw_raw = get("city_keywords")
                cfg["city_keywords"] = [k.strip() for k in kw_raw.split(",") if k.strip()]
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
    print(f"UAV Watcher Config UI → http://localhost:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
