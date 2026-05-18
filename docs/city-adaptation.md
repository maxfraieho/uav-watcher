# Адаптація під будь-яке місто

---


> ⚠️ **Дисклеймер:** Цей інструмент є **доповненням** до офіційної системи оповіщення ДСНС, а не її заміною. При сигналі тривоги — негайно прямуйте до найближчого укриття. Дані надходять з публічних Telegram-каналів та AI-аналізу і можуть містити неточності. Рішення про дії завжди залишається за вами.

> AI-компонент може помилятись — як і будь-яка мовна модель (ChatGPT, Gemini, Claude). Розробники не несуть відповідальності за рішення, прийняті на основі порад системи.

## Концепція геолокаційного підходу

Замість пошуку ключових слів ("ВашеМісто", "ВашеМісто") система може використовувати
**координати міста** і перевіряти відстань від кожної згаданої локації до центру міста.

Це більш надійно: нові назви населених пунктів, помилки в написанні, або просто
"над регіоною" без назви конкретного міста — геокодер розуміє.

---

## Архітектура геолокаційного класифікатора

```
Текст повідомлення
    ↓
extract_locations()     — NLP або regex витягує назви місць
    ↓
geocode_locations()     — Nominatim/Overpass → coordinates
    ↓
calculate_distances()   — haversine від центру міста
    ↓
proximity_score()       — 0.0 (далеко) → 1.0 (над містом)
    ↓
threat_assessment()     — LLM + proximity_score → final decision
```

### Зони реакції

```
     [МІСТО CENTER (lat, lon)]
          ↕ radius_km
    ─────────────────────────
    0–15 km    РІВЕНЬ 3 — Небезпека
   15–30 km    РІВЕНЬ 2 — Тривога  
   30–80 km    РІВЕНЬ 1 — Спостереження
   > 80 km     РІВЕНЬ 0 — Тиша
```

---

## config.json для вашого міста

```json
{
  "city": "Ваше Місто",
  "city_keywords": ["Ваше Місто", "ВашеМісто", "YourCity"],
  "city_lat": LAT,
  "city_lon": LON,
  "city_radius_km": 30,
  "region": "Область",
  "region_keywords": ["Область", "обл."],
  "channels": [
    -1001234567890,
    -1009876543210
  ],
  "bot_token": "YOUR_BOT_TOKEN",
  "notify_chat_id": "YOUR_CHAT_OR_GROUP_ID",
  "llm_proxy_url": "https://integrate.api.nvidia.com/v1",
  "llm_proxy_token": "nvapi-YOUR_KEY",
  "llm_proxy_model": "meta/llama-4-maverick-17b-128e-instruct"
}
```

### Де взяти координати

```python
# Використати Nominatim (OpenStreetMap)
import requests
r = requests.get("https://nominatim.openstreetmap.org/search",
    params={"q": "Ваше Місто, Україна", "format": "json", "limit": 1},
    headers={"User-Agent": "uav-watcher/1.0"})
data = r.json()[0]
print(f"lat={data['lat']}, lon={data['lon']}")
```

---

## Рекомендовані канали для моніторингу

### Загальноукраїнські (додати до всіх міст)
- `@Ukraine_alerts` — Повітряна Тривога
- `@kpszsu` — Командування Повітряних Сил ЗСУ
- `@suspilne_news` — Суспільне Мовлення

### Регіональні (знайти для свого регіону)
- `@[oblast]_alert` — регіональні канали тривог
- `@suspilne_[city]` — місцеве Суспільне
- Канали місцевих ОВА

### Як знайти

1. Пошук у Telegram: "тривога [ваша область]"
2. `tgstat.com.ua` — каталог українських каналів
3. Перевірте популярні канали в місцевих групах

---

## Крок за кроком: нове місто за 30 хвилин

### 1. Підготовка (5 хв)
```bash
git clone https://github.com/YOUR_ORG/uav-watcher
cd uav-watcher
pip install -r requirements.txt
```

### 2. Конфіг (10 хв)
```bash
cp config.example.json config.json
# Заповніть: city, lat/lon, channels, bot_token, notify_chat_id
```

### 3. Telegram (10 хв)
```bash
# Отримайте bot token через @BotFather
# Отримайте channel ID через @userinfobot або @getidsbot
export TELEGRAM_PHONE="+380XXXXXXXXX"
python3 -c "from telethon.sync import TelegramClient; ..."  # перша авторизація
```

### 4. База знань (5 хв)
```bash
# Відредагуйте consultant/knowledge/ — замініть "ВашеМісто" на ваше місто
# Файли автоматично реіндексуються при зміні
```

### 5. Запуск
```bash
python uav_watcher.py &
cd consultant && python main.py &
# або через systemd/OpenRC
```

### 6. Тест
```bash
curl -X POST http://localhost:8770/chat \
  -d '{"message": "Як обстановка?", "session_id": "test"}' \
  -H "Content-Type: application/json"
```

---

## Що персоналізувати

| Файл | Що змінити |
|------|-----------|
| `config.json` | city, lat/lon, radius, channels |
| `consultant/knowledge/shelter.md` | Укриття вашого міста |
| `consultant/knowledge/local.md` | Локальні особливості |
| `consultant/pipeline/nodes.py` | `CASUAL_SYSTEM_PROMPT` — назва міста |
| `consultant/pipeline/nodes.py` | `SYSTEM_PROMPT` — назва міста |

---

## Майбутнє: автоматична геолокація загроз

Плановий функціонал — замість ключових слів повна геолокація:

```python
# extract_locations_from_text() — НЛП або LLM витягує топоніми
# geocode_all() — масовий геокодинг через Nominatim
# filter_by_radius(city_lat, city_lon, radius_km) — відстань
# → proximity_score для кожного повідомлення
```

Це дозволить ловити загрози навіть якщо місто не згадується явно —
достатньо щоб повідомлення містило сусідній населений пункт в радіусі 30 км.
