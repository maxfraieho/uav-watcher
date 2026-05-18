# Sharon — Handoff для нового Claude
> **Остання сесія:** 2026-05-18 · git `95b4410` · гілка `master`

---

## Що це за проект

**Sharon** — гіперлокальна AI-система моніторингу повітряних загроз для міст України.  
Стежить за 5+ Telegram-каналами, класифікує загрози AI, надсилає прицільні сповіщення.  
Включає AI-консультант Sharon (FastAPI :8770), пошук укриттів і Telegram бот (`@OlBPLA_bot`).

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
| Telegram бот | `@OlBPLA_bot` |

**УВАГА:** `config.json` НЕ в git. Містить: bot_token, NIM API key, координати міста.

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
    situation_monitor (daemon thread)
         → LLM оцінює рівень 0-3 → прогресивний Telegram alert

Telegram Bot (@OlBPLA_bot)
    /start          → persistent reply keyboard (4 кнопки)
    /shelter        → запит геолокації
    📍 Укриття поруч → GPS prompt → find_shelters_enhanced()
    📋 Типи загроз  → inline crisis keyboard
    🧘 Заземлення   → покрокова техніка
    Текст           → _normalize_query() → Sharon :8770/chat

Sharon consultant (FastAPI :8770)
    retrieve_kb()  → normalize → 2h events inject → channel_feed → BM25
    generate()     → Llama 4 Maverick → відповідь
```

---

## Ключові файли

| Файл | Призначення |
|------|-------------|
| `uav_watcher.py` | Головний процес: Telethon + AI + Bot + monitor |
| `shelter_search.py` | Пошук укриттів: ebot → Overpass → seed |
| `rescue/location_tracker.py` | GPS check-in + авто-пошук укриттів |
| `consultant/main.py` | FastAPI Sharon: /chat, /health, /feed |
| `consultant/pipeline/nodes.py` | retrieve_kb(), generate(), _normalize_query() |
| `consultant/pipeline/graph.py` | LangGraph: retrieve → web_search → generate |
| `db/models.py` | save_threat_event(detected_at=) |
| `data/families.db` | SQLite: threat_events, location_checkins |
| `bot/crisis_templates.py` | TEMPLATES, THREAT_KEYBOARD, GROUNDING_STEPS |
| `web_config.py` | Веб UI налаштувань (:8422) |
| `config.json` | **НЕ в git** — секрети |
| `docs/plans/2026-05-18-sharon-roadmap.md` | Plan розвитку Task 1–12 |

---

## Що зроблено в цій сесії (коміти)

| SHA | Що |
|-----|----|
| `95b4410` | Persistent reply keyboard для /start (4 кнопки) |
| `aff2c9a` | Global query normalization — _normalize_query() |
| `928cfb6` | Fuzzy shelter detection — difflib SequenceMatcher |
| `c6ea586` | Loose shelter stems + short-query threshold |
| `625b768` | Startup catchup 4h + хронологічний порядок + реальні timestamps |
| `82ba009` | Always-inject 2h threat context в кожен запит |
| `3914a3e` | Fix: читає ОСТАННІ події, не найстаріші |
| `d60d682` | Web shelter redirect → Telegram бот |

---

## Поточний стан бота

### ✅ Працює
- Постійна клавіатура після /start (кнопки внизу чату)
- Shelter пошук через геолокацію (GPS share → авто результат)
- Web-сесії (UUID) → редірект на @OlBPLA_bot для GPS
- Sharon відповідає актуальний стан (inject 2h events в кожен запит)
- Typo tolerance: "трйвога" → "тривога", "унриття" → "укриття" тощо
- При старті — catchup 4h history каналів

### 🔴 Критично
- **Перевірити /start** — написати боту, переконатись що клавіатура з'явилась

### 🟡 Важливо
- Task 5 (roadmap): `goclaw_*` → `llm_proxy_*` міграція в `uav_watcher.py:140-160`
- Frontend redesign: план готовий (`docs/plans/2026-05-18-sharon-frontend-redesign.md`), код не розпочато

---

## Shelter Search — як працює

```
share location → location_tracker.py → find_shelters_enhanced(user_client, lat, lon)
    1. @UkraineShelterStfalconBot — userbot надсилає GPS, збирає geo-пари
    2. Fallback: Overpass API (OSM shelter nodes)
    3. Fallback: data/shelters_seed_oleksandria.json
    Cache: 24h у data/shelters_cache.json

