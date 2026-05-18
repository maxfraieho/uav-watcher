# Sharon v2.0 — Development Plan for Claude Code
# =====================================================
# READ THIS FIRST. This file is your primary directive.
# Project path: /home/vokov/projects/Sharon
# Status: Active wartime civilian safety system — Ukraine
# Goal: Evolve from single-alert-bot → full family safety platform

## QUICK CONTEXT

Current system (v1.x) does:
- Monitors Telegram channels for UAV/missile threats via Telethon
- AI-classifies threats via OpenAI-compatible API
- Sends one-way alerts to a single user/chat

What we need (v2.0):
- Family groups with automatic rollcall ("I'm safe" / "SOS")
- Crisis chatbot with threat-specific survival instructions
- alerts.in.ua official API integration (parallel to Telegram scraping)
- Dead man's switch (auto-SOS if user doesn't respond post-strike)
- Foundation for offline LoRa mesh (Meshtastic) — scaffold only for now

---

## WORKING RULES FOR CLAUDE CODE

1. **Ask before major refactors** — existing uav_watcher.py is in production
2. **Never break existing functionality** — add, don't replace
3. **All new modules go in subdirectories** — keep root clean
4. **Write Ukrainian UI strings, English comments/code**
5. **After each Task, run the test and confirm pass before proceeding**
6. **Commit after each completed Task** with descriptive message
7. **If a Task is blocked, report exactly why and wait for user input**

---

## PHASE 0 — IMMEDIATE WINS (Start here. Do TODAY.)
**Goal:** Ship real improvements within hours. No new dependencies needed.

---

### TASK 0.1 — Crisis Templates Bot Commands
**Files to create:** `bot/crisis_templates.py`, `bot/__init__.py`
**Modify:** `uav_watcher.py` (add imports + register handlers)
**Time:** ~1 hour

Create `bot/crisis_templates.py`:

