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
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

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


HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UAV Watcher — Налаштування</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500&display=swap" rel="stylesheet">
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
</style>
</head>
<body>
<div class="topbar">
  <div class="dot"></div>
  <span class="topbar-title">UAV WATCHER</span>
  <span class="topbar-sub">— система моніторингу БПЛА-загроз</span>
  <span class="status-pill {status_class}">{status_text}</span>
</div>

<div class="layout">
  <div class="col-main">

    {flash_html}

    <!-- CITY CONFIG -->
    <div class="card">
      <div class="card-header"><span class="card-title">🏙 Місто моніторингу</span></div>
      <form method="POST" action="/save-city">
      <div class="card-body">
        <div>
          <label>Назва міста</label>
          <input type="text" name="city" value="{city}" placeholder="Олександрія">
        </div>
        <div>
          <label>Область</label>
          <input type="text" name="city_region" value="{city_region}" placeholder="Кіровоградська область">
        </div>
        <div>
          <label>Ключові слова (через кому)</label>
          <input type="text" name="city_keywords" value="{city_keywords}" placeholder="Олександрія, Олександрійськ">
          <div class="hint" style="margin-top:5px">Слова для попередньої фільтрації — якщо жодне не знайдено в тексті, AI не викликається.</div>
        </div>
        <div class="btn-row">
          <button type="submit" class="btn btn-primary">Зберегти</button>
        </div>
      </div>
      </form>
    </div>

    <!-- CHANNELS -->
    <div class="card" id="channels-card">
      <div class="card-header" style="justify-content:space-between">
        <span class="card-title">📡 Канали моніторингу</span>
        <span class="ch-total" id="ch-total">{channel_total} активних</span>
      </div>
      <div style="padding:0">

        <div class="ch-section">
          <div class="ch-section-label">🔒 СИСТЕМНИЙ — ЗАВЖДИ АКТИВНИЙ</div>
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
          <div class="ch-section-label">📻 ВАШІ КАНАЛИ <span id="user-ch-count" style="font-weight:400;opacity:0.6">{user_channel_count}</span></div>
          <div id="user-channels-list">
            {user_channels_html}
          </div>

          <div class="ch-add-wrap">
            <div class="ch-add-row">
              <input type="text" id="ch-input" class="ch-input" placeholder="@username або -1001234567890"
                onkeydown="if(event.key==='Enter'){resolveChannel()}">
              <button class="btn btn-ghost ch-btn" onclick="resolveChannel()" id="ch-resolve-btn" style="white-space:nowrap">Перевірити</button>
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
      <div class="card-header"><span class="card-title">🔑 Telegram User Bot (Telethon)</span></div>
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
          <label>Номер телефону</label>
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
          <button type="submit" class="btn btn-primary">Зберегти</button>
          <span class="hint">Після збереження потрібно запустити <code>python3 auth.py</code> в терміналі для авторизації сесії</span>
        </div>
      </div>
      </form>
    </div>

  </div>

  <div class="col-side">

    <!-- USER ID INSTRUCTION -->
    <div class="card">
      <div class="card-header"><span class="card-title">📲 Куди надсилати сповіщення</span></div>
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
            <label>Notify Chat ID (твій Telegram User ID)</label>
            <input type="text" name="notify_chat_id" value="{notify_chat_id}" placeholder="123456789">
          </div>
          <div class="btn-row" style="margin-top:8px">
            <button type="submit" class="btn btn-primary" style="height:30px;font-size:10px;">Зберегти Chat ID</button>
          </div>
        </form>
      </div>
    </div>

    <!-- SERVICE CONTROL -->
    <div class="card">
      <div class="card-header"><span class="card-title">⚙ Сервіс</span></div>
      <div class="card-body">
        <form method="POST" action="/restart">
          <button type="submit" class="btn btn-ghost" style="width:100%">↺ Перезапустити сервіс</button>
        </form>
        <div class="hint">Після зміни конфігурації або каналів — перезапусти сервіс.</div>
        <div class="separator"></div>
        <div class="hint">
          <strong style="color:rgba(255,255,255,0.6)">Поточний стан:</strong><br>
          City: <code>{city}</code><br>
          Channels: <code>{channel_count}</code><br>
          Model: <code>{model}</code>
        </div>
      </div>
    </div>

    <!-- BOT TOKEN -->
    <div class="card">
      <div class="card-header"><span class="card-title">🤖 Telegram Bot — сповіщувач</span></div>
      <div class="card-body">

        <details open>
          <summary class="steps-toggle">Як створити бота через BotFather</summary>
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
            <button type="submit" class="btn btn-primary" style="height:30px;font-size:10px;">Зберегти токен</button>
            <button type="button" class="btn btn-ghost" style="height:30px;font-size:10px;" onclick="sendTest()">▶ Тест</button>
          </div>
          <div id="test-result" style="margin-top:8px;display:none"></div>
        </form>

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
  btn.textContent = 'Перевірити';
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
  list.innerHTML = d.user_channels.map(ch => channelRow(ch)).join('') || '<div style="padding:6px 0;font-family:var(--mono);font-size:10px;color:var(--dim)">— немає власних каналів —</div>';
  count.textContent = d.user_channels.length;
  total.textContent = (d.user_channels.length + d.locked_count) + ' активних';
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
    res.textContent = 'Помилка з\'єднання';
  }
  btn.disabled = false;
  btn.textContent = '▶ Тест';
}
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

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
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
