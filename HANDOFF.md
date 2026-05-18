# Sharon — Handoff для нового Claude

> Цей документ дає повний контекст для продовження розробки Sharon без попередньої розмови.
> **Останнє оновлення:** 2026-05-18, git `8c572a7`

---

## Що це за проект

**Sharon** — гіперлокальна AI-система моніторингу повітряних загроз для міст України.
Стежить за 5+ Telegram-каналами, класифікує загрози AI, надсилає прицільні сповіщення.
Включає AI-консультант Sharon (FastAPI :8770) і пошук укриттів.

**Репозиторій:** `https://github.com/maxfraieho/uav-watcher` · гілка `master`

---

## Інфраструктура

| Ресурс | Значення |
|--------|---------|
| Dev server | `192.168.3.184` (Alpine Linux, Raspberry Pi 4) |
| SSH | `sshpass -p '805235io.' ssh -o StrictHostKeyChecking=no vokov@192.168.3.184` |
| Проект | `/home/vokov/projects/uav-watcher/` |
| Сервіс watcher | `sudo rc-service uav-watcher restart` |
| Сервіс consultant | `sudo rc-service uav-consultant restart` |
| Логи watcher | `tail -f /var/log/uav-watcher.log` |
| Логи consultant | `tail -f /var/log/uav-consultant.log` |
| Sharon API | `curl http://192.168.3.184:8770/health` |
| Web UI | `http://192.168.3.184:8422` |

**УВАГА:** `config.json` НЕ в git. Ніколи не комітити. Містить: bot_token, NIM API key, координати міста.

---

## Архітектура

```
Telegram-канали (5+)
    ↓ Telethon userbot (uav_watcher.py)
    ├─► keyword_classify() — без AI, миттєво
    ├─► ai_classify()      — Llama 4 Maverick via NVIDIA NIM
    ├─► send_notification() — dedup 90s + level-aware escalation bypass
    └─► channel_feed.db    — SQLite ring buffer (500 msg, 2h)
              ↓
    situation_monitor (daemon thread, consultant/memory/situation_monitor.py)
         → LLM оцінює рівень 0-3 → прогресивний Telegram alert

Telegram Bot (uav_watcher.py — bot_app)
    /shelter <address>      → shelter_search.py → OSM/ebot/seed
    /start, /help           → кнопки кризових ситуацій
    Геолокація від юзера    → rescue/location_tracker.py → auto shelter search
    Текст                   → http://localhost:8770/chat (Sharon)

Sharon consultant (FastAPI :8770)
    retrieve_kb() → channel_feed + summarizer + alerts.in.ua + BM25Plus
    generate()    → Llama 4 Maverick → відповідь
```

---

## Ключові файли

| Файл | Призначення |
|------|-------------|
| `uav_watcher.py` | Головний процес: Telethon + AI + Bot + monitor |
| `shelter_search.py` | Пошук укриттів: @UkraineShelterStfalconBot → Overpass OSM → seed |
| `rescue/location_tracker.py` | GPS check-in + авто-пошук укриттів при share location |
| `geo_monitor.py` | Геолокаційний моніторинг сімей |
| `consultant/main.py` | FastAPI Sharon: /chat, /health, /feed, /situation |
| `consultant/pipeline/nodes.py` | retrieve_kb(), generate(), system prompts |
| `consultant/pipeline/graph.py` | LangGraph: retrieve → web_search → generate |
| `consultant/memory/channel_feed.py` | SQLite ring buffer для повідомлень каналів |
| `consultant/memory/summarizer.py` | Background AI summary кожні 5 хв |
| `consultant/memory/situation_monitor.py` | 4-рівневий проактивний монітор |
| `consultant/knowledge_base/retrieval.py` | BM25Plus singleton (auto-reindex watchdog) |
| `consultant/knowledge/*.md` | База знань — редагуй вільно, авто-реіндекс |
| `web_config.py` | Веб UI налаштувань (:8422) |
| `config.json` | **НЕ в git** — секрети, координати міста |
| `config.example.json` | Публічний шаблон |
| `docs/plans/2026-05-18-sharon-roadmap.md` | Plan розвитку Task 1–12 |

---

## Shelter Search — як працює (реалізовано 2026-05-18)

