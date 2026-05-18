# Sharon v2.0 — Session State
# Дата: 2026-05-17

## Статус виконання плану

### Phase 0 — COMPLETE ✅

| Task | Файли | Комміт | Статус |
|------|-------|--------|--------|
| 0.1 Crisis Templates | `bot/__init__.py`, `bot/crisis_templates.py`, `uav_watcher.py` | `8071136` | ✅ DONE |
| 0.2 /status command | `uav_watcher.py` | `bc3db39` | ✅ DONE |
| 0.3 alerts.in.ua API | `integrations/__init__.py`, `integrations/alerts_ua.py`, `uav_watcher.py` | `5d52bab` | ✅ DONE |

### Phase 1 — PENDING

| Task | Файли | Комміт | Статус |
|------|-------|--------|--------|
| 1.1 SQLite Family DB | `db/__init__.py`, `db/models.py` | — | ⏳ |
| 1.2 Family Bot Commands | `family/__init__.py`, `family/bot_handlers.py`, `uav_watcher.py` | — | ⏳ |

### Phase 2 — PENDING

| Task | Файли | Комміт | Статус |
|------|-------|--------|--------|
| 2.1 Dead Man's Switch | `rescue/__init__.py`, `rescue/location_tracker.py` | — | ⏳ |

### Phase 3 — PENDING

| Task | Файли | Статус |
|------|-------|--------|
| 3.1 Meshtastic scaffold | `integrations/meshtastic_bridge.py` | ⏳ |
| 3.2 PWA scaffold | `web/pwa/index.html` | ⏳ |

---

## Нові бот-команди після Phase 0

| Команда | Дія |
|---------|-----|
| `/help`, `/що_робити`, `/допомога` | Меню типів загроз (inline-кнопки) |
| `/заземлення`, `/calm`, `/паніка` | 5-крокова техніка при паніці (8с між кроками) |
| `/status`, `/статус`, `/безпечно` | Надіслати "Я в безпеці" в notify_chat_id |
| crisis inline callbacks | Деталі по кожному типу загрози |

## Що потрібно після рестарту бота

1. Рестарт: `pkill -f uav_watcher.py && cd ~/projects/Sharon && nohup python3 uav_watcher.py &`
2. Якщо є токен alerts.in.ua — додати в `config.json`: `"alerts_ua_token": "ВАШ_ТОКЕН"`

---

## Структура файлів після Phase 0

```
Sharon/
├── bot/
│   ├── __init__.py          ← NEW
│   └── crisis_templates.py  ← NEW: 7 типів загроз + grounding
├── integrations/
│   ├── __init__.py          ← NEW
│   └── alerts_ua.py         ← NEW: AlertsUAPoller
├── uav_watcher.py           ← MODIFIED: bot_app + handlers
├── docs/plans/
│   ├── v2-plan-index.md     ← план
│   └── v2-session-state.md  ← ЦЕЙ ФАЙЛ
└── discawe/
    └── CLAUDE.md            ← повний план v2.0
```

---

## Наступний крок при відновленні сесії

**Починати з Task 1.1** — SQLite Family Groups DB
- Файл плану: `discawe/CLAUDE.md` розділ `TASK 1.1`
- Створити: `db/__init__.py`, `db/models.py`
- Тест: `python3 -c "from db.models import init_db, create_family; ..."`