```python
"""
Crisis response templates for Sharon chatbot.
All text is in Ukrainian. Sources: DSNS, WHO, IFRC, Israeli HFC model.
"""

TEMPLATES = {
    "uav": {
        "title": "🚁 ЗАГРОЗА БПЛА / ДРОН-КАМІКАДЗЕ",
        "text": (
            "🚁 *ЗАГРОЗА БПЛА — ДІЙ ЗАРАЗ*\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Відійди від вікон — ляж на підлогу\n"
            "• Вимкни світло, закрий штори (перекриває оптику)\n"
            "• НЕ виходь надвір — дрон відстежує рух\n"
            "• Телефон на беззвучний, але НЕ вимикай\n\n"
            "🏠 *УКРИТТЯ (правило двох стін):*\n"
            "Ванна кімната або коридор > підвал\n"
            "НЕ ховайся під сходами (ризик обвалу)\n\n"
            "💥 *ПІСЛЯ ВИБУХУ В РАДІУСІ 500м:*\n"
            "• Зачини вікна (хімічна загроза)\n"
            "• Не виходь 15 хв (можлива друга хвиля)\n"
            "• Зателефонуй: 101 або 112"
        )
    },
    "ballistic": {
        "title": "🚀 БАЛІСТИЧНА РАКЕТА / ISKANDER",
        "text": (
            "🚀 *БАЛІСТИЧНА ЗАГРОЗА — СЕКУНДИ ВИРІШУЮТЬ*\n\n"
            "⚡ Час: 2–4 хвилини до удару\n\n"
            "✅ *ЯКЩО Є ЧАС:*\n"
            "Підвал або 1-й поверх, несучі стіни\n\n"
            "✅ *ЯКЩО НЕ ВСТИГ:*\n"
            "• Ляж у будь-яке заглиблення (канава, підземний перехід)\n"
            "• Відкрий рот (від вибухової хвилі)\n"
            "• Прикрий потилицю руками\n"
            "• Відвернись від напрямку загрози\n\n"
            "📵 НЕ знімай відео — йди в укриття"
        )
    },
    "cruise": {
        "title": "✈️ КРИЛАТА РАКЕТА / KALIBR",
        "text": (
            "✈️ *КРИЛАТА РАКЕТА — УКРИЙСЯ*\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Підземний паркінг або підвал — мета №1\n"
            "• Від вікон якомога далі\n"
            "• Не стій у відкритих місцях\n\n"
            "⚠️ Kalibr летить на малій висоті — попередження може бути коротким\n\n"
            "🔇 Вимкни газ, відкрий вікно в іншій кімнаті (від вибухової хвилі)\n\n"
            "📞 Після відбою: 101 (ДСНС), 112"
        )
    },
    "fab": {
        "title": "💣 АВІАБОМБА FAB / Планер",
        "text": (
            "💣 *FAB АВІАБОМБА — МАКСИМАЛЬНА ЗАГРОЗА*\n\n"
            "‼️ Правило двох стін НЕ ПРАЦЮЄ\n"
            "‼️ Потрібен ГЛИБОКИЙ підвал або багаторівневе бомбосховище\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Глибоке бомбосховище / метро / підземний паркінг\n"
            "• НЕ залишайся в квартирі — навіть на 1-му поверсі\n"
            "• Якщо немає укриття — відійди від будівель щонайменше 50м\n"
            "• Ляж у ямку/канаву, прикрий голову\n\n"
            "📞 112 або 101 — після удару"
        )
    },
    "chemical": {
        "title": "☣️ ХІМІЧНА / ТОКСИЧНА ЗАГРОЗА",
        "text": (
            "☣️ *ХІМІЧНА ЗАГРОЗА — ГЕРМЕТИЗУЙ ПРИМІЩЕННЯ*\n\n"
            "🔴 Ознаки: незвичний запах, димова хмара, симптоми у людей\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Закрий ВСІ вікна і двері ГЕРМЕТИЧНО\n"
            "• Змочи тканину — прикрий рот і ніс\n"
            "• Піднімись вище (більшість газів важчі за повітря)\n"
            "• Заклей щілини скотчем якщо є\n\n"
            "🚫 *НЕ виходь без захисту*\n\n"
            "✅ *Якщо ти надворі:*\n"
            "• Тримайся з навітряного боку\n"
            "• Знімай одяг, рясно промивай шкіру водою\n\n"
            "📞 101 — одразу"
        )
    },
    "rubble": {
        "title": "🆘 ПІД ЗАВАЛАМИ / БУДИНОК ЗРУЙНОВАНО",
        "text": (
            "🆘 *ПІД ЗАВАЛАМИ — ЩО РОБИТИ*\n\n"
            "📱 *ЯКЩО ТИ ПІД ЗАВАЛАМИ:*\n"
            "• Натисни кнопку SOS нижче — надсилається GPS\n"
            "• Стукай по трубах або бетону КОЖНІ 30 СЕК\n"
            "• Прикрий рот тканиною від пилу\n"
            "• Дихай спокійно — економ кисень\n"
            "• НЕ кричи постійно — втратиш сили\n\n"
            "👥 *ЯКЩО ШУКАЄШ ЛЮДИНУ:*\n"
            "• Зателефонуй 101 (ДСНС) — ПЕРШОЧЕРГОВО\n"
            "• Слухай кожні 2 хвилини: стукіт, голос\n"
            "• НЕ рухай великі уламки самостійно\n"
            "• Перевір останнє місце через бота (кнопка нижче)"
        )
    },
    "allclear": {
        "title": "✅ ВІДБІЙ ТРИВОГИ",
        "text": (
            "✅ *ВІДБІЙ — НЕБЕЗПЕКА МИНУЛА*\n\n"
            "Перш ніж виходити:\n"
            "• Зачекай 5–10 хвилин після офіційного відбою\n"
            "• Оглянь вулицю через вікно перед виходом\n"
            "• Не торкайся невідомих предметів на вулиці\n\n"
            "💬 Повідом рідних що ти в безпеці (/status)\n\n"
            "📊 Перевір статус сім'ї: /family_status"
        )
    }
}

THREAT_KEYBOARD = [
    [{"text": "🚁 БПЛА/Дрон", "callback_data": "crisis_uav"},
     {"text": "🚀 Балістика", "callback_data": "crisis_ballistic"}],
    [{"text": "✈️ Крилата ракета", "callback_data": "crisis_cruise"},
     {"text": "💣 FAB бомба", "callback_data": "crisis_fab"}],
    [{"text": "☣️ Хімічна загроза", "callback_data": "crisis_chemical"},
     {"text": "🆘 Під завалами", "callback_data": "crisis_rubble"}],
    [{"text": "✅ Відбій", "callback_data": "crisis_allclear"}]
]

GROUNDING_STEPS = [
    "🟢 Крок 1/5 — Назви 5 речей які ти БАЧИШ зараз",
    "🟢 Крок 2/5 — Торкнись 4 різних поверхні поруч з тобою",
    "🟢 Крок 3/5 — Прислухайся — назви 3 звуки які чуєш",
    "🟢 Крок 4/5 — Відчуй 2 запахи або текстури",
    "🟢 Крок 5/5 — Зроби 1 глибокий вдих... і повільний видих.\n\n✅ Ти тут. Ти в безпеці. Продовжуй дихати рівно."
]
```

