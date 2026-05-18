# UAV Watcher — Project Context for Claude Code

> Civilian UAV/rocket alert monitoring system for Ukraine.
> Monitors Telegram channels → AI classification → family notifications.

---

## 🗺️ Architecture overview

```
Telegram channels (Telethon MTProto userbot)
    ↓  keyword pre-filter (city_keywords)
AI proxy (goclaw / OpenAI-compatible)
    ↓  JSON: {"threat": true/false, "reason": "..."}
Telegram Bot API → notify_chat_id
    +
alerts.in.ua official API (parallel poller)
    ↓
web_config.py (port 8422)
    ├── GET /        → admin config UI (9 languages)
    ├── GET /share   → public page for family members
    ├── POST /api/shelter      → Overpass API shelter search
    ├── POST /api/shelter-chat → AI chat (keyword match OR consultant service)
    └── POST /api/sos          → SOS: Telegram + relay to rescue_peers
```

---

## 📁 File responsibilities

| File | Role |
|------|------|
| `uav_watcher.py` | Main process: Telethon userbot + Bot API handlers |
| `web_config.py` | HTTP server 8422: admin UI + /share public page (133KB — God File) |
| `auth.py` | One-time Telethon session creation |
| `config.json` | Runtime config: city, channels, tokens, tunnel state |
| `.env` | Secrets: TELEGRAM_API_ID, API_HASH, PHONE |
| `bot/crisis_templates.py` | 7 threat type templates + grounding technique |
| `db/models.py` | SQLite: families, rollcalls, rollcall_responses |
| `family/bot_handlers.py` | `/family_create`, `/family_join`, `/family_status`, `/sos` commands |
| `rescue/location_tracker.py` | Dead man's switch location handler |
| `integrations/alerts_ua.py` | alerts.in.ua official API poller |
| `integrations/meshtastic_bridge.py` | LoRa mesh bridge scaffold |
| `consultant/` | Standalone RAG service (FastAPI + LangGraph + BM25) |
| `web/pwa/index.html` | PWA scaffold — NOT implemented yet |

---

## 🖥️ Server

- **Host:** `192.168.3.184` (Alpine Linux + OpenRC)
- **SSH:** `sshpass -p '${ADMIN_PASS}' ssh -o StrictHostKeyChecking=no vokov@192.168.3.184`
- **Web UI:** `http://localhost:8422` or via Cloudflare tunnel
- **Watcher log:** `tail -f ~/uav-watcher/uav.log`

Passwords and tokens are in `.env` and `config.json` — NEVER hardcode them in source.

---

## 🔧 Cloudflare Tunnel

- Tunnel ID: in `.cloudflared/` (gitignored) and `config.json`
- Wildcard DNS: `*.your-domain.example` — users pick prefix → `{prefix}-alert.your-domain.example`
- **CRITICAL:** `CF_TUNNEL_ID` in `web_config.py` is hardcoded — should be moved to `config.json`
- `tunnel_pid` stored in `config.json` — fragile, check with `/proc/{pid}/cmdline`

---

## ✅ Implementation state (as of 2026-05-17)

### Done (code exists and is wired)
- [x] Phase 0.1 — Crisis templates (`bot/crisis_templates.py`)
- [x] Phase 0.2 — `/status` command in `uav_watcher.py`
- [x] Phase 0.3 — alerts.in.ua integration (`integrations/alerts_ua.py`)
- [x] Cloudflare tunnel management in `web_config.py`
- [x] SOS + rescue signal (web + `/api/sos`)
- [x] Shelter search (Overpass API, 3km, 1h cache)
- [x] Multi-language UI (9 languages incl. RTL ar/fa)
- [x] P2P rescue relay (`rescue_peers` → `/api/sos-relay`)