/shelter text → _SHELTER_KEYWORDS перехоплює → _SHELTER_GEO_MSG (просить GPS)
Web query → _is_shelter_query() → redirect до @OlBPLA_bot
```

---

## _normalize_query — як працює

```python
# consultant/pipeline/nodes.py
_QUERY_VOCAB = ("укриття", "тривога", "загроза", "ситуація", "зараз", ...)

def _normalize_query(text):
    # Для кожного слова >= 5 символів:
    # difflib.get_close_matches(word, VOCAB, cutoff=0.75)
    # Tie-break: мінімальна різниця в довжині (зарза→зараз не загроза)
    # Викликається першим у retrieve_kb()
```

---

## Pending — Відкриті задачі

### 🔴 Критичне
1. Перевірити /start в Telegram — чи з'явилась постійна клавіатура

### 🟡 Важливо
2. **Task 5 (roadmap):** `uav_watcher.py:140-160` — замінити `cfg["goclaw_url"]` на `cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")`
3. **Frontend redesign** — почати Task 1: `npx sv create sharon-web` (SvelteKit), план в `2026-05-18-sharon-frontend-redesign.md`
4. Sharon tests #63, #65 — semantic edge cases в `CASUAL_SYSTEM_PROMPT`

### 🟢 Minor
5. `requirements.txt` — оновити (Task 2)
6. `LICENSE` — MIT (Task 3)
7. Aeris Rimor channel — web UI
8. `docs/integrated/`, `*.txt`, `психо.html` — перевірити, додати в git або gitignore

---

## LLM конфігурація

- **Provider:** NVIDIA NIM
- **URL:** `https://integrate.api.nvidia.com/v1`
- **Model:** `meta/llama-4-maverick-17b-128e-instruct`
- **Key:** `config.json → llm_proxy_token`
- **Tier:** 1000 req/day (безкоштовний)

---

## Корисні команди

```bash
# Sharon health
curl http://192.168.3.184:8770/health

# Тест Sharon з typo
curl -X POST http://192.168.3.184:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "яка трйвога зараз?", "session_id": "test"}'

# Recent events
curl http://192.168.3.184:8770/feed/recent?limit=5

# Логи в реальному часі
sshpass -p '805235io.' ssh vokov@192.168.3.184 'tail -f /var/log/uav-watcher.log'

# Тест shelter
sshpass -p '805235io.' ssh vokov@192.168.3.184 'cd /home/vokov/projects/uav-watcher && python3 -c "
from shelter_search import find_shelters_sync, format_shelters_for_chat
print(format_shelters_for_chat(find_shelters_sync(48.6681, 33.117, radius_m=3000, top_n=3)))
"'
```

---

## Сайт (Web UI) — наступний крок

**Поточний стан:** `web_config.py` (Flask :8422) — адмін-панель для налаштувань.  
**Нема:** публічного чат-інтерфейсу Sharon для браузера.

**План:** `docs/plans/2026-05-18-sharon-frontend-redesign.md` (9 tasks, SvelteKit)
- Task 1: `npx sv create sharon-web` в `/home/vokov/projects/uav-watcher/web/`
- Стек: SvelteKit + Tailwind + SSE для live threat updates
- Design: Stitch prompt готовий в `docs/plans/2026-05-18-sharon-frontend-stitch-prompt.md`
- API: Sharon :8770/chat (chat), :8770/feed/recent (live feed), :8770/health

**При старті frontend задачі:**
1. Прочитати `docs/plans/2026-05-18-sharon-frontend-redesign.md`
2. Прочитати `docs/plans/2026-05-18-sharon-frontend-stitch-prompt.md` (DESIGN.md + Stitch prompt)
3. Почати з Task 1 (scaffold)