Then in `uav_watcher.py`, add these bot command handlers (append to `main()`):

```python
# --- CRISIS CHATBOT HANDLERS ---
from bot.crisis_templates import TEMPLATES, THREAT_KEYBOARD, GROUNDING_STEPS

@bot_app.on(events.NewMessage(pattern='/help|/допомога|/що_робити'))
async def cmd_help(event):
    from telethon.tl.types import ReplyInlineMarkup, KeyboardButtonCallback, KeyboardButtonRow
    buttons = [[KeyboardButtonCallback(row[0]["text"], row[0]["callback_data"].encode()),
                KeyboardButtonCallback(row[1]["text"], row[1]["callback_data"].encode())]
               if len(row) > 1 else
               [KeyboardButtonCallback(row[0]["text"], row[0]["callback_data"].encode())]
               for row in THREAT_KEYBOARD]
    await event.respond(
        "🛡 *Sharon — Кризовий консультант*\n\nОберіть тип загрози:",
        buttons=buttons,
        parse_mode='md'
    )

@bot_app.on(events.CallbackQuery(pattern=b'crisis_(.+)'))
async def handle_crisis_callback(event):
    threat_key = event.data.decode().replace('crisis_', '')
    if threat_key in TEMPLATES:
        template = TEMPLATES[threat_key]
        await event.edit(template["text"], parse_mode='md')
    await event.answer()

@bot_app.on(events.NewMessage(pattern='/заземлення|/calm|/панiка'))
async def cmd_grounding(event):
    """5-4-3-2-1 grounding technique for panic attacks"""
    await event.respond("🧘 *Техніка заземлення — зупинись і читай повільно:*\n\nЦе допоможе тобі повернутись у теперішній момент.", parse_mode='md')
    for step in GROUNDING_STEPS:
        import asyncio
        await asyncio.sleep(8)
        await event.respond(step)
```

**Test after Task 0.1:**
```bash
cd /home/vokov/projects/Sharon
python3 -c "from bot.crisis_templates import TEMPLATES; print('OK:', list(TEMPLATES.keys()))"
```

**Commit:** `feat: add crisis chatbot templates — 7 threat types + grounding technique`

---

### TASK 0.2 — Personal Status Command (/status)
**Modify:** `uav_watcher.py`
**Time:** ~30 minutes

Add `/status` command so user can broadcast "I'm safe" to their notify chat:

```python
@bot_app.on(events.NewMessage(pattern='/status|/статус|/безпечно'))
async def cmd_status(event):
    import datetime
    now = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
    await event.respond(f"✅ Статус оновлено: {now}\n\nЗберігаємо...")
    # Broadcast to notify_chat_id
    cfg = load_config()
    sender = await event.get_sender()
    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Користувач"
    msg = f"✅ *{name}* в безпеці\n🕐 {now}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
            json={'chat_id': cfg['notify_chat_id'], 'text': msg, 'parse_mode': 'Markdown'}
        )
```

**Commit:** `feat: add /status command — broadcast "I'm safe" to notify chat`

---

### TASK 0.3 — alerts.in.ua Official API Integration
**Files to create:** `integrations/__init__.py`, `integrations/alerts_ua.py`
**Modify:** `uav_watcher.py`, `config.json` (add alerts_ua_token field), `install.sh`
**Time:** ~2 hours