```
/shelter <адреса> або share location
    ↓
find_shelters_enhanced(user_client, lat, lon)
    1. @UkraineShelterStfalconBot — userbot надсилає GPS, збирає відповіді (text+geo пари)
       _parse_ebot_messages() → точні координати з MessageMediaGeo
       dedup threshold: 30м (будинки-сусіди залишаються, ідентичні видаляються)
    2. Fallback: Overpass API (civil_defence=shelter, emergency=shelter, building=bunker)
    3. Fallback: seed file data/shelters_seed_oleksandria.json
    Cache: 24h у data/shelters_cache.json
```

**При share location** (`rescue/location_tracker.py`):
- Зберігає GPS в `location_checkins` SQLite таблиці
- Автоматично шукає укриття через `find_shelters_enhanced(user_client, lat, lon)`
- `user_client` передається з `uav_watcher.py:539`: `register_location_handlers(bot_app, cfg, user_client=client)`

---

## Dedup логіка сповіщень

```python
# uav_watcher.py (top-level globals)
_last_notify_time: float = 0.0
_last_notify_level: int = 0
_NOTIFY_COOLDOWN_SEC = 90

def _infer_level(text, reason) -> int:
    # L3: вибух/прямо над/над містом/над нами/над головою
    # L2: у місті/по місту/в напрямку міста/тривога у місті
    # L1: все інше (регіон)

# В send_notification():
# level > _last_notify_level → bypass cooldown (ескалація)
# level <= _last_notify_level і elapsed < 90s → suppress + log
```

---

## LLM конфігурація

- **Provider:** NVIDIA NIM
- **URL:** `https://integrate.api.nvidia.com/v1`  
- **Model:** `meta/llama-4-maverick-17b-128e-instruct`
- **Key:** `config.json → llm_proxy_token`
- **Безкоштовний tier:** 1000 req/day

---

## Стан безпеки

- `config.json` видалено з git history (git-filter-repo) ✅
- `exodus.pp.ua` → `YOUR_PROXY_URL` в усіх tracked файлах ✅
- `.gitignore`: `*.db`, `*.db-shm`, `*.db-wal`, `*.log`, `*.session`, `config.json` ✅
- 42 публічні репо maxfraieho → приватні (крім uav-watcher) ✅
- Документація: README, disclaimer, city-adaptation, legal ✅

---

## Pending / Відкриті питання

### 🔴 Критичне
1. **Новий bot token** — старий відкликано (був в публічному git). Telegram → @BotFather → /mybots → Regenerate → оновити `config.json` на сервері.

### 🟡 Важливо  
2. **Перевірити /shelter для реального юзера** — тест з вул. 6-го Грудня 141/2 (з HANDOFF попередньої сесії)
3. **all-clear в реальних умовах** — перевірити що cooldown не флудить при відбої
4. **register_family_handlers подвоєний лог** — дослідити (`uav_watcher.py`)
5. **goclaw_* legacy** — `uav_watcher.py` читає `cfg["goclaw_url"]` напряму. Fix: `cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")`

### 🟢 Minor
6. **Канал Aeris Rimor** — додати через web UI
7. **Sharon tests #63, #65** — semantic edge cases
8. **Untracked knowledge files** — `consultant/knowledge/*.txt`, `психо.html`

---

## Корисні команди

```bash
# Sharon health
curl http://192.168.3.184:8770/health

# Sharon chat test
curl -X POST http://192.168.3.184:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Як обстановка?", "session_id": "test"}'

# Recent channel feed
curl http://192.168.3.184:8770/feed/recent?limit=5

# Логи watcher
sshpass -p '805235io.' ssh vokov@192.168.3.184 'tail -f /var/log/uav-watcher.log'

# Тест AI-класифікації
sshpass -p '805235io.' ssh vokov@192.168.3.184 'cd /home/vokov/projects/uav-watcher && python3 -c "
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
print(asyncio.run(ai_classify(\"Повітряна тривога у місті\", cfg)))
"'

# Тест shelter search
sshpass -p '805235io.' ssh vokov@192.168.3.184 'cd /home/vokov/projects/uav-watcher && python3 -c "
import asyncio
from shelter_search import find_shelters_sync, format_shelters_for_chat
shelters = find_shelters_sync(48.6681, 33.117, radius_m=3000, top_n=3)
print(format_shelters_for_chat(shelters))
"'
```