### Written but NOT yet wired into main process
- [ ] Phase 1.1 — `db/models.py` exists but `init_db()` not called at startup
- [ ] Phase 1.2 — `family/bot_handlers.py` exists, `register_family_handlers()` present in `uav_watcher.py` (lines ~3573–3574) — **verify it's actually reached**
- [ ] Phase 2.1 — `rescue/location_tracker.py` exists, `register_location_handlers()` in `uav_watcher.py` — **verify**
- [ ] Phase 3.1 — `integrations/meshtastic_bridge.py` scaffold only, not integrated

### Known pending
- [ ] `web/pwa/index.html` — 487-byte scaffold, all TODO
- [ ] Consultant service NOT connected to `/api/shelter-chat` — uses keyword matching instead
- [ ] `rescue_peers` management UI not in web config
- [ ] PWA: manifest + service worker

---

## 🐛 Known bugs & critical issues

### Security
1. **Admin UI publicly accessible** — `web_config.py` runs on `0.0.0.0:8422` with NO auth.
   With Cloudflare tunnel active, anyone knowing the URL can change tokens, channels, restart service.
   **Fix needed:** split admin routes (require localhost-only or Basic Auth) from `/share` public routes.

2. **`CF_TUNNEL_ID` hardcoded** in `web_config.py` — move to `config.json`.

3. **`config.json` has no file locking** — concurrent read/write between `uav_watcher.py` and `web_config.py`
   can corrupt it. Use `fcntl.flock()` in `save_config()`.

### Code bugs
4. **`add_messages` type mismatch in `consultant/pipeline/states.py`:**
   ```python
   # states.py — wrong: add_messages expects BaseMessage objects
   messages: Annotated[list, add_messages]
   # nodes.py — returns plain dicts, not HumanMessage/AIMessage
   {"type": "human", "content": ...}
   ```
   Either use `from langchain_core.messages import HumanMessage, AIMessage` in nodes.py,
   or remove `add_messages` annotation and use plain `list`.

5. **`_llm_call()` in `consultant/pipeline/nodes.py` is synchronous** — blocks FastAPI event loop.
   Replace with `async def _llm_call()` + `httpx.AsyncClient`.

6. **`restart_service()` only handles OpenRC** — `install.sh` also supports systemd.
   Add `systemctl --user restart uav-watcher` branch.

7. **`CHAT_KB` in `web_config.py` duplicates `TEMPLATES` in `bot/crisis_templates.py`** — DRY violation.
   Import from `bot.crisis_templates` instead.

8. **Rate limiting missing for family SOS broadcast** — sequential `httpx.post()` per member
   will hit Telegram's 429 at 30+ members. Need token-bucket queue (max 25 msg/sec).

---

## ⚙️ Known quirks

- `socket.getaddrinfo()` doesn't work for tunnel conflict check — wildcard `*.your-domain.example` resolves everything.
  `web_config.py` checks against stored URL instead.
- Overpass API requires `"User-Agent": "UAVWatcher/1.0"` — returns 406 without it.
- AI proxy requires `"User-Agent": "curl/7.88.1"` for urllib requests — Cloudflare WAF blocks Python default UA.
- `tunnel_pid` in `config.json` can be stale after system reboot — always verify via `/proc/{pid}/cmdline`.
- SSH background start may return exit 255 (nohup exits before SSH closes) — service does start, check `pgrep -f web_config.py`.

---

## 🤖 AI / LLM stack

| Service | URL | Key | Model |
|---------|-----|-----|-------|
| Main watcher classifier | `config.json → goclaw_url` | `config.json → goclaw_api_key` | `goclaw_model` |
| Consultant (RAG service) | `localhost:8770` | `PROXY_TOKEN` env | `PROXY_MODEL` env |

Both use OpenAI-compatible `/v1/chat/completions` format.

**Classifier prompt rules:**
- `threat=true`: active UAV/missile attack right now for configured city
- `threat=false`: all-clear, end of alert, cancellation — words "відбій" = false
- Response ONLY JSON, no markdown: `{"threat": bool, "reason": "short"}`

---

## 🧠 Consultant RAG service (`consultant/`)

Standalone FastAPI service on port 8770. **Currently NOT connected to main app.**