Install dependency:
```bash
pip3 install alerts-in-ua
```

Create `integrations/alerts_ua.py`:
```python
"""
Official Ukrainian air raid alert API integration.
Docs: https://devs.alerts.in.ua/
Runs in parallel with Telegram OSINT channel monitoring.
"""
import asyncio
import logging
from alerts_in_ua import AsyncClient as AlertsClient

log = logging.getLogger(__name__)

class AlertsUAPoller:
    def __init__(self, token: str, region: str, callback):
        """
        token: API key from alerts.in.ua (free for civilian use)
        region: Oblast name e.g. "Кіровоградська область"
        callback: async function(alert_type, location, started_at) to call on new threat
        """
        self.client = AlertsClient(token=token)
        self.region = region
        self.callback = callback
        self.active_alerts = set()  # Track alert IDs to avoid duplicate notifications
        log.info(f"AlertsUA poller initialized for region: {region}")

    async def poll_loop(self, interval_seconds: int = 15):
        """Main polling loop — runs alongside Telegram watcher."""
        log.info("Starting alerts.in.ua polling loop...")
        while True:
            try:
                active = await self.client.get_active_alerts()
                current_ids = set()

                for alert in active:
                    # Match region — partial match for flexibility
                    if self.region.lower() not in alert.location_title.lower():
                        continue
                    
                    alert_id = f"{alert.id}_{alert.started_at}"
                    current_ids.add(alert_id)
                    
                    # New alert — not seen before
                    if alert_id not in self.active_alerts:
                        log.info(f"NEW OFFICIAL ALERT: {alert.location_title} — {alert.alert_type}")
                        await self.callback(
                            alert_type=alert.alert_type,
                            location=alert.location_title,
                            started_at=alert.started_at
                        )
                
                # Update active set
                self.active_alerts = current_ids
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                log.error(f"alerts.in.ua polling error: {e}")
                await asyncio.sleep(30)  # Extended delay on error
```

**In `uav_watcher.py` `main()` — add the poller alongside existing watcher:**
```python
# Run official API poller concurrently if token is configured
if cfg.get('alerts_ua_token'):
    from integrations.alerts_ua import AlertsUAPoller

    async def on_official_alert(alert_type, location, started_at):
        reason = f"Офіційна тривога: {alert_type}"
        msg = f"🔴 *ОФІЦІЙНА ТРИВОГА* [{location}]\nТип: {alert_type}\nПочаток: {started_at}"
        await send_notification(msg, reason, cfg)

    poller = AlertsUAPoller(
        token=cfg['alerts_ua_token'],
        region=cfg['city_region'],
        callback=on_official_alert
    )
    asyncio.ensure_future(poller.poll_loop())
    log.info("alerts.in.ua official poller started in background")
```

**Add to config.json (add after existing fields):**
```json
"alerts_ua_token": ""
```

**Test:**
```bash
python3 -c "from integrations.alerts_ua import AlertsUAPoller; print('OK')"
```
**Commit:** `feat: integrate alerts.in.ua official API — parallel to Telegram OSINT`

---

## PHASE 1 — FAMILY SAFETY GROUPS (Do after Phase 0 is committed)
**Goal:** Family rollcall with "I'm safe" / "SOS" inline buttons

---

### TASK 1.1 — SQLite Database for Family State
**Files to create:** `db/__init__.py`, `db/models.py`
**Time:** ~1 hour

