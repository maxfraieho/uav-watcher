# Sharon — План розвитку

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Довести Sharon від особистого пілоту до відкритого інструменту, який будь-яке місто України може розгорнути за 30 хвилин.

**Architecture:** Telethon userbot → keyword+AI classifier → SQLite ring buffer → LangGraph consultant (Sharon) + progressive Telegram alerts. Кожне місто розгортає власний екземпляр з локальним `config.json` та knowledge base.

**Tech Stack:** Python 3.11+, Telethon, FastAPI, LangGraph, BM25Plus, SQLite WAL, NVIDIA NIM (Llama 4 Maverick), OpenRC / systemd.

**Repo:** `git@github.com:maxfraieho/uav-watcher.git` · branch `master`
**Dev server:** `192.168.3.184` · user `vokov` · pass `805235io.`
**Services:** `uav-watcher` (OpenRC), `uav-consultant` (OpenRC)

---

## Фази розвитку

```
Phase 1 — Запуск (термінові)       ~2 год
Phase 2 — Надійність               ~4 год
Phase 3 — Open Source polish       ~3 год
Phase 4 — Нові фічі                ~8 год
Phase 5 — Масштабування            ~?
```

---

## Phase 1: Запуск після security cleanup

### Task 1: Новий bot token

**Контекст:** Старий token відкликано через BotFather (був в публічному git). Сервіс зупинений.

**Files:**
- Modify: `/home/vokov/projects/uav-watcher/config.json` (локально на сервері, не в git)

**Step 1: Отримати новий token**
```
Telegram → @BotFather → /mybots → вибрати бота → API Token → Revoke (якщо не зроблено) → Generate
```

**Step 2: Оновити config.json на сервері**
```bash
ssh vokov@192.168.3.184
# Відредагувати config.json, замінити bot_token
nano /home/vokov/projects/uav-watcher/config.json
```

**Step 3: Перезапустити сервіси**
```bash
sudo rc-service uav-watcher restart
sudo rc-service uav-consultant restart
```

**Step 4: Перевірити**
```bash
curl http://192.168.3.184:8770/health
# → {"status":"ok","kb_sections":122}
# Надіслати /start боту в Telegram
```

---

### Task 2: Перевірити та оновити requirements.txt

**Files:**
- Modify: `/home/vokov/projects/uav-watcher/requirements.txt`

**Step 1: Порівняти з реальними залежностями**
```bash
ssh vokov@192.168.3.184
pip3 freeze | grep -E "telethon|httpx|fastapi|langgraph|rank_bm25|watchdog|aiofiles|uvicorn|alembic|sqlalchemy"
cat /home/vokov/projects/uav-watcher/requirements.txt
```

**Step 2: Оновити якщо щось відсутнє**
```bash
# Перевірити що consultant/memory/* і geo_monitor.py використовують
grep -r "^import\|^from" /home/vokov/projects/uav-watcher/consultant/memory/ | grep -v __pycache__
```

**Step 3: Commit**
```bash
cd /home/vokov/projects/uav-watcher
git add requirements.txt
git commit -m "deps: update requirements.txt with all current dependencies"
git push origin master
```

---

### Task 3: Додати LICENSE

**Files:**
- Create: `/home/vokov/projects/uav-watcher/LICENSE`

**Step 1: Створити MIT license**
```bash
cat > /home/vokov/projects/uav-watcher/LICENSE << 'EOF'
MIT License

Copyright (c) 2026 Sharon Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

**Step 2: Commit**
```bash
cd /home/vokov/projects/uav-watcher
git add LICENSE
git commit -m "add MIT license"
git push origin master
```

---

## Phase 2: Надійність

### Task 4: Self-monitoring — сповіщення якщо Sharon впала

**Проблема:** якщо `uav-consultant` або `uav-watcher` впали, ніхто не знає.

**Files:**
- Create: `/home/vokov/projects/uav-watcher/watchdog_notify.sh`
- Modify: OpenRC cron або `/etc/periodic/5min/`

**Step 1: Написати скрипт перевірки**
```bash
cat > /home/vokov/projects/uav-watcher/watchdog_notify.sh << 'EOF'
#!/bin/sh
BOT_TOKEN=$(python3 -c "import json; print(json.load(open('/home/vokov/projects/uav-watcher/config.json'))['bot_token'])")
CHAT_ID=$(python3 -c "import json; print(json.load(open('/home/vokov/projects/uav-watcher/config.json'))['notify_chat_id'])")

