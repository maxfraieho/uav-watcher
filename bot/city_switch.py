"""
bot/city_switch.py — Hot-swap city handler for Sharon bot.

Handles /setcity command from Telegram:
  /setcity               → show current city + inline preset keyboard
  /setcity Кропивницький → geocode and apply
  /setcity 48.5079,32.2623 → apply GPS directly

Also exposes:
  geocode_city_nominatim(city_name) → (lat, lon, display_name) | (None, None, None)
  build_city_cfg(name, lat, lon, region, keywords, radius_km) → dict
  load_presets() → list[dict]
"""

import json
import logging
import os
import re
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS_PATH = os.path.join(_HERE, "data", "city_presets.json")

# ── Presets ────────────────────────────────────────────────────────────────────

def load_presets() -> list:
    """Load city presets from data/city_presets.json. Returns [] on error."""
    try:
        with open(PRESETS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"[city_switch] Could not load presets: {e}")
        return []


# ── Geocoding ──────────────────────────────────────────────────────────────────

def geocode_city_nominatim(city_name: str):
    """
    Geocode city via Nominatim.
    Returns (lat, lon, display_name) or (None, None, None) on failure.
    """
    try:
        q = urllib.parse.urlencode({
            "q": f"{city_name}, Ukraine",
            "format": "json",
            "limit": "1",
            "accept-language": "uk",
        })
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/search?{q}",
            headers={"User-Agent": "Sharon/2.0 (city-switch)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            display = data[0].get("display_name", city_name)
            # Extract region from display_name (usually after city)
            return lat, lon, display
    except Exception as e:
        log.warning(f"[city_switch] Nominatim geocode error for '{city_name}': {e}")
    return None, None, None


def reverse_geocode_region(lat: float, lon: float) -> str:
    """
    Reverse geocode to get oblast name from coordinates.
    Returns region string like 'Кіровоградська область' or '' on failure.
    """
    try:
        q = urllib.parse.urlencode({
            "lat": lat, "lon": lon,
            "format": "json",
            "accept-language": "uk",
        })
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/reverse?{q}",
            headers={"User-Agent": "Sharon/2.0 (city-switch)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        addr = data.get("address", {})
        state = addr.get("state", "")
        if state and "область" not in state.lower():
            state = state + " область"
        return state
    except Exception as e:
        log.warning(f"[city_switch] reverse geocode error: {e}")
    return ""


# ── Config builder ─────────────────────────────────────────────────────────────

def build_city_cfg(name: str, lat: float, lon: float,
                   region: str = "", keywords: list = None,
                   radius_km: int = 30) -> dict:
    """
    Build city sub-config dict suitable for hot_reload_city().
    Keywords auto-generated from name if not provided.
    """
    if not keywords:
        # Generate basic keywords: full name + first 6/8 chars
        kws = [name]
        if len(name) > 6:
            kws.append(name[:8])
        keywords = kws
    return {
        "city": name,
        "city_region": region,
        "city_keywords": keywords,
        "city_lat": lat,
        "city_lon": lon,
        "city_radius_km": radius_km,
    }


# ── Parse input ────────────────────────────────────────────────────────────────

_GPS_RE = re.compile(
    r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*[,\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$"
)

def parse_setcity_arg(arg: str):
    """
    Parse /setcity argument.
    Returns ('gps', lat, lon) | ('name', city_name) | None
    """
    arg = arg.strip()
    if not arg:
        return None
    m = _GPS_RE.match(arg)
    if m:
        try:
            lat, lon = float(m.group(1)), float(m.group(2))
            if 44 <= lat <= 53 and 22 <= lon <= 40:
                return ("gps", lat, lon)
        except ValueError:
            pass
    return ("name", arg)


# ── Telegram handler registration ──────────────────────────────────────────────

def register_setcity_handlers(bot_app, cfg: dict, hot_reload_city_fn, save_config_fn):
    """
    Register /setcity handlers on bot_app (Telethon TelegramClient).

    hot_reload_city_fn(new_city_cfg: dict) — called after successful city change.
    save_config_fn(cfg: dict) — persists cfg to disk.
    """
    from telethon import events
    from telethon.tl.types import KeyboardButtonCallback

    # ── /setcity without argument: show current city + preset keyboard ──────────
    @bot_app.on(events.NewMessage(pattern=r"^/setcity\s*$"))
    async def cmd_setcity_menu(event):
        if not event.is_private:
            return
        current = cfg.get("city", "невідоме")
        presets = load_presets()

        # Build inline rows: 2 buttons per row
        rows = []
        row = []
        for i, p in enumerate(presets):
            row.append(KeyboardButtonCallback(
                text=p["name"],
                data=f"setcity_p_{i}".encode(),
            ))
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        # "Enter manually" button
        rows.append([KeyboardButtonCallback(
            text="✏️ Ввести вручну...",
            data=b"setcity_manual",
        )])

        await event.respond(
            f"📍 *Поточне місто моніторингу:* {current}\n\n"
            "Оберіть нове місто або натисніть «Ввести вручну»:",
            buttons=rows,
            parse_mode="md",
        )

    # ── /setcity CityName or /setcity lat,lon ──────────────────────────────────
    @bot_app.on(events.NewMessage(pattern=r"^/setcity\s+(.+)"))
    async def cmd_setcity_arg(event):
        if not event.is_private:
            return
        arg = event.pattern_match.group(1).strip()
        await _apply_setcity_input(event, arg, cfg, hot_reload_city_fn, save_config_fn)

    # ── Callback: preset selected ───────────────────────────────────────────────
    @bot_app.on(events.CallbackQuery(pattern=rb"setcity_p_(\d+)"))
    async def cb_setcity_preset(event):
        await event.answer()
        idx = int(event.pattern_match.group(1))
        presets = load_presets()
        if idx < 0 or idx >= len(presets):
            await event.respond("❌ Пресет не знайдено.")
            return
        p = presets[idx]
        new_city_cfg = build_city_cfg(
            name=p["name"],
            lat=p["lat"],
            lon=p["lon"],
            region=p["region"],
            keywords=p.get("keywords"),
            radius_km=p.get("radius_km", 30),
        )
        await _commit_city_change(event, new_city_cfg, cfg, hot_reload_city_fn, save_config_fn)

    # ── Callback: manual input prompt ──────────────────────────────────────────
    @bot_app.on(events.CallbackQuery(data=b"setcity_manual"))
    async def cb_setcity_manual(event):
        await event.answer()
        await event.respond(
            "✏️ Надішли назву міста або GPS-координати:\n\n"
            "Приклади:\n"
            "`/setcity Кропивницький`\n"
            "`/setcity 48.5079, 32.2623`",
            parse_mode="md",
        )

    log.info("[city_switch] /setcity handlers registered")


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _apply_setcity_input(event, arg: str, cfg, hot_reload_fn, save_fn):
    """Parse arg, geocode if needed, then commit."""
    parsed = parse_setcity_arg(arg)
    if parsed is None:
        await event.respond("❌ Не зрозумів. Спробуй: `/setcity Кропивницький`", parse_mode="md")
        return

    if parsed[0] == "gps":
        _, lat, lon = parsed
        # Reverse geocode for display
        region = reverse_geocode_region(lat, lon)
        name = f"{lat:.4f}, {lon:.4f}"
        keywords = [str(round(lat, 2))]  # minimal keyword
        new_city_cfg = build_city_cfg(name=name, lat=lat, lon=lon, region=region,
                                      keywords=keywords, radius_km=30)

    elif parsed[0] == "name":
        city_name = parsed[1]
        await event.respond(f"🔍 Геокодую: *{city_name}*...", parse_mode="md")

        # Check presets first (fast, no network)
        new_city_cfg = _find_in_presets(city_name)
        if new_city_cfg is None:
            # Nominatim lookup
            lat, lon, display_name = geocode_city_nominatim(city_name)
            if lat is None:
                await event.respond(
                    f"❌ Не знайшов *{city_name}* в Nominatim.\n\n"
                    "Спробуй точнішу назву або GPS-координати:\n"
                    f"`/setcity 48.5079, 32.2623`",
                    parse_mode="md",
                )
                return
            region = reverse_geocode_region(lat, lon)
            new_city_cfg = build_city_cfg(
                name=city_name, lat=lat, lon=lon,
                region=region, radius_km=30,
            )
    else:
        return

    await _commit_city_change(event, new_city_cfg, cfg, hot_reload_fn, save_fn)


async def _commit_city_change(event, new_city_cfg: dict, cfg: dict, hot_reload_fn, save_fn):
    """Apply city change: hot-reload in memory, persist to disk, notify user."""
    try:
        # 1. Hot-reload in memory (no restart)
        hot_reload_fn(new_city_cfg)
        # 2. Persist to disk
        cfg.update(new_city_cfg)
        save_fn(cfg)
        # 3. Notify
        city = new_city_cfg["city"]
        lat = new_city_cfg["city_lat"]
        lon = new_city_cfg["city_lon"]
        region = new_city_cfg.get("city_region", "")
        kws = ", ".join(new_city_cfg.get("city_keywords", []))
        region_line = f"\n📍 Область: {region}" if region else ""
        await event.respond(
            f"✅ *Моніторинг перемкнуто на:*\n\n"
            f"🏙 Місто: *{city}*{region_line}\n"
            f"🗺 Координати: `{lat:.4f}, {lon:.4f}`\n"
            f"🔑 Ключові слова: `{kws}`\n\n"
            f"_Зміна набула чинності без перезапуску._",
            parse_mode="md",
        )
        log.info(f"[city_switch] City changed to: {city} ({lat}, {lon})")
    except Exception as e:
        log.error(f"[city_switch] commit error: {e}")
        await event.respond(f"❌ Помилка при зміні міста: {e}")


def _find_in_presets(city_name: str) -> dict | None:
    """Check if city_name matches any preset (case-insensitive). Returns city_cfg or None."""
    name_lower = city_name.lower().strip()
    presets = load_presets()
    for p in presets:
        if p["name"].lower() == name_lower:
            return build_city_cfg(
                name=p["name"],
                lat=p["lat"],
                lon=p["lon"],
                region=p["region"],
                keywords=p.get("keywords"),
                radius_km=p.get("radius_km", 30),
            )
        # Also check keywords
        if any(kw.lower() == name_lower for kw in p.get("keywords", [])):
            return build_city_cfg(
                name=p["name"],
                lat=p["lat"],
                lon=p["lon"],
                region=p["region"],
                keywords=p.get("keywords"),
                radius_km=p.get("radius_km", 30),
            )
    return None