Create `db/models.py`:
```python
"""
Local SQLite database for family groups and rollcall state.
Zero external dependencies — all data stored locally for OPSEC.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'families.db')

def init_db():
    """Initialize database schema on first run."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Family groups
    c.execute('''CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_user_id INTEGER NOT NULL,
        invite_code TEXT UNIQUE NOT NULL,
        telegram_group_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Family members
    c.execute('''CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER REFERENCES families(id),
        user_id INTEGER NOT NULL,
        username TEXT,
        display_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(family_id, user_id)
    )''')
    
    # Rollcall events — one per threat alert
    c.execute('''CREATE TABLE IF NOT EXISTS rollcalls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER REFERENCES families(id),
        threat_type TEXT,
        initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    )''')
    
    # Individual responses to rollcall
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
    import secrets
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    invite_code = secrets.token_urlsafe(8).upper()
    c.execute(
        "INSERT INTO families (name, creator_user_id, invite_code) VALUES (?,?,?)",
        (name, creator_id, invite_code)
    )
    family_id = c.lastrowid
    # Auto-add creator as first member
    c.execute(
        "INSERT INTO family_members (family_id, user_id) VALUES (?,?)",
        (family_id, creator_id)
    )
    conn.commit()
    conn.close()
    return {"id": family_id, "name": name, "invite_code": invite_code}

def join_family(invite_code: str, user_id: int, username: str = None, display_name: str = None) -> dict | None:
    """Join existing family by invite code."""
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
    # Pre-populate with no_response for all members
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
    c.execute("""SELECT status, COUNT(*) FROM rollcall_responses 
                 WHERE rollcall_id=? GROUP BY status""", (rollcall_id,))
    counts = {r[0]: r[1] for r in c.fetchall()}
    c.execute("""SELECT user_id, display_name, username, status FROM rollcall_responses 
                 JOIN family_members USING(user_id) WHERE rollcall_id=?""", (rollcall_id,))
    details = [{"user_id": r[0], "name": r[1] or r[2] or str(r[0]), "status": r[3]}
               for r in c.fetchall()]
    conn.close()
    return {
        "safe": counts.get("safe", 0),
        "sos": counts.get("sos", 0),
        "no_response": counts.get("no_response", 0),
        "details": details
    }
```

**Test:**
```bash
python3 -c "
from db.models import init_db, create_family, join_family, get_family_members
init_db()
f = create_family('Тест Сім\\'я', 12345)
print('Created:', f)
m = join_family(f['invite_code'], 67890, 'testuser', 'Тест Юзер')
print('Joined:', m)
print('Members:', get_family_members(f['id']))
"
```
**Commit:** `feat: add SQLite family groups database schema`

---

### TASK 1.2 — Family Bot Commands
**Files to create:** `family/bot_handlers.py`
**Modify:** `uav_watcher.py`
**Time:** ~2 hours

Create `family/bot_handlers.py` with `/family_create`, `/family_join`, `/family_status`, `/sos` commands:

