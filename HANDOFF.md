# Sharon — Handoff для нового Claude

> Цей документ дає повний контекст для продовження розробки Sharon без попередньої розмови.

---

## Що це за проект

**Sharon** — гіперлокальна AI-система моніторингу повітряних загроз для міст України.

**Проблема яку вирішує:** загальноукраїнська тривога охоплює половину країни → alert fatigue → люди ігнорують попередження. Sharon стежить за 5+ Telegram-каналами, класифікує загрози AI і надсилає **прицільне** сповіщення лише коли загроза наближається до конкретного міста.

**Публічний репозиторій:** `https://github.com/maxfraieho/uav-watcher`
**Гілка:** `master`

---

## Інфраструктура

| Ресурс | Значення |
|--------|---------|
| Dev server | `192.168.3.184` (Alpine Linux) |
| SSH | `sshpass -p '805235io.' ssh -o StrictHostKeyChecking=no vokov@192.168.3.184` |
| Проект | `/home/vokov/projects/uav-watcher/` |
| Сервіс watcher | `sudo rc-service uav-watcher restart` |
| Сервіс consultant | `sudo rc-service uav-consultant restart` |
| Логи watcher | `tail -f /var/log/uav-watcher.log` |
| Логи consultant | `tail -f /var/log/uav-consultant.log` |
| Sharon API | `curl http://192.168.3.184:8770/health` |
| Web UI | `http://192.168.3.184:8422` |

**УВАГА:** `config.json` НЕ в git (в `.gitignore`). Містить справжній bot_token, NIM API key. Ніколи не комітити.

---

## Архітектура (коротко)

```
Telegram-канали (5+)
    ↓ Telethon userbot (uav_watcher.py)
    ├─► keyword_classify() — без AI, миттєво
    ├─► ai_classify()      — Llama 4 Maverick via NVIDIA NIM
    ├─► send_notification() — dedup 90s + escalation bypass
    └─► channel_feed.db    — SQLite ring buffer (500 msg, 2h)
              ↓
    situation_monitor (daemon, consultant/memory/situation_monitor.py)
         → LLM оцінює рівень 0-3 → прогресивний Telegram alert

Sharon consultant (FastAPI :8770)
    retrieve_kb() → channel_feed + summarizer + alerts.in.ua + BM25Plus
    generate() → Llama 4 Maverick → відповідь
```

---

## Ключові файли

| Файл | Призначення |
|------|-------------|
| `uav_watcher.py` | Головний процес: Telethon + AI + Bot + monitor |
| `consultant/main.py` | FastAPI app: Sharon endpoints |
| `consultant/pipeline/nodes.py` | retrieve_kb(), generate(), system prompts |
| `consultant/pipeline/graph.py` | LangGraph: retrieve → web_search → generate |
| `consultant/memory/channel_feed.py` | SQLite ring buffer для повідомлень каналів |
| `consultant/memory/summarizer.py` | Background AI summary кожні 5 хв |
| `consultant/memory/situation_monitor.py` | 4-рівневий проактивний монітор |
| `consultant/knowledge_base/retrieval.py` | BM25Plus singleton |
| `consultant/knowledge/*.md` | База знань (auto-reindex через watchdog) |
| `web_config.py` | Веб UI налаштувань (:8422) |
| `config.json` | **НЕ в git** — всі секрети та налаштування |
| `config.example.json` | Публічний шаблон (без секретів) |
| `docs/README.md` | Головна публічна документація |
| `docs/plans/2026-05-18-sharon-roadmap.md` | **План розвитку** |

---

## Стан безпеки (вже зроблено)

- `config.json` видалено з git history (git-filter-repo)
- `exodus.pp.ua` замінено на `YOUR_PROXY_URL` в усіх tracked файлах
- `.gitignore` покриває: `*.db`, `*.db-shm`, `*.db-wal`, `*.log`, `*.session`, `config.json`, `*.key`, `.env*`
- 42 публічні репо maxfraieho → приватні (крім uav-watcher)
- Email в комітах → `noreply@github.com`

---

## Поточні проблеми (PENDING)

### 🔴 Критичне
1. **Новий bot token потрібен** — старий відкликано через BotFather (був в публічному git). Без нього `send_notification()` не працює. Отримати: Telegram → @BotFather → /mybots → обрати бота → Regenerate token → оновити `config.json` на сервері.

### 🟡 Важливо
2. **goclaw_* legacy** — `uav_watcher.py:143-149` читає `cfg["goclaw_url"]`, `cfg["goclaw_api_key"]`, `cfg["goclaw_model"]` напряму. `web_config.py:3034` синхронізує їх з `llm_proxy_*` при збереженні через UI. Але якщо хтось встановлює з нуля через `config.example.json` (де тільки `llm_proxy_*`), AI-класифікація в `uav_watcher.py` не знайде ключів. **Fix:** замінити на `cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")`.

3. **Proxy URL** — власник планує перенести проксі на власний сервер. Поточний NIM URL (`integrate.api.nvidia.com`) прямий. `goclaw_url` в `config.json` вказує на старий `exodus.pp.ua` (не в git але на сервері).

### 🟢 Minor
4. **Sharon tests #63, #65** — семантичні edge cases: офтопік → пише код замість перенаправлення. Правити в `CASUAL_SYSTEM_PROMPT` в `nodes.py`.
5. **Untracked knowledge files** — `consultant/knowledge/*.txt`, `психо.html` ще не в git. Перевірити вміст → якщо без ідентифікуючих даних → додати.

---

## LLM конфігурація

- **Provider:** NVIDIA NIM
- **URL:** `https://integrate.api.nvidia.com/v1`
- **Model:** `meta/llama-4-maverick-17b-128e-instruct`
- **Key:** в `config.json` → `llm_proxy_token` (nvapi-...)
- **Безкоштовний tier:** 1000 req/day

---

## Деdup логіка (свіжа)

```python
# uav_watcher.py
_last_notify_time: float = 0.0
_last_notify_level: int = 0
_NOTIFY_COOLDOWN_SEC = 90

def _infer_level(text, reason) -> int:
    # L3: вибух/прямо над/над містом/над нами
    # L2: у місті/по місту/в напрямку міста
    # L1: все інше

# В send_notification():
# - Якщо level > _last_notify_level → bypass cooldown (ескалація)
# - Якщо level <= _last_notify_level і elapsed < 90s → suppress
```

---

## Як продовжувати розробку

1. Прочитати `docs/plans/2026-05-18-sharon-roadmap.md` — повний план з Task 1–12
2. Почати з **Task 1** (новий bot token) — без нього нічого не тестується
3. Перевірити сервіси: `curl http://192.168.3.184:8770/health`
4. Перед кожним кодовим кроком: `git status` → комітити лише конкретні файли, **не `git add .`**
5. Після змін в коді: рестарт через `sudo rc-service <name> restart`

---

## Корисні команди

```bash
# Перевірити Sharon
curl -X POST http://192.168.3.184:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Як обстановка?", "session_id": "test123"}'

# Переглянути останні сповіщення
curl http://192.168.3.184:8770/feed/recent?limit=5

# Логи в реальному часі
sshpass -p '805235io.' ssh vokov@192.168.3.184 'tail -f /var/log/uav-watcher.log'

# Тест AI-класифікації
sshpass -p '805235io.' ssh vokov@192.168.3.184 'cd /home/vokov/projects/uav-watcher && python3 -c "
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
print(asyncio.run(ai_classify(\"Повітряна тривога у місті\", cfg)))
"'
```
