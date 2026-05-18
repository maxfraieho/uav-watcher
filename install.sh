#!/bin/bash
# UAV Watcher — Termux installer
# Usage: curl -fsSL https://raw.githubusercontent.com/maxfraieho/uav-watcher/master/install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[UAV]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC} $1"; exit 1; }
ask()     { echo -e "${BOLD}$1${NC}"; }

INSTALL_DIR="$HOME/uav-watcher"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       UAV Watcher — Termux Setup     ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Залежності ────────────────────────────────────────────────────────────
info "Встановлення системних пакетів..."
if command -v pkg &>/dev/null; then
    pkg update -y -q
    pkg install -y python git curl 2>/dev/null || true
    success "Пакети встановлено (Termux)"
elif command -v apt-get &>/dev/null; then
    apt-get update -q && apt-get install -y python3 git curl 2>/dev/null || true
    success "Пакети встановлено (apt)"
else
    warn "Невідомий менеджер пакетів — встанови python та git вручну"
fi

# ── 2. Клонування ────────────────────────────────────────────────────────────
info "Завантаження UAV Watcher..."
if [ -d "$INSTALL_DIR" ]; then
    warn "Папка $INSTALL_DIR вже існує — оновлюємо"
    cd "$INSTALL_DIR" && git pull
else
    git clone https://github.com/maxfraieho/uav-watcher "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
success "Код завантажено в $INSTALL_DIR"

# ── 3. Python-залежності ─────────────────────────────────────────────────────
info "Встановлення Python бібліотек..."
pip install --quiet telethon httpx python-dotenv 2>/dev/null || \
    pip3 install --quiet telethon httpx python-dotenv
success "telethon, httpx, python-dotenv встановлено"

# ── 4. Налаштування .env ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══ НАЛАШТУВАННЯ TELEGRAM ══${NC}"
echo ""
warn "Потрібні API credentials з https://my.telegram.org"
warn "Зайди → API development tools → App api_id та App api_hash"
echo ""

if [ ! -f "$INSTALL_DIR/.env" ]; then
    ask "Введи Telegram API ID (числовий):"
    read -r API_ID
    ask "Введи Telegram API Hash (рядок hex):"
    read -r API_HASH
    ask "Введи номер телефону (формат +380XXXXXXXXX):"
    read -r PHONE

    cat > "$INSTALL_DIR/.env" <<EOF
TELEGRAM_API_ID=$API_ID
TELEGRAM_API_HASH=$API_HASH
TELEGRAM_PHONE=$PHONE
EOF
    success ".env створено"
else
    warn ".env вже існує — пропускаємо (редагуй вручну якщо треба)"
fi

# ── 5. Налаштування config.json ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}══ НАЛАШТУВАННЯ МІСТА ══${NC}"
echo ""

ask "Введи назву міста (Enter = Олександрія):"
read -r CITY
CITY="${CITY:-Олександрія}"

ask "Введи область (Enter = Кіровоградська область):"
read -r REGION
REGION="${REGION:-Кіровоградська область}"

echo ""
echo -e "${BOLD}══ TELEGRAM БОТ ══${NC}"
echo ""
warn "Створи бота через @BotFather → /newbot → скопіюй токен"
ask "Введи Bot Token:"
read -r BOT_TOKEN

warn "Дізнайся свій User ID через @userinfobot або @getmyid_bot"
ask "Введи свій Telegram User ID (числовий):"
read -r NOTIFY_ID

echo ""
echo -e "${BOLD}══ AI СЕРВІС ══${NC}"
echo ""
echo "  Для класифікації загроз використовується AI-проксі."
echo ""
echo -e "  ${GREEN}[1] Спільний проксі (за замовчуванням)${NC} — безкоштовно, не потрібен ключ"
echo -e "      ${CYAN}YOUR_PROXY_HOST${NC}"
echo -e "  ${YELLOW}[2] Свій AI endpoint${NC} — OpenAI, Groq, OpenRouter або власний сервер"
echo ""
ask "Вибір (Enter = 1, спільний проксі):"
read -r AI_CHOICE