```python
"""
Family safety group bot command handlers.
Uses db/models.py for persistence and bot API for notifications.
"""
import asyncio
import logging
import httpx
from db.models import (init_db, create_family, join_family, 
                        get_family_members, get_user_families,
                        start_rollcall, record_rollcall_response, 
                        get_rollcall_status)

log = logging.getLogger(__name__)

def register_family_handlers(bot_client, cfg):
    """Register all family-related event handlers on the bot client."""
    from telethon import events

    init_db()  # Ensure DB exists

    @bot_client.on(events.NewMessage(pattern=r'/family_create (.+)'))
    async def cmd_family_create(event):
        """Create a new family group: /family_create Назва Сім'ї"""
        sender = await event.get_sender()
        name = event.pattern_match.group(1).strip()
        family = create_family(name, sender.id)
        await event.respond(
            f"✅ *Сімейну групу створено!*\n\n"
            f"👨‍👩‍👧 Назва: {family['name']}\n"
            f"🔑 Код запрошення: `{family['invite_code']}`\n\n"
            f"Поділись кодом з рідними — вони приєднаються командою:\n"
            f"`/family_join {family['invite_code']}`",
            parse_mode='md'
        )

    @bot_client.on(events.NewMessage(pattern=r'/family_join (.+)'))
    async def cmd_family_join(event):
        """/family_join КОД — приєднатися до сім'ї"""
        sender = await event.get_sender()
        code = event.pattern_match.group(1).strip().upper()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        family = join_family(code, sender.id, sender.username, name)
        if family:
            await event.respond(
                f"✅ Ти доданий до сім'ї *{family['name']}*!\n"
                f"При наступній тривозі бот запитає: чи ти в безпеці.",
                parse_mode='md'
            )
        else:
            await event.respond("❌ Код не знайдено. Перевір правильність.")

    @bot_client.on(events.NewMessage(pattern='/family_status|/сім\\'я'))
    async def cmd_family_status(event):
        """/family_status — показати членів всіх своїх груп"""
        sender = await event.get_sender()
        families = get_user_families(sender.id)
        if not families:
            await event.respond(
                "У тебе немає сімейних груп.\n"
                "Створи: `/family_create Назва`\n"
                "або приєднайся: `/family_join КОД`",
                parse_mode='md'
            )
            return
        text = "👨‍👩‍👧 *Твої сімейні групи:*\n\n"
        for f in families:
            members = get_family_members(f['id'])
            text += f"• *{f['name']}* (код: `{f['invite_code']}`)\n"
            text += f"  Учасники: {len(members)}\n"
        await event.respond(text, parse_mode='md')

    @bot_client.on(events.NewMessage(pattern='/sos|/SOS|/допоможіть'))
    async def cmd_sos(event):
        """/sos — emergency SOS to all families"""
        sender = await event.get_sender()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        families = get_user_families(sender.id)
        if not families:
            await event.respond("❌ Ти не в жодній сімейній групі.\n/family_join КОД")
            return
        # Notify each family's creator
        sos_msg = f"🆘🆘🆘 *ЕКСТРЕНИЙ СИГНАЛ SOS*\n\n{name} потребує допомоги!\n\nЗателефонуй негайно."
        await event.respond("🆘 SOS надіслано всім членам твоїх сімейних груп.")
        for family in families:
            members = get_family_members(family['id'])
            for m in members:
                if m['user_id'] != sender.id:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                                json={'chat_id': m['user_id'], 'text': sos_msg, 'parse_mode': 'Markdown'}
                            )
                    except Exception as e:
                        log.error(f"SOS delivery failed to {m['user_id']}: {e}")

    return {
        'rollcall': lambda family_id, threat_type: _run_rollcall(bot_client, cfg, family_id, threat_type)
    }


async def _run_rollcall(bot_client, cfg, family_id: int, threat_type: str):
    """
    Trigger automatic rollcall for a family when threat is detected.
    Sends inline buttons to each member: ✅ В безпеці / 🆘 Потрібна допомога
    """
    from telethon import events
    rollcall_id = start_rollcall(family_id, threat_type)
    members = get_family_members(family_id)
    
    threat_labels = {
        'air_raid': '🚨 Повітряна тривога',
        'uav': '🚁 Загроза БПЛА',
        'ballistic': '🚀 Балістична загроза',
    }
    label = threat_labels.get(threat_type, f'⚠️ Загроза: {threat_type}')
    
    msg = (
        f"{label}\n\n"
        f"❓ Підтвердь свій статус:\n"
        f"Ти маєш 10 хвилин — інакше буде надіслано SOS."
    )
    buttons = [
        [{"text": "✅ Я В БЕЗПЕЦІ", "callback_data": f"rc_safe_{rollcall_id}"},
         {"text": "🆘 ПОТРІБНА ДОПОМОГА", "callback_data": f"rc_sos_{rollcall_id}"}]
    ]
    
    for member in members:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                    json={
                        'chat_id': member['user_id'],
                        'text': msg,
                        'parse_mode': 'Markdown',
                        'reply_markup': {'inline_keyboard': buttons}
                    }
                )
        except Exception as e:
            log.error(f"Rollcall delivery failed to {member['user_id']}: {e}")
    
    # After 10 minutes — check for non-responses and send SOS alerts
    await asyncio.sleep(600)
    status = get_rollcall_status(rollcall_id)
    for detail in status['details']:
        if detail['status'] == 'no_response':
            alert_msg = (
                f"⚠️ *{detail['name']}* не відповів протягом 10 хвилин!\n"
                f"Можливо потрібна допомога. Зателефонуй або перевір."
            )
            for other in members:
                if other['user_id'] != detail['user_id']:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                                json={'chat_id': other['user_id'], 'text': alert_msg, 'parse_mode': 'Markdown'}
                            )
                    except Exception as e:
                        log.error(f"No-response alert failed: {e}")
```

**Commit:** `feat: family rollcall system with inline Safe/SOS buttons and 10min dead-man check`

