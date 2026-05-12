# UAV Alert Watcher — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Моніторити Telegram-канали на предмет БПЛА-загроз для міста Олександрія і надсилати Q персональні сповіщення через Telegram-бота.

**Architecture:** Telethon userbot (один з двох акаунтів Q) слухає список каналів через MTProto. При повідомленні з "Олександрія" — regex pre-filter, потім AI-класифікація через goclaw proxy (localhost:18880). Якщо загроза — Bot API sendMessage до Q.

**Tech Stack:** Python 3, Telethon 1.41.2, httpx (async HTTP), Telegram Bot API, goclaw OpenAI proxy (localhost:18880, key=freecc, model=fast-proxy)

**Server:** 192.168.3.184, `/home/vokov/projects/uav-watcher/`

---

### Task 0: Отримати Q's chat_id

**Передумова:** Q надсилає `/start` боту (token: `8660277592:AAEfzH9fq4jM81gyHdgvdNYi1AnXhr1anEg`).

**Step 1: Отримати updates від бота**

```bash
curl -s "https://api.telegram.org/bot8660277592:AAEfzH9fq4jM81gyHdgvdNYi1AnXhr1anEg/getUpdates" | python3 -m json.tool | grep -A3 '"from"'
```

Знайти `"id"` поля `from` — це Q's chat_id. Записати.

---

### Task 1: Ініціалізувати проект

**Files:**
- Create: `/home/vokov/projects/uav-watcher/config.json`
- Create: `/home/vokov/projects/uav-watcher/.env`
- Create: `/home/vokov/projects/uav-watcher/.gitignore`

**Step 1: Створити config.json**

```bash
cat > /home/vokov/projects/uav-watcher/config.json << 'EOF'
{
  "channels": [-1002187970584],
  "city_keywords": ["Олександрія", "Олександрійськ"],
  "bot_token": "8660277592:AAEfzH9fq4jM81gyHdgvdNYi1AnXhr1anEg",
  "notify_chat_id": REPLACE_WITH_CHAT_ID,
  "goclaw_url": "http://localhost:18880/v1/chat/completions",
  "goclaw_api_key": "freecc",
  "goclaw_model": "fast-proxy"
}
EOF
```

**Step 2: Створити .env**

```bash
cat > /home/vokov/projects/uav-watcher/.env << 'EOF'
TELEGRAM_API_ID=REPLACE_WITH_API_ID
TELEGRAM_API_HASH=REPLACE_WITH_API_HASH
TELEGRAM_PHONE=REPLACE_WITH_PHONE
EOF
```

> **Примітка:** API_ID і API_HASH — з https://my.telegram.org/apps (для акаунту-спостерігача). PHONE — телефон того акаунту.

**Step 3: .gitignore**

```bash
cat > /home/vokov/projects/uav-watcher/.gitignore << 'EOF'
.env
*.session
*.session-journal
__pycache__/
EOF
```

**Step 4: Ініціалізувати git**

```bash
cd /home/vokov/projects/uav-watcher && git init && git add config.json .gitignore && git commit -m "feat: init uav-watcher project"
```

---

### Task 2: Авторизація Telethon сесії

**Files:**
- Create: `/home/vokov/projects/uav-watcher/auth.py`

**Step 1: Написати auth.py**

```python
#!/usr/bin/env python3
"""Run once interactively to create Telethon session file."""
import asyncio, os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

async def main():
    client = TelegramClient(
        'uav_watcher',
        int(os.environ['TELEGRAM_API_ID']),
        os.environ['TELEGRAM_API_HASH']
    )
    await client.start(phone=os.environ['TELEGRAM_PHONE'])
    me = await client.get_me()
    print(f"Authorized as: {me.first_name} (@{me.username})")
    await client.disconnect()

asyncio.run(main())
```

**Step 2: Встановити python-dotenv якщо нема**

```bash
pip3 install python-dotenv --quiet
```

**Step 3: Запустити авторизацію (інтерактивно — потрібен термінал)**

```bash
cd /home/vokov/projects/uav-watcher && python3 auth.py
```

Telethon запросить SMS-код і (можливо) 2FA пароль. Після успіху з'явиться файл `uav_watcher.session`.

**Step 4: Перевірити що сесія створена**

```bash
ls -la /home/vokov/projects/uav-watcher/*.session
```

Expected: файл `uav_watcher.session` ненульового розміру.

---

### Task 3: Написати основний watcher

**Files:**
- Create: `/home/vokov/projects/uav-watcher/uav_watcher.py`

**Step 1: Написати uav_watcher.py**

