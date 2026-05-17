# UAV Watcher — Project Context for Claude Code

## What this is
Python Telegram monitoring bot + web config UI for civilian UAV/rocket alert tracking in Ukraine.
- `uav_watcher.py` — Telethon (MTProto) client that monitors Telegram channels for alerts, classifies them via AI, sends to configured notify_chat_id via Bot API
- `web_config.py` — HTTPServer on port 8422: config UI + public /share page for family members

## Servers
- **Dev/Run server**: `192.168.3.184` (Alpine Linux, pass `805235io.` with dot)
- **SSH**: `sshpass -p '805235io.' ssh -o StrictHostKeyChecking=no vokov@192.168.3.184`
- **Web UI**: `http://localhost:8422` (local) or via Cloudflare tunnel

## Cloudflare Tunnel
- Tunnel name: `uav-watcher-alerts`, ID: `c0413dca-1f1d-4176-be39-23e2c8f0754f`
- Wildcard DNS: `*.exodus.pp.ua` — users pick prefix → `{prefix}-alert.exodus.pp.ua`
- Credentials in `.cloudflared/` (gitignored: private keys)
- Start via web UI → Tunnel card → enter prefix → Start

## What's implemented (as of 2026-05-17)

### web_config.py routes
- `GET /` — config UI (9 languages, RTL ar/fa)
- `GET /share` — public landing page for family members (QR/link recipients)
- `GET /api/tunnel` — tunnel status JSON
- `GET /api/bot-info` — Telegram bot username/URL
- `POST /tunnel-check` — check prefix availability
- `POST /tunnel-start` — start Cloudflare tunnel
- `POST /tunnel-stop` — stop tunnel
- `POST /api/shelter` — Overpass API shelter search by lat/lon (cached 1h)
- `POST /api/shelter-chat` — AI chat via goclaw (shelter + safety advice)
- `POST /api/sos` — trigger SOS: Telegram alert + relay to rescue_peers
- `POST /api/sos-relay` — receive SOS from peer UAV Watcher instances

### /share page features
1. Alert monitoring status
2. Telegram bot connect (deep link to @OlBPLA_bot)
3. Shelter search (Overpass API, OSM data, 3km radius)
4. AI shelter chat (goclaw LLM, threat level awareness)
5. **Rescue signal mode** — ARM → DeviceMotion impact detection → 30s countdown → SOS overlay + Web Audio morse beep + Telegram alert

### P2P rescue network design
- `rescue_peers` list in config.json — URLs of peer UAV Watcher instances
- When SOS fires → POST `/api/sos-relay` to all peers → each peer sends Telegram to its own notify_chat_id
- No central server needed; bootstrap by sharing tunnel URLs

## AI / LLM
- Model: `docs-assistant-proxy` via `https://openai-proxy.exodus.pp.ua/v1/chat/completions`
- API key: `freecc` (from config.json `goclaw_api_key`)
- **IMPORTANT**: urllib requests to this endpoint require `"User-Agent": "curl/7.88.1"` header — Cloudflare WAF blocks Python-urllib default UA

## Known quirks
- `socket.getaddrinfo()` doesn't work for conflict check (wildcard DNS `*.exodus.pp.ua` resolves everything) — uses local URL check instead
- Overpass API requires `"User-Agent": "UAVWatcher/1.0"` header — returns 406 without it
- SSH background start sometimes returns exit 255 (nohup exits before SSH closes) — service does start, check with `pgrep -f web_config.py`

## Pending / Next steps
- [ ] Bot subscriber flow: `/api/sos-relay` on family devices that opened /share should also subscribe them to receive future alerts (currently only notify_chat_id receives)
- [ ] In uav_watcher.py: monitor a shared rescue coordination Telegram channel → relay nearby SOS to local channels
- [ ] Web UI: add `rescue_peers` management in config page (add/remove peer URLs)
- [ ] Web UI: show incoming SOS relay notifications in config page
- [ ] Cloudflare Worker as optional central rescue registry (geo-based discovery without manual peering)

## git
- Remote: `github.com:maxfraieho/uav-watcher.git`
- `git add .` is FORBIDDEN — add files individually
- `.cloudflared/` is gitignored (private tunnel credentials)