if [ "$AI_CHOICE" = "2" ]; then
    ask "Введи URL AI endpoint (наприклад https://api.openai.com/v1/chat/completions):"
    read -r AI_URL
    ask "Введи API ключ:"
    read -r AI_KEY
    ask "Введи назву моделі (Enter = gpt-4o-mini):"
    read -r AI_MODEL
    AI_MODEL="${AI_MODEL:-gpt-4o-mini}"
    success "Використовуватиметься власний AI endpoint"
else
    AI_URL="https://YOUR_PROXY_URL/v1/chat/completions"
    AI_KEY="freecc"
    AI_MODEL="fast-proxy"
    success "Використовуватиметься спільний AI проксі (YOUR_PROXY_HOST)"
fi

# Генерація keywords з назви міста
CITY_FIRST4="${CITY:0:4}"

cat > "$INSTALL_DIR/config.json" <<EOF
{
  "city": "$CITY",
  "city_region": "$REGION",
  "city_keywords": ["$CITY", "${CITY:0:8}"],
  "channels": [],
  "bot_token": "$BOT_TOKEN",
  "notify_chat_id": $NOTIFY_ID,
  "goclaw_url": "$AI_URL",
  "goclaw_api_key": "$AI_KEY",
  "goclaw_model": "$AI_MODEL"
}
EOF
success "config.json створено"

# ── 6. Авторизація Telethon ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══ АВТОРИЗАЦІЯ TELETHON ══${NC}"
echo ""
warn "Зараз запустимо авторизацію. Telegram надішле код на твій номер."
warn "Після авторизації буде створений файл uav_watcher.session"
echo ""
ask "Натисни Enter для авторизації (або Ctrl+C для пропуску):"
read -r _SKIP

cd "$INSTALL_DIR"
python auth.py 2>/dev/null || python3 auth.py

# ── 7. Додавання каналів ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══ КАНАЛИ ══${NC}"
echo ""
warn "Канали потрібно додати вручну в config.json"
warn "Дізнатись ID каналу: переслати повідомлення боту @userinfobot"
warn "Приклад: [-1002187970584, -1001234567890]"
echo ""
warn "Файл конфігурації: $INSTALL_DIR/config.json"
warn "Після додавання каналів запусти: cd ~/uav-watcher && python uav_watcher.py"

# ── 8. Скрипт запуску ────────────────────────────────────────────────────────
cat > "$INSTALL_DIR/start.sh" <<'STARTSCRIPT'
#!/bin/bash
# UAV Watcher — запуск watcher + web config UI
cd "$(dirname "$0")"
PYTHON=$(command -v python3 || command -v python)

if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock
    echo "[UAV] Wake lock активовано"
fi

"$PYTHON" web_config.py &
WEB_PID=$!
echo "[UAV] Web Config UI: http://localhost:8422 (PID $WEB_PID)"

echo "[UAV] Запуск UAV Watcher..."
"$PYTHON" uav_watcher.py

kill $WEB_PID 2>/dev/null
STARTSCRIPT
chmod +x "$INSTALL_DIR/start.sh"

# ── 9. Автозапуск ────────────────────────────────────────────────────────────
info "Налаштування автозапуску..."
AUTOSTART_TYPE="невідомо"

