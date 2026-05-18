# Sharon — AI-моніторинг повітряних загроз

> **Sharon** — гіперлокальна система раннього попередження про повітряні загрози для міст України.
> Слідкує за Telegram-каналами, класифікує загрози через AI, надсилає прицільні сповіщення конкретному місту.

> ⚠️ **Відмова від відповідальності:** Sharon є **доповненням** до офіційного оповіщення ДСНС, не його заміною.
> AI помиляється. Довіряй лише офіційним сиренам і [@air_alert_ua](https://t.me/air_alert_ua).
> **При офіційній тривозі — прямуйте до укриття негайно.**

---

## Що робить Sharon

- **Моніторинг 8+ каналів** в реальному часі через Telethon userbot
- **Дворівнева класифікація:** спочатку ключові слова (швидко), потім Llama 4 Maverick (точно)
- **Прицільні сповіщення:** тільки загрози для вашого міста, не весь регіон
- **Рівні тривоги (1–3):** БПЛА в регіоні → у місті → вибух поруч
- **Dedup 90 сек:** без спаму при дублюванні з різних каналів
- **Ескалація:** якщо рівень загрози зростає — bypass cooldown
- **ВІДБІЙ** — тільки якщо перед цим була активна загроза (guard від хибних відбоїв)
- **Відновлення після рестарту:** стан тривоги зберігається в `data/threat_state.json`

## Sharon-консультант (AI чат-бот)

Окремий FastAPI-сервіс на `:8770`:
- `/chat` — відповідає на питання про поточну ситуацію, укриття, дії при загрозах
- Використовує `channel_feed` (SQLite ring-buffer 500 повідомлень / 2 год) як контекст
- BM25Plus для пошуку в базі знань (123 секції)
- Ситуаційний монітор: оцінює рівень 0–3, надсилає проактивні Telegram-алерти

## Telegram Bot

Команди та кнопки:
| Команда / кнопка | Дія |
|-----------------|-----|
| `/start` | Головне меню з клавіатурою |
| `⚠️ Загрози зараз` | Live-запит до Sharon + кнопка 📡 Деталізуй |
| `📡 Деталізуй з каналів` | Цитати з каналів за останні 2 год |
| `/shelter <адреса>` | Пошук укриттів (@UkraineShelterStfalcon → OSM → seed) |
| Геолокація | Автоматичний пошук укриттів поруч |
| `/family_create <назва>` | Створити сімейну групу |
| `/family_join <код>` | Приєднатись до групи |
| `/family_status` | Статус членів родини |
| `/ok` | Повідомити що в безпеці |
| `/sos` | Сигнал про допомогу |
| 🧘 Заземлення | Техніка при паніці (покроково) |

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
    situation_monitor (daemon thread)
         → LLM оцінює рівень 0-3 → Telegram alert

Sharon consultant (FastAPI :8770)
    retrieve_kb() → channel_feed + BM25Plus + alerts.in.ua
    generate()    → Llama 4 Maverick → відповідь
    LangGraph: retrieve → web_search → generate

Telegram Bot (uav_watcher.py — bot_app)
    /shelter → shelter_search.py → OSM/ebot/seed
    Геолокація → rescue/location_tracker.py → auto shelter
    Текст → http://localhost:8770/chat (Sharon)
    /family_* → family/bot_handlers.py
```

## Перше налаштування

### 1. Telegram API credentials

1. Зайти на [my.telegram.org](https://my.telegram.org) → API development tools
2. Записати **App api_id** і **App api_hash**

### 2. Telegram Bot Token

Написати [@BotFather](https://t.me/BotFather) → `/newbot` → зберегти токен

### 3. Заповнити `.env`

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+380XXXXXXXXX
```

### 4. Авторизувати Telethon (одноразово)

```bash
python auth.py
```

### 5. Налаштувати `config.json`

```json
{
  "city": "Ваше місто",
  "city_region": "Ваша область",
  "city_keywords": ["Назва міста", "Скорочення"],
  "channels": [-1001234567890],
  "bot_token": "1234567890:ABC...",
  "notify_chat_id": 123456789,
  "llm_proxy_url": "https://integrate.api.nvidia.com/v1",
  "llm_proxy_token": "nvapi-YOUR_KEY",
  "llm_proxy_model": "meta/llama-4-maverick-17b-128e-instruct"
}
```

**Де знайти ID каналу:** переслати повідомлення з нього до [@userinfobot](https://t.me/userinfobot)

### 6. Запустити

```bash
# Як сервіс (OpenRC / Alpine Linux)
sudo rc-service uav-watcher start
sudo rc-service uav-consultant start

# Вручну
python3 uav_watcher.py
python3 consultant/main.py
```

## Веб-інтерфейс налаштувань

```bash
sudo rc-service uav-web-config start
# → http://192.168.3.184:8422
```

Дозволяє без редагування файлів:
- Змінити місто, ключові слова, канали
- Налаштувати API credentials
- Перезапустити сервіс

## Сервіси (OpenRC)

| Сервіс | Порт | Опис |
|--------|------|------|
| `uav-watcher` | — | Telethon userbot + Telegram bot |
| `uav-consultant` | 8770 | Sharon FastAPI AI-консультант |
| `uav-web-config` | 8422 | Веб UI налаштувань |

```bash
sudo rc-service uav-watcher {start|stop|restart|status}
tail -f /var/log/uav-watcher.log
tail -f /var/log/uav-consultant.log
```

## Пошук каналів для моніторингу

Шукати в Telegram:
- `повітряна тривога` + назва вашої області
- `БПЛА` + ваш регіон
- `сирена` + область

Або використати userbot:
```python
from telethon.tl.functions.contacts import SearchRequest
results = await client(SearchRequest(q="тривога Ваше місто", limit=10))
```

## Залежності

```bash
pip install telethon httpx python-dotenv fastapi uvicorn langgraph
```

## Налагодження

```bash
# Перевірити статус
curl http://localhost:8770/health

# Тест Sharon
curl -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Яка обстановка?", "session_id": "test"}'

# Тест AI-класифікації
python3 -c "
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
print(asyncio.run(ai_classify(Повітряна тривога у місті, cfg)))
"

# Переглянути останні загрози з БД
python3 -c "
import sqlite3
conn = sqlite3.connect(data/families.db)
c = conn.cursor()
c.execute(SELECT detected_at, threat_type, is_allclear, channel_name FROM threat_events ORDER BY id DESC LIMIT 10)
for r in c.fetchall(): print(r)
"
```

## Безпека

- `config.json` — **ніколи не комітити** (містить токени)
- `.gitignore` включає: `*.db`, `*.session`, `config.json`, `*.log`
- Веб-інтерфейс — тільки локальна мережа

---

> Детальна документація для розробника: [HANDOFF.md](HANDOFF.md)
> Репозиторій: [github.com/maxfraieho/uav-watcher](https://github.com/maxfraieho/uav-watcher)
