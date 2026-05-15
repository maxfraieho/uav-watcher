# UAV Watcher

Моніторинг БПЛА-загроз для конкретного міста через Telegram. Слідкує за каналами повітряних тривог, класифікує повідомлення через AI, надсилає сповіщення в Telegram.

## Як це працює

```
Telegram-канали (Telethon userbot)
    ↓  фільтр за ключовими словами міста
AI-proxy (goclaw/fast-proxy)
    ↓  JSON: {"threat": true/false, "reason": "..."}
Telegram Bot API → сповіщення в чат
```

1. **Telethon** (MTProto userbot) слідкує за каналами в режимі реального часу
2. Якщо повідомлення містить ключове слово міста — надсилається на AI-класифікацію
3. AI визначає: чи є це загрозою саме для вашого міста (не просто тривога десь)
4. При `"threat": true` — бот надсилає сповіщення з причиною

## Файли

```
uav_watcher.py      — основний процес (Telethon + AI + Bot API)
web_config.py       — веб-інтерфейс налаштувань (порт 8422)
auth.py             — одноразовий скрипт авторизації Telethon
config.json         — налаштування: місто, канали, токени
.env                — секрети: API_ID, API_HASH, PHONE
uav_watcher.session — сесія Telethon (створюється при авторизації)
```

## Перше налаштування

### 1. Отримати Telegram API credentials

1. Зайти на [my.telegram.org](https://my.telegram.org)
2. "API development tools" → створити застосунок
3. Записати **App api_id** і **App api_hash**

### 2. Telegram Bot Token

1. Написати [@BotFather](https://t.me/BotFather) → `/newbot`
2. Зберегти токен вигляду `1234567890:ABC...`

### 3. Отримати свій User ID (для `notify_chat_id`)

Написати будь-якому з ботів:
- [@userinfobot](https://t.me/userinfobot) — напише ваш ID у відповідь
- [@getmyid_bot](https://t.me/getmyid_bot) — аналогічно

Або надіслати будь-яке повідомлення своєму боту, потім перевірити:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Шукати `"chat": {"id": ...}` у відповіді.

### 4. Заповнити `.env`

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+380XXXXXXXXX
```

### 5. Авторизувати Telethon (одноразово)

```bash
python auth.py
```

Введіть код підтвердження з Telegram. Файл `uav_watcher.session` буде створений.

### 6. Налаштувати `config.json`

```json
{
  "city": "Ваше місто",
  "city_region": "Ваша область",
  "city_keywords": ["Назва міста", "Скорочення"],
  "channels": [-1001234567890],
  "bot_token": "1234567890:ABC...",
  "notify_chat_id": 123456789,
  "goclaw_url": "http://localhost:18880/v1/chat/completions",
  "goclaw_api_key": "freecc",
  "goclaw_model": "fast-proxy"
}
```

**channels** — числові ID Telegram-каналів (від'ємні для супергруп/каналів).  
Знайти ID каналу: переслати будь-яке повідомлення з нього боту [@userinfobot](https://t.me/userinfobot).

## Веб-інтерфейс налаштувань

Запустити:
```bash
python web_config.py
```

Відкрити у браузері: `http://192.168.3.184:8422`

Дозволяє налаштувати без редагування файлів вручну:
- Місто та ключові слова
- Список каналів
- Telegram API credentials (API ID, Hash, Phone)
- notify_chat_id та bot_token
- Перезапустити сервіс

> Веб-інтерфейс не захищений паролем — використовуйте тільки в локальній мережі.

## Запуск як сервіс (OpenRC)

Сервіс зареєстрований як `uav-watcher`:

```bash
sudo rc-service uav-watcher start
sudo rc-service uav-watcher stop
sudo rc-service uav-watcher restart
sudo rc-service uav-watcher status
```

Увімкнути автозапуск:
```bash
sudo rc-update add uav-watcher default
```

Логи:
```bash
tail -f /var/log/uav-watcher.log
# або через journalctl якщо перенаправлено
```

## Де знайти канали для моніторингу

### Канали повітряних тривог
Шукати в Telegram за запитами:
- `повітряна тривога` + назва вашої області
- `БПЛА` + ваш регіон
- `антидрон` + область

### Перевірені джерела
- Офіційні канали обласних ВА (військових адміністрацій)
- Місцеві новинні канали (часто дублюють тривоги швидше офіційних)
- Канали типу "Повітряна тривога [Область]"

### Як перевірити ID каналу
1. Додати [@userinfobot](https://t.me/userinfobot) або [@getmyid_bot](https://t.me/getmyid_bot)
2. Переслати будь-яке повідомлення з потрібного каналу боту
3. Бот поверне ID каналу (від'ємне число для каналів)

## Налагодження

**Перевірити чи AI-proxy доступний:**
```bash
curl -s http://localhost:18880/v1/chat/completions \
  -H "Authorization: Bearer freecc" \
  -H "Content-Type: application/json" \
  -d '{"model":"fast-proxy","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' | python3 -m json.tool
```

**Перевірити Bot API:**
```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

**Тест AI-класифікації вручну:**
```bash
python3 -c "
import asyncio, json, httpx, re
from uav_watcher import ai_classify, load_config
cfg = load_config()
result = asyncio.run(ai_classify('Увага! БПЛА в бік Олександрії, Кіровоградська область!', cfg))
print(result)
"
```

## Залежності

```
telethon
httpx
python-dotenv
```

```bash
pip install telethon httpx python-dotenv
```

## Конфігурація за замовчуванням

- Місто: **Олександрія** (Кіровоградська область)
- AI: goclaw proxy (`http://localhost:18880`) → модель `fast-proxy`
- Порт веб-інтерфейсу: **8422**