---

## PHASE 2 — DEAD MAN'S SWITCH + GPS SOS (After Phase 1)
**Goal:** Find person even if they can't respond

### TASK 2.1 — Location Check-in and Dead Man's Switch
**Files to create:** `rescue/location_tracker.py`
**Time:** ~2 hours

Key features:
- User sends `/checkin` → bot saves last known location (from Telegram's Location message)
- After threat + no rollcall response → bot sends last known location to family members
- Configurable check-in interval (default: every 4 hours, every 30min during active alert)

```python
"""
Location check-in and dead man's switch for victim location under rubble.
Stores last known location per user in SQLite.
"""
import sqlite3, logging
from datetime import datetime, timedelta
from db.models import DB_PATH

log = logging.getLogger(__name__)

def save_checkin(user_id: int, lat: float, lon: float, address: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS location_checkins (
        user_id INTEGER PRIMARY KEY,
        lat REAL, lon REAL, address TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute(
        "INSERT OR REPLACE INTO location_checkins (user_id, lat, lon, address, updated_at) VALUES (?,?,?,?,?)",
        (user_id, lat, lon, address, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_last_location(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lat, lon, address, updated_at FROM location_checkins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"lat": row[0], "lon": row[1], "address": row[2], "updated_at": row[3]}
    return None
```

---

## PHASE 3 — SCAFFOLD ONLY (Do not implement yet — prepare structure)

### TASK 3.1 — Meshtastic Bridge Scaffold
Create empty `integrations/meshtastic_bridge.py` with TODO comments.
This signals intent but doesn't add broken imports.

### TASK 3.2 — PWA Client Scaffold
Create `web/pwa/index.html` with minimal shell and TODO comments.

---

## RUNNING THE FULL SYSTEM

After all Phase 0 tasks:
```bash
cd /home/vokov/projects/Sharon
python3 uav_watcher.py
```

New bot commands available:
- `/help` or `/що_робити` → threat type menu
- `/status` → "I'm safe" broadcast
- `/заземлення` → panic attack grounding
- `/family_create Назва` → create family group
- `/family_join КОД` → join family
- `/family_status` → view family
- `/sos` → emergency SOS to all family members

---

## INTERACTION PROTOCOL WITH USER

After completing each Task, report in this format:

```
✅ TASK X.X DONE
Час: XX хв
Що зроблено: [1 рядок]
Тест: PASS / FAIL [деталі]
Комміт: [хеш]
Питання до тебе: [якщо є]
Наступний Task: X.X — починаю? (Y/N від користувача)
```

If blocked:
```
⛔ TASK X.X БЛОК
Причина: [точно що не так]
Потрібно від тебе: [конкретно]
```

---

## PROJECT STRUCTURE AFTER ALL PHASES

```
Sharon/
├── CLAUDE.md                    ← THIS FILE
├── uav_watcher.py               ← Main daemon (modified)
├── auth.py                      ← Telethon auth (unchanged)
├── web_config.py                ← Web UI (unchanged)
├── config.json                  ← Add: alerts_ua_token
├── .env                         ← Unchanged
├── bot/
│   ├── __init__.py
│   └── crisis_templates.py      ← NEW: 7 threat templates
├── db/
│   ├── __init__.py
│   └── models.py                ← NEW: SQLite family DB
├── family/
│   ├── __init__.py
│   └── bot_handlers.py          ← NEW: /family_* commands
├── integrations/
│   ├── __init__.py
│   ├── alerts_ua.py             ← NEW: official API
│   └── meshtastic_bridge.py     ← SCAFFOLD
├── rescue/
│   ├── __init__.py
│   └── location_tracker.py      ← NEW: GPS check-in
├── web/
│   └── pwa/                     ← SCAFFOLD
└── data/
    └── families.db              ← AUTO-CREATED by SQLite
```

---

## SECURITY REMINDERS

1. Never log GPS coordinates to stdout in production
2. families.db must NOT be in git — add to .gitignore
3. Bot token stays in config.json — never in source code
4. alerts_ua_token same — config.json only
5. Rate limit all bot API calls — max 25/sec, queue the rest