setup_autostart() {
    # Termux (Android)
    if [ -d "$HOME/.termux" ] || command -v termux-info &>/dev/null; then
        if [ -d "$HOME/.termux/boot" ] || mkdir -p "$HOME/.termux/boot" 2>/dev/null; then
            cp "$INSTALL_DIR/start.sh" "$HOME/.termux/boot/uav-watcher.sh"
            chmod +x "$HOME/.termux/boot/uav-watcher.sh"
            AUTOSTART_TYPE="Termux:Boot (~/.termux/boot/)"
            success "Termux:Boot налаштовано — переконайся що Termux:Boot встановлено з F-Droid"
            return 0
        fi
    fi

    # systemd (Linux з systemd --user)
    if command -v systemctl &>/dev/null && systemctl --user daemon-reload &>/dev/null 2>&1; then
        SDIR="$HOME/.config/systemd/user"
        mkdir -p "$SDIR"
        PYTHON=$(command -v python3 || command -v python)
        cat > "$SDIR/uav-watcher.service" <<EOF
[Unit]
Description=UAV Watcher
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON $INSTALL_DIR/uav_watcher.py
Restart=always

[Install]
WantedBy=default.target
EOF
        cat > "$SDIR/uav-web-config.service" <<EOF
[Unit]
Description=UAV Web Config UI
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON $INSTALL_DIR/web_config.py
Restart=always

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload
        systemctl --user enable uav-watcher.service uav-web-config.service 2>/dev/null
        AUTOSTART_TYPE="systemd --user"
        success "systemd user-сервіси зареєстровано"
        return 0
    fi

    # OpenRC (Alpine Linux та ін.)
    if command -v rc-update &>/dev/null && command -v sudo &>/dev/null; then
        PYTHON=$(command -v python3 || command -v python)
        sudo tee /etc/init.d/uav-watcher > /dev/null <<EOF
#!/sbin/openrc-run
name="uav-watcher"
description="UAV Alert Watcher"
command="$PYTHON"
command_args="$INSTALL_DIR/uav_watcher.py"
command_user="$USER"
command_background=true
pidfile="/run/uav-watcher.pid"
output_log="$INSTALL_DIR/uav-watcher.log"
directory="$INSTALL_DIR"
depend() { need net; }
EOF
        sudo tee /etc/init.d/uav-web-config > /dev/null <<EOF
#!/sbin/openrc-run
name="uav-web-config"
description="UAV Web Config UI"
command="$PYTHON"
command_args="$INSTALL_DIR/web_config.py"
command_user="$USER"
command_background=true
pidfile="/run/uav-web-config.pid"
output_log="$INSTALL_DIR/web-config.log"
directory="$INSTALL_DIR"
depend() { need net; }
EOF
        sudo chmod +x /etc/init.d/uav-watcher /etc/init.d/uav-web-config
        sudo touch "$INSTALL_DIR/uav-watcher.log" "$INSTALL_DIR/web-config.log"
        sudo chown "$USER" "$INSTALL_DIR/uav-watcher.log" "$INSTALL_DIR/web-config.log"
        sudo rc-update add uav-watcher default 2>/dev/null
        sudo rc-update add uav-web-config default 2>/dev/null
        AUTOSTART_TYPE="OpenRC (/etc/init.d/)"
        success "OpenRC сервіси зареєстровано"
        return 0
    fi

    # cron @reboot (universal fallback)
    if command -v crontab &>/dev/null; then
        (crontab -l 2>/dev/null | grep -v "uav-watcher"; echo "@reboot bash $INSTALL_DIR/start.sh >> $INSTALL_DIR/uav-watcher.log 2>&1") | crontab -
        AUTOSTART_TYPE="cron @reboot"
        success "Cron @reboot налаштовано"
        return 0
    fi

    warn "Автозапуск не налаштовано — запускай вручну: bash $INSTALL_DIR/start.sh"
    AUTOSTART_TYPE="ручний запуск"
}

setup_autostart

# ── 10. Результат ────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Встановлення завершено!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════${NC}"
echo ""
echo "  Папка:        $INSTALL_DIR"
echo "  Конфіг:       $INSTALL_DIR/config.json"
echo "  Секрети:      $INSTALL_DIR/.env"
echo "  Автозапуск:   $AUTOSTART_TYPE"
echo ""
echo -e "${BOLD}  Наступні кроки:${NC}"
echo "  1. Додай ID каналів у config.json або через веб:"
echo -e "     ${CYAN}http://localhost:8422${NC}"
echo "  2. Запусти: bash $INSTALL_DIR/start.sh"
echo "  3. Веб-інтерфейс: http://localhost:8422"
echo ""
