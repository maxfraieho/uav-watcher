# UAV Watcher — Session State 2026-05-17 (Session 3)

## Що зроблено в цій сесії

### ✅ Batch 3 committed (був uncommitted з S2)
- Admin Basic Auth: `_require_admin_auth()` + `/save-password` UI card
- ThreadingHTTPServer + ReusableServer (concurrent LLM requests)
- Overpass query: metro stations + underground parking
- `/api/chat` returns `reply`+`text` fields
- Rate limiter в rollcall broadcast (20 msg/sec)
- SyntaxWarning fix: `/\*...\*/` → `/[*]...[*]/`

### ✅ P2: threading.Lock для save_config()
- Серіалізує запити до config.json при concurrent ThreadingHTTPServer

### ✅ Розширення бази знань (22 → 76 секцій)
- `03-trauma.md` — вибухова травма, джгут, MARCH, crush syndrome
- `04-first-aid.md` — CPR, задуха, переломи, анафілаксія, CO
- `05-psychological.md` — PFA WHO, панічна атака, заморозка, діти
- `06-search-rescue.md` — пошук під завалами, голосовий контакт, ДСНС
- `07-shelters.md` — типи укриттів, e-shelter.gov.ua, оцінка якості
- Watchdog автоматично реіндексував (без рестарту)

### ✅ Офлайн-режим консультанта
- `_format_offline()` в nodes.py — повертає секції KB напряму при відсутності LLM
- `try/except` навколо `_llm_call()` в `generate()`
- Бот відповідає без інтернету (тільки BM25, без LLM генерації)
- Hint в admin UI: Ollama для локальної офлайн-моделі
  - URL: `http://localhost:11434/v1`, Token: `ollama`, Model: `qwen2:1.5b`

## Commits

```
4ff0170 docs: add Ollama local model hint in AI Proxy admin card
c2baf67 feat: offline fallback in consultant
ae4454e feat: expand KB — 5 new files (76 sections)
af2b6c7 fix: thread-safe save_config with threading.Lock
4452303 feat: admin auth + ThreadingHTTPServer + shelter search expanded
```

## Поточний стан (2026-05-17, Session 3)

| Компонент | Стан |
|-----------|------|
| consultant :8770 | ✅ живий, 76 KB секцій |
| web_config :8422 | ✅ живий, ThreadingHTTPServer |
| /api/chat | ✅ → consultant + offline fallback |
| KB ролі | ✅ кризис/медик/психолог/гід/пошук&рятування |
| Офлайн-режим | ✅ BM25 без LLM |
| Admin Auth | ✅ (password не встановлено = відкритий доступ) |

## Наступні фічі (обговорені з Q)

| Пріоритет | Задача |
|-----------|--------|
| P1 | Watchdog таймер — переглядає чати, накопичує ситуаційне знання |
| P1 | Web search tool для консультанта — DuckDuckGo instant API |
| P2 | Ollama setup guide для Termux/Android |
| P3 | PWA service worker + offline cache |

## Archітектура (оновлена)

```
consultant (:8770) — LangGraph + BM25Plus
  ├── 76 секцій KB: crisis + trauma + first-aid + psych + SAR + shelters
  ├── Ollama local: http://localhost:11434/v1 (офлайн)
  └── Offline fallback: raw KB sections when LLM unavailable

web_config.py (:8422)
  ├── ThreadingHTTPServer — concurrent requests
  ├── Admin Basic Auth (configure via /save-password)
  └── Overpass: shelters + metro + underground parking
```