```
POST /chat → LangGraph graph:
  retrieve_kb (BM25Plus on knowledge/*.md)
  → generate (LLM with KB context + last 6 messages)
  → MemorySaver per session_id
```

**To connect to web_config.py** — replace `chat_match()` call in `/api/shelter-chat` handler
with HTTP call to `http://localhost:8770/chat` + fallback to keyword matching.

**Knowledge base is thin** — only `consultant/knowledge/00-crisis-base.md` (6.5KB).
Add content from `discawe/` research and `docs/manual-uk.md` for better retrieval.

---

## 🗄️ Database (`data/families.db`)

SQLite, zero external deps, local for OPSEC.

Tables: `families`, `family_members`, `rollcalls`, `rollcall_responses`

`init_db()` must be called at startup in `uav_watcher.py` (currently not explicitly called).
Connection pattern: open/close per operation (no connection pool) — fine for current scale.

---

## 🔐 Security rules for this codebase

- **NEVER** put real credentials in source code or CLAUDE.md
- **NEVER** `git add .` — add files individually
- `.env`, `*.session`, `*.session-journal`, `.cloudflared/` are gitignored — keep it that way
- `config.json` contains tokens — gitignored? Check `.gitignore`. If not, add it.
- `bot_token` exposure = anyone can impersonate the bot
- `API_ID/API_HASH/PHONE` exposure = Telegram account compromise

---

## 🧪 Testing

```bash
# Verify crisis templates
python3 -c "from bot.crisis_templates import TEMPLATES; print(list(TEMPLATES.keys()))"

# Test AI classifier
python3 -c "
import asyncio
from uav_watcher import ai_classify, load_config
cfg = load_config()
print(asyncio.run(ai_classify('БПЛА у напрямку Олександрії', cfg)))
"

# Consultant pipeline
cd consultant && python3 -m pytest tests/ -v

# BM25 retrieval
python3 -c "
from knowledge_base import retrieval
retrieval.init('knowledge/')
print(retrieval.retrieve('що робити при бпла', top_k=2))
"
```

---

## 🚀 Run

```bash
# Start both services
cd ~/uav-watcher && bash start.sh

# Or separately
python3 web_config.py &
python3 uav_watcher.py

# Consultant service (separate)
cd consultant && uvicorn main:app --port 8770

# Check alive
pgrep -fa uav_watcher
pgrep -fa web_config

# OpenRC service
sudo rc-service uav-watcher restart
sudo rc-service uav-watcher status
```

---

## 📋 Next priorities (ordered)

1. **P0** — Split admin/public routes in `web_config.py` + Basic Auth for admin
2. **P0** — `CF_TUNNEL_ID` → `config.json`
3. **P1** — Wire consultant service into `/api/shelter-chat` with keyword fallback
4. **P1** — Add `init_db()` call to `uav_watcher.py` startup
5. **P1** — Fix `add_messages` bug in `consultant/pipeline/states.py`
6. **P1** — Make `_llm_call` async in `consultant/pipeline/nodes.py`
7. **P2** — Add `fcntl` file locking to `save_config()`
8. **P2** — Enrich `consultant/knowledge/` with content from `discawe/` and `docs/`
9. **P2** — Token-bucket rate limiter for family SOS broadcast
10. **P3** — PWA: service worker + offline cache for `/share` page

---

## 🔗 External services

| Service | Docs | Notes |
|---------|------|-------|
| Telegram Bot API | `api.telegram.org` | `bot_token` in config.json |
| Telethon MTProto | `docs.telethon.dev` | Session in `uav_watcher.session` |
| alerts.in.ua | `devs.alerts.in.ua` | Token optional: `alerts_ua_token` in config |
| Overpass API | `overpass-api.de` | OSM shelter data, needs User-Agent header |
| Nominatim | `nominatim.openstreetmap.org` | Geocoding for city lat/lon |
| Cloudflare Tunnel | `cloudflare.com` | Creds in `.cloudflared/` (gitignored) |
| Meshtastic | `meshtastic.org` | LoRa hardware, bridge not yet integrated |