send_alert() {
    curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=⚡ SHARON MONITOR: $1"
}

# Check consultant
if ! curl -sf http://localhost:8770/health > /dev/null 2>&1; then
    send_alert "uav-consultant DOWN — Sharon не відповідає на :8770"
fi

# Check uav-watcher process
if ! rc-service uav-watcher status | grep -q started; then
    send_alert "uav-watcher DOWN — моніторинг каналів зупинено"
    rc-service uav-watcher restart
fi
EOF
chmod +x /home/vokov/projects/uav-watcher/watchdog_notify.sh
```

**Step 2: Додати в cron кожні 5 хвилин**
```bash
echo "*/5 * * * * /home/vokov/projects/uav-watcher/watchdog_notify.sh >> /var/log/sharon-watchdog.log 2>&1" | crontab -
```

**Step 3: Тест**
```bash
sudo rc-service uav-consultant stop
sleep 10
# Має прийти сповіщення в Telegram
sudo rc-service uav-consultant start
```

---

### Task 5: Міграція goclaw_* → llm_proxy_* в uav_watcher.py

**Проблема:** `uav_watcher.py` читає `cfg["goclaw_url"]`, `cfg["goclaw_api_key"]`, `cfg["goclaw_model"]` напряму. Нові користувачі з `config.example.json` (де тільки `llm_proxy_*`) зламаються.

**Files:**
- Modify: `/home/vokov/projects/uav-watcher/uav_watcher.py:140-160`

**Step 1: Знайти всі goclaw reads у uav_watcher.py**
```bash
grep -n "goclaw" /home/vokov/projects/uav-watcher/uav_watcher.py
```

**Step 2: Замінити на llm_proxy_* з fallback**
```python
# Замінити:
cfg["goclaw_url"]
cfg["goclaw_api_key"]
cfg["goclaw_model"]

# На:
cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")
cfg.get("llm_proxy_token") or cfg.get("goclaw_api_key", "")
cfg.get("llm_proxy_model") or cfg.get("goclaw_model", "")
```

**Step 3: Перевірити що ai_classify() працює**
```bash
cd /home/vokov/projects/uav-watcher
python3 -c "
import asyncio, json
from uav_watcher import ai_classify, load_config
cfg = load_config()
result = asyncio.run(ai_classify('Повітряна тривога у місті', cfg))
print(result)
"
```
Expected: `(True, 'повітряна тривога у місті')`

**Step 4: Commit**
```bash
git add uav_watcher.py
git commit -m "fix: use llm_proxy_* keys in ai_classify, goclaw_* as fallback"
git push origin master
```

---

### Task 6: Graceful config reload

**Проблема:** зараз зміна `config.json` потребує рестарту сервісу.

**Files:**
- Modify: `/home/vokov/projects/uav-watcher/uav_watcher.py` — `load_config()` кешування з TTL

**Step 1: Додати TTL cache в load_config()**
```python
import time as _time

_config_cache = {}
_config_mtime = 0.0

def load_config(path="config.json"):
    global _config_cache, _config_mtime
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return _config_cache
    if mtime == _config_mtime and _config_cache:
        return _config_cache
    with open(path) as f:
        _config_cache = json.load(f)
    _config_mtime = mtime
    return _config_cache
