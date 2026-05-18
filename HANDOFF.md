# Sharon — Handoff для нового Claude

> **Останнє оновлення:** 2026-05-18, git `70344cb`

---

## Що це за проект

**Sharon** — гіперлокальна AI-система моніторингу повітряних загроз для міст України.
Слідкує за 8+ Telegram-каналами, класифікує загрози AI, надсилає прицільні сповіщення.
Включає AI-консультант Sharon (FastAPI :8770) і пошук укриттів.

**Репозиторій:** `https://github.com/maxfraieho/uav-watcher` · гілка `master`

---

## Інфраструктура

| Ресурс | Значення |
|--------|---------|
| Dev server | `192.168.3.184` (Alpine Linux) |
| SSH | `sshpass -p 805235io. ssh -o StrictHostKeyChecking=no vokov@192.168.3.184` |
| Проект | `/home/vokov/projects/uav-watcher/` |
| Сервіс watcher | `sudo rc-service uav-watcher restart` |
| Сервіс consultant | `sudo rc-service uav-consultant restart` |
| Сервіс web-config | `sudo rc-service uav-web-config restart` |
| Логи watcher | `tail -f /var/log/uav-watcher.log` |
| Логи consultant | `tail -f /var/log/uav-consultant.log` |
| Sharon API | `curl http://192.168.3.184:8770/health` |
| Web UI | `http://192.168.3.184:8422` |

**УВАГА:** `config.json` НЕ в git. Ніколи не комітити.

---

## Архітектура

```
Telegram-канали (8+)
    ↓ Telethon userbot (uav_watcher.py)
    ├─► keyword_classify()   — без AI, миттєво
    ├─► ai_classify()        — Llama 4 Maverick via NVIDIA NIM
    ├─► _active_threat guard — відбій тільки після реальної тривоги
    ├─► data/threat_state.json — зберігає стан між рестартами
    └─► dedup 90s + level escalation bypass
              ↓
    situation_monitor (daemon thread, consultant/memory/situation_monitor.py)
         → LLM оцінює рівень 0-3 → прогресивний Telegram alert

Telegram Bot (uav_watcher.py — bot_app)
    ⚠️ Загрози зараз   → Sharon /chat (live) + кнопка 📡 Деталізуй
    📡 Деталізуй       → Sharon /chat з запитом цитат каналів
    /shelter <адреса>   → shelter_search.py → OSM/ebot/seed
    Геолокація          → rescue/location_tracker.py → auto shelter
    Текст               → http://localhost:8770/chat (Sharon)
    /family_*           → family/bot_handlers.py

Sharon consultant (FastAPI :8770)
    retrieve_kb() → channel_feed + BM25Plus + alerts.in.ua
    generate()    → Llama 4 Maverick → відповідь
```

---

## Ключові файли

| Файл | Призначення |
|------|-------------|
| `uav_watcher.py` | Головний процес: Telethon + AI + Bot + monitor |
| `data/threat_state.json` | Персистентний стан _active_threat (пережиє рестарт) |
| `shelter_search.py` | Пошук укриттів: ebot → Overpass OSM → seed |
| `rescue/location_tracker.py` | GPS check-in + авто-пошук укриттів |
| `geo_monitor.py` | Геолокаційний моніторинг |
| `consultant/main.py` | FastAPI Sharon: /chat, /health, /situation |
| `consultant/pipeline/nodes.py` | retrieve_kb(), generate(), system prompts |
| `consultant/memory/channel_feed.py` | SQLite ring buffer |
| `consultant/memory/situation_monitor.py` | 4-рівневий проактивний монітор |
| `consultant/knowledge_base/retrieval.py` | BM25Plus singleton |
| `consultant/knowledge/*.md` | База знань (авто-реіндекс) |
| `family/bot_handlers.py` | /family_create, /family_join, /family_status |
| `web_config.py` | Веб UI налаштувань (:8422) |
| `config.json` | **НЕ в git** — секрети, координати |
| `docs/plans/2026-05-18-sharon-roadmap.md` | Roadmap Task 1–12 |