```python
#!/usr/bin/env python3
"""
UAV threat watcher for Oleksandriia.
Monitors Telegram channels via Telethon, classifies via goclaw AI,
notifies via Telegram Bot API.
"""
import asyncio
import json
import logging
import os
import re
import httpx
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

async def ai_classify(text: str, cfg: dict) -> tuple[bool, str]:
    """Ask goclaw AI: is this a UAV threat for Oleksandriia?"""
    prompt = (
        "Ти система моніторингу БПЛА. Визнач: чи це повідомлення містить "
        "загрозу БПЛА (безпілотного літального апарату) або ракетну загрозу "
        "саме для міста Олександрія Кіровоградської області? "
        "Відповідь ТІЛЬКИ JSON без markdown: {\"threat\": true/false, \"reason\": \"коротко\"}\n\n"
        f"Повідомлення:\n{text}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                cfg['goclaw_url'],
                headers={
                    'Authorization': f"Bearer {cfg['goclaw_api_key']}",
                    'Content-Type': 'application/json'
                },
                json={
                    'model': cfg['goclaw_model'],
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 100,
                    'temperature': 0
                }
            )
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].strip()
            # Strip markdown code blocks if present
            content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
            result = json.loads(content)
            return result.get('threat', False), result.get('reason', '')
    except Exception as e:
        log.error(f"AI classify error: {e}")
        return False, ''

async def send_notification(text: str, reason: str, cfg: dict):
    """Send alert via Bot API."""
    msg = f"🚨 *ЗАГРОЗА БПЛА — ОЛЕКСАНДРІЯ*\n\n{text}\n\n_AI: {reason}_"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                json={
                    'chat_id': cfg['notify_chat_id'],
                    'text': msg,
                    'parse_mode': 'Markdown'
                }
            )
            resp.raise_for_status()
            log.info(f"Notification sent: {reason}")
    except Exception as e:
        log.error(f"Send notification error: {e}")

async def main():
    cfg = load_config()
    city_pattern = re.compile('|'.join(cfg['city_keywords']), re.IGNORECASE)
    channels = cfg['channels']

    client = TelegramClient(
        os.path.join(os.path.dirname(__file__), 'uav_watcher'),
        int(os.environ['TELEGRAM_API_ID']),
        os.environ['TELEGRAM_API_HASH']
    )

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        text = event.message.text or ''
        if not text:
            return
        if not city_pattern.search(text):
            return  # Pre-filter: skip if city not mentioned
        log.info(f"City keyword found, sending to AI: {text[:80]}...")
        is_threat, reason = await ai_classify(text, cfg)
        if is_threat:
            log.info(f"THREAT detected: {reason}")
            await send_notification(text, reason, cfg)
        else:
            log.info(f"Not a threat: {reason}")

    await client.start(phone=os.environ['TELEGRAM_PHONE'])
    log.info(f"Watching channels: {channels}")
    log.info("UAV watcher started. Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
```

**Step 2: Встановити httpx якщо нема**

```bash
pip3 install httpx --quiet
```

**Step 3: Commit**

```bash
cd /home/vokov/projects/uav-watcher && git add uav_watcher.py auth.py && git commit -m "feat: add uav_watcher with telethon+goclaw AI pipeline"
```

---

### Task 4: Ручне тестування

**Step 1: Запустити watcher в терміналі**

```bash
cd /home/vokov/projects/uav-watcher && python3 uav_watcher.py
```

Expected: `UAV watcher started. Watching channels: [-1002187970584]`

**Step 2: Перевірити AI класифікацію окремо**

```bash
cd /home/vokov/projects/uav-watcher && python3 - << 'EOF'
import asyncio, json
from uav_watcher import ai_classify, load_config
cfg = load_config()
result = asyncio.run(ai_classify(
    "⚠️ Увага! Загроза БПЛА. Олександрія, Знам'янка — повітряна тривога!",
    cfg
))
print(f"threat={result[0]}, reason={result[1]}")
EOF
```

Expected: `threat=True, reason=...`

**Step 3: Перевірити що відбій не тригерить**

```bash
cd /home/vokov/projects/uav-watcher && python3 - << 'EOF'
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
result = asyncio.run(ai_classify(
    "✅ Відбій. Олександрія — загроза минула.",
    cfg
))
print(f"threat={result[0]}, reason={result[1]}")
EOF
```

Expected: `threat=False, reason=...`

---

### Task 5: Systemd сервіс (автозапуск)

**Files:**
- Create: `/etc/systemd/system/uav-watcher.service`

**Step 1: Написати unit-файл**

```bash
sudo tee /etc/systemd/system/uav-watcher.service << 'EOF'
[Unit]
Description=UAV Alert Watcher for Oleksandriia
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vokov
WorkingDirectory=/home/vokov/projects/uav-watcher
EnvironmentFile=/home/vokov/projects/uav-watcher/.env
ExecStart=/usr/bin/python3 /home/vokov/projects/uav-watcher/uav_watcher.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Step 2: Активувати і запустити**

```bash
sudo systemctl daemon-reload
sudo systemctl enable uav-watcher
sudo systemctl start uav-watcher
```

**Step 3: Перевірити статус**

```bash
sudo systemctl status uav-watcher
sudo journalctl -u uav-watcher -f --no-pager -n 20
```

Expected: `Active: active (running)` і лог `UAV watcher started.`

---

### Task 6: Додати новий канал (пізніше)

Просто відредагувати `config.json`:

```json
{
  "channels": [-1002187970584, -1001234567890],
  ...
}
```

Потім `sudo systemctl restart uav-watcher`.

---

## Передумови перед стартом

1. Q надсилає `/start` боту — отримуємо `notify_chat_id`
2. Q заходить на https://my.telegram.org/apps — копіює `api_id` і `api_hash` для акаунту-спостерігача
3. Task 2 (auth.py) запускається **інтерактивно** — потрібен термінал з TTY (не фоновий процес)