```

**Step 2: Тест (змінити config.json → перевірити через 1 хв без рестарту)**

---

## Phase 3: Open Source Polish

### Task 7: docker-compose.yml

**Мета:** `docker-compose up` → система запущена за 5 хвилин.

**Files:**
- Create: `/home/vokov/projects/uav-watcher/Dockerfile`
- Create: `/home/vokov/projects/uav-watcher/Dockerfile.consultant`
- Create: `/home/vokov/projects/uav-watcher/docker-compose.yml`

**Step 1: docker-compose.yml**
```yaml
version: "3.9"
services:
  watcher:
    build: .
    command: python uav_watcher.py
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
    restart: unless-stopped
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_PHONE=${TELEGRAM_PHONE}

  consultant:
    build:
      context: .
      dockerfile: Dockerfile.consultant
    ports:
      - "8770:8770"
    volumes:
      - ./config.json:/app/config.json:ro
      - ./consultant/knowledge:/app/consultant/knowledge
      - ./data:/app/data
    restart: unless-stopped
```

**Step 2: Базовий Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

---

### Task 8: CONTRIBUTING.md + issue templates

**Files:**
- Create: `/home/vokov/projects/uav-watcher/CONTRIBUTING.md`
- Create: `/home/vokov/projects/uav-watcher/.github/ISSUE_TEMPLATE/city-setup.md`
- Create: `/home/vokov/projects/uav-watcher/.github/ISSUE_TEMPLATE/bug-report.md`

**Вміст CONTRIBUTING.md:** як додати knowledge base для свого міста, як тестувати Sharon локально, як надіслати PR.

---

## Phase 4: Нові фічі

### Task 9: Геолокаційна класифікація (архітектура готова)

**Контекст:** зараз keyword-matching ("ВашеМісто", "ВашеМісто"). Детальна архітектура в `docs/city-adaptation.md`.

**Files:**
- Create: `/home/vokov/projects/uav-watcher/geo_classifier.py`
- Modify: `/home/vokov/projects/uav-watcher/uav_watcher.py` — замінити keyword check

**Алгоритм:**
```python
# extract_locations(text) → список топонімів
# geocode_batch(locations) → [(lat, lon, name)]
# filter_by_radius(coords, city_lat, city_lon, radius_km) → proximity_score 0.0-1.0
# Якщо score > 0.3 → передати AI для підтвердження
```

**Залежності:** `geopy`, `requests` (Nominatim API)

---

### Task 10: Підписка користувачів

**Мета:** будь-хто може написати `/start` боту і отримувати сповіщення (зараз тільки `notify_chat_id`).

**Files:**
- Create: `/home/vokov/projects/uav-watcher/db/subscribers.py`
- Modify: `/home/vokov/projects/uav-watcher/uav_watcher.py` — broadcast замість single chat

**Команди:**
- `/start` → підписатись
- `/stop` → відписатись
- `/status` → поточний рівень загрози

---

### Task 11: Виправити Sharon semantic edge cases

**Проблема:** тест #63 (офтопік → crisis grounding), #65 (запит коду → написав код).

**Files:**
- Modify: `consultant/pipeline/nodes.py` — `CASUAL_SYSTEM_PROMPT`

**Step 1: Перевірити поточні failing тести**
```bash
ssh vokov@192.168.3.184
cd /home/vokov/projects/uav-watcher/consultant
python -m pytest tests/ -k "63 or 65" -v
```

**Step 2: Уточнити CASUAL_SYSTEM_PROMPT правило офтопіку**
```python
# Додати в правило 4 (off-topic):
# "Якщо запитують написати код, поясни що ти кризовий консультант, не розробник"
```

---

## Phase 5: Масштабування

### Task 12: Multi-city SaaS

Концепція: один сервер → кілька міст. Кожне місто — окремий Docker container з власним `config.json`.

```
sharon-coordinator/
  cities/
    mykolaiv/config.json
    kharkiv/config.json
    odesa/config.json
```

Потребує: повна контейнеризація (Task 7), координатор для спільного NIM API key quota.

---

## Пріоритети

```
НЕГАЙНО:   Task 1 (bot token) — без цього нічого не працює
ЦЬОГО ТИЖНЯ: Task 2 (requirements), Task 3 (LICENSE), Task 5 (goclaw migration)
НАСТУПНИЙ ТИЖДЕНЬ: Task 4 (watchdog), Task 7 (docker), Task 6 (config reload)
ПОТІМ: Task 9 (geo), Task 10 (subscribers), Task 11 (tests)
ДАЛЕКО: Task 12 (multi-city)
```
