# UAV Watcher — Встановлення на смартфон (Termux)

Запустити моніторинг БПЛА-загроз прямо на Android-смартфоні — без сервера.

## Що потрібно

- Android смартфон
- Застосунок **Termux** (з F-Droid, не з Google Play — та версія застаріла)
- Telegram акаунт
- API ключ будь-якого OpenAI-сумісного сервісу (OpenAI, Groq, OpenRouter, тощо)

---

## Крок 1 — Встановити Termux

1. Встановити **F-Droid**: [f-droid.org](https://f-droid.org)
2. В F-Droid знайти **Termux** → встановити
3. *(необов'язково)* Також встановити **Termux:Boot** — для автозапуску при включенні телефону

---

## Крок 2 — Встановити curl і запустити інсталятор

Відкрити Termux і виконати одну команду:

```bash
pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/maxfraieho/uav-watcher/master/install.sh | bash
```

Інсталятор автоматично:
- Встановить Python, git та всі залежності
- Завантажить код з GitHub
- Запитає всі необхідні дані (крок за кроком)
- Авторизує Telethon
- Створить скрипт запуску `start.sh`

---

## Що запитає інсталятор

### Telegram API credentials
Потрібні з [my.telegram.org](https://my.telegram.org):
1. Зайти → **API development tools**
2. Створити застосунок (будь-яка назва)
3. Записати **App api_id** (число) та **App api_hash** (рядок hex)

### Telegram Bot Token
1. Написати [@BotFather](https://t.me/BotFather) → `/newbot`
2. Дати назву боту
3. Скопіювати токен вигляду `1234567890:ABC...`

### Свій Telegram User ID
Написати будь-якому з ботів:
- [@userinfobot](https://t.me/userinfobot)
- [@getmyid_bot](https://t.me/getmyid_bot)

Бот відповість числом — це твій `notify_chat_id`.

### AI endpoint
Варіанти (будь-який OpenAI-сумісний):

| Сервіс | URL | Ціна |
|--------|-----|------|
| OpenAI | `https://api.openai.com/v1/chat/completions` | платно |
| Groq | `https://api.groq.com/openai/v1/chat/completions` | є безкоштовний tier |
| OpenRouter | `https://openrouter.ai/api/v1/chat/completions` | є безкоштовні моделі |
| Свій goclaw | `http://192.168.X.X:18880/v1/chat/completions` | якщо є локальний сервер |

**Рекомендація для старту:** Groq — безкоштовно, швидко.
- Реєстрація: [console.groq.com](https://console.groq.com)
- Модель: `llama-3.1-8b-instant` (безкоштовна)

---

## Крок 3 — Додати канали для моніторингу

Після встановлення потрібно додати числові ID Telegram-каналів.

**Як дізнатись ID каналу:**
1. Відкрити потрібний канал у Telegram
2. Переслати будь-яке повідомлення боту [@userinfobot](https://t.me/userinfobot)
3. Бот поверне ID каналу (від'ємне число, наприклад `-1002187970584`)

**Додати в config.json:**
```bash
nano ~/uav-watcher/config.json
```

Знайти рядок `"channels": []` і замінити на:
```json
"channels": [-1002187970584, -1001234567890]
```

Зберегти: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Крок 4 — Запустити

```bash
cd ~/uav-watcher && bash start.sh
```

Або якщо хочеш залишити в фоні і закрити Termux:
```bash
cd ~/uav-watcher && nohup bash start.sh > uav.log 2>&1 &
```

Перевірити лог:
```bash
tail -f ~/uav-watcher/uav.log
```

---

## Автозапуск при включенні телефону (Termux:Boot)

1. Встановити **Termux:Boot** з F-Droid
2. Запустити Termux:Boot хоча б раз (щоб активувати)
3. Виконати в Termux:

```bash
mkdir -p ~/.termux/boot
cp ~/uav-watcher/start.sh ~/.termux/boot/uav-watcher.sh
```

Тепер при кожному перезавантаженні телефону сервіс запускатиметься автоматично.

---

## Відмінності від серверного запуску

| Параметр | Сервер (OpenRC) | Termux |
|----------|-----------------|--------|
| Менеджер процесів | `rc-service` | `nohup` / Termux:Boot |
| Веб-конфіг restart | ✅ працює | ❌ кнопка перезапуску не працює |
| AI endpoint | локальний goclaw | зовнішній API |
| Автозапуск | `rc-update add` | Termux:Boot |
| Споживання батареї | — | ~5% на добу (активний wake lock) |

---

## Оновлення

```bash
cd ~/uav-watcher && git pull && pip install --upgrade telethon httpx python-dotenv
```

---

## Часті проблеми

**`FloodWaitError`** — Telegram обмежив запити. Почекай кілька хвилин, сервіс відновиться сам.

**`SessionPasswordNeededError`** — акаунт захищений 2FA. При авторизації введи пароль.

**Повідомлення не надходять** — перевір:
1. Правильність ID каналів в `config.json`
2. Чи є повідомлення з ключовими словами міста в каналі
3. Логи: `tail -f ~/uav-watcher/uav.log`

**AI не відповідає** — перевір endpoint та API ключ:
```bash
curl -s "$AI_URL" \
  -H "Authorization: Bearer $AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' | python3 -m json.tool
```

**Телефон вимикає Termux** — зайти в Налаштування → Батарея → знайти Termux → вимкнути оптимізацію батареї.