---

## LLM конфігурація

- **Provider:** NVIDIA NIM
- **URL:** `https://integrate.api.nvidia.com/v1`
- **Model:** `meta/llama-4-maverick-17b-128e-instruct`
- **Key:** `config.json → llm_proxy_token`
- **Безкоштовний tier:** 1000 req/day

---

## _active_threat — логіка відбою

Глобальний стан `_active_threat: bool` (uav_watcher.py:25).
Зберігається в `data/threat_state.json` (виживає рестарт, TTL 4 год).

```python
# send_notification() → _active_threat = True + _save_threat_state(True)
# send_allclear_notification() → if not _active_threat: return (skip)
#                              → _active_threat = False + _save_threat_state(False)
# main() startup → _active_threat = _load_threat_state()
```

---

## Shelter Search

```
/shelter <адреса> або share location
    ↓
find_shelters_enhanced(user_client, lat, lon)
    1. @UkraineShelterStfalconBot — userbot надсилає GPS
    2. Fallback: Overpass API (civil_defence=shelter)
    3. Fallback: seed file data/shelters_seed_oleksandria.json
    Cache: 24h у data/shelters_cache.json
```

---

## Канали (поточні — 8 штук)

| ID | Назва | Учасники |
|----|-------|---------|
| -1001223955273 | Повітряні Сили ЗС України | SYSTEM (завжди) |
| -1001766138888 | Повітряна Тривога | ~53k |
| -1001588890885 | СИРЕНА КІРОВОГРАДЩИНА | ~53k |
| -1001547049625 | Суспільне Кропивницький | — |
| -1001158325608 | (регіональний) | — |
| -1001611420751 | Тривога Олександрія | 111 |
| -1001341110175 | Сирени Кіровоградщина | 806 |
| -1001511318448 | Повітряна Тривога Кіровоградська | 156 |

---

## Стан безпеки

- `config.json` видалено з git history ✅
- `.gitignore`: `*.db`, `*.session`, `config.json`, `*.log` ✅
- Web UI перевіряє `rc-service uav-watcher status` (виправлено з "Sharon") ✅

---

## Pending / Відкриті питання

### 🟡 Важливо
1. **alerts.in.ua token** — `situation_watcher` повідомляє "polling disabled". Отримати безкоштовний токен на alerts.in.ua і додати в `config.json`
2. **all-clear в реальних умовах** — перевірити що guard не блокує легітимний відбій після рестарту (state file має вирішити)
3. **register_family_handlers подвоєний лог** — дослідити (`uav_watcher.py`)
4. **goclaw_* legacy** — `cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")` — вже виправлено частково

### 🟢 Minor
5. **Канал Aeris Rimor** — додати через web UI
6. **Sharon tests #63, #65** — semantic edge cases
7. **Untracked knowledge files** — `consultant/knowledge/*.txt`, `психо.html`

---

## Корисні команди

```bash
# Sharon health
curl http://192.168.3.184:8770/health

# Sharon chat test
curl -X POST http://192.168.3.184:8770/chat \
  -H "Content-Type: application/json" \
  -d {message: Яка обстановка?, session_id: test}

# Поточний стан _active_threat
cat /home/vokov/projects/uav-watcher/data/threat_state.json

# Логи watcher
tail -f /var/log/uav-watcher.log

# Тест AI-класифікації
cd /home/vokov/projects/uav-watcher && python3 -c "
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
print(asyncio.run(ai_classify(Повітряна тривога у місті, cfg)))
"

# Тест shelter search
cd /home/vokov/projects/uav-watcher && python3 -c "
import asyncio
from shelter_search import find_shelters_sync, format_shelters_for_chat
shelters = find_shelters_sync(48.6681, 33.117, radius_m=3000, top_n=3)
print(format_shelters_for_chat(shelters))
"
```
