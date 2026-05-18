"""
shelter_search.py — пошук укриттів ЦО за GPS.
Overpass API (фільтр реальних укриттів) + Nominatim адреси + відстань.
Статичний seed як fallback коли OSM порожній.
"""
import asyncio
import json
import logging
import math
import os
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
CACHE_FILE = Path(__file__).parent / "data" / "shelters_cache.json"
SEED_DIR = Path(__file__).parent / "data"
CACHE_TTL = 86400  # 24 год

_SKIP_TYPES = {"picnic_shelter", "public_transport", "gazebo", "lean_to", "basic_hut"}

_cache_lock = asyncio.Lock()


def _haversine(lat1, lon1, lat2, lon2) -> int:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return int(R * 2 * math.asin(math.sqrt(a)))


def _query_overpass(lat: float, lon: float, radius_m: int = 2000) -> list:
    """Overpass: вибірка тільки реальних укриттів (не газони і зупинки)."""
    query = (
        f"[out:json][timeout:25];\n("
        f'  node["civil_defence"="shelter"](around:{radius_m},{lat},{lon});\n'
        f'  node["emergency"="shelter"](around:{radius_m},{lat},{lon});\n'
        f'  node["building"="bunker"](around:{radius_m},{lat},{lon});\n'
        f'  node["amenity"="shelter"]["shelter_type"!="picnic_shelter"]'
        f'["shelter_type"!="public_transport"]["shelter_type"!="gazebo"]'
        f'["shelter_type"!="lean_to"](around:{radius_m},{lat},{lon});\n'
        f'  way["civil_defence"="shelter"](around:{radius_m},{lat},{lon});\n'
        f'  way["amenity"="shelter"]["shelter_type"!="picnic_shelter"]'
        f'["shelter_type"!="public_transport"](around:{radius_m},{lat},{lon});\n'
        f");\nout tags center;"
    )
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(
            OVERPASS_URL, data=data,
            headers={"User-Agent": "UAVWatcher/1.0 (family safety)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        out = []
        for el in result.get("elements", []):
            tags = el.get("tags", {})
            stype = tags.get("shelter_type", tags.get("building", "shelter"))
            if stype in _SKIP_TYPES:
                continue
            slat = el.get("lat") or el.get("center", {}).get("lat")
            slon = el.get("lon") or el.get("center", {}).get("lon")
            if slat and slon:
                out.append({
                    "lat": slat, "lon": slon,
                    "name": tags.get("name:uk") or tags.get("name") or "",
                    "type": stype, "source": "osm", "address": "",
                })
        return out
    except Exception as e:
        log.warning(f"Overpass shelter query error: {e}")
        return []


def _nominatim_address(lat: float, lon: float) -> str:
    url = f"{NOMINATIM_URL}?lat={lat}&lon={lon}&format=json&accept-language=uk"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UAVWatcher/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
        addr = d.get("address", {})
        road = addr.get("road") or addr.get("pedestrian") or addr.get("street") or ""
        house = addr.get("house_number") or ""
        return f"{road} {house}".strip()
    except Exception:
        return ""


def _city_key_from_coords(lat: float, lon: float) -> str:
    """Груба прив'язка координат до ключа seed-файлу міста."""
    if 48.5 < lat < 48.8 and 33.0 < lon < 33.3:
        return "oleksandria"
    return ""


def _load_seed(city_key: str) -> list:
    f = SEED_DIR / f"shelters_seed_{city_key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(data: dict):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _geocode_street(street: str, user_lat: float, user_lon: float) -> tuple:
    """Forward geocode a street address near user coordinates. Returns (lat, lon) or None."""
    buf = 0.12  # ~13km bounding box
    viewbox = f"{user_lon - buf},{user_lat + buf},{user_lon + buf},{user_lat - buf}"
    params = urllib.parse.urlencode({
        "q": street,
        "format": "json",
        "limit": 1,
        "viewbox": viewbox,
        "bounded": 1,
        "accept-language": "uk",
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UAVWatcher/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        log.debug(f"Geocode failed for '{street}': {e}")
    return None


def _parse_ebot_response(text: str, user_lat: float, user_lon: float) -> list:
    """
    Parse @UkraineShelterStfalconBot response into shelter dicts.
    Tries GPS coords first; falls back to geocoding backtick-quoted addresses.
    """
    shelters = []
    coord_pats = [
        re.compile(r'[?&]q=(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'),
        re.compile(r'/maps/@(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'),
        re.compile(r'geo:(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'),
        re.compile(r'(?<!\d)(\d{2}\.\d{4,})[,\s]+(\d{2}\.\d{4,})(?!\d)'),
    ]
    blocks = re.split(r'\n(?=\d+[.)]\s)', text)
    if len(blocks) <= 1:
        blocks = re.split(r'\n\n+', text)
    if len(blocks) <= 1:
        blocks = [text]

    for i, block in enumerate(blocks):
        # 1. Try GPS coords
        for pat in coord_pats:
            m = pat.search(block)
            if not m:
                continue
            try:
                slat, slon = float(m.group(1)), float(m.group(2))
                if not (44 < slat < 53 and 22 < slon < 40):
                    continue
                am = re.search(
                    r'((?:вул\.?|пр\.?|пров\.?|бул\.?|просп\.?)\s+[\w\s\-,\.]+\d*)',
                    block, re.UNICODE
                )
                addr = am.group(1).strip() if am else ""
                nm = re.search(r'\d+[.)]\s*(.+?)(?:\n|$)', block)
                name = nm.group(1).strip()[:60] if nm else f"Укриття {i + 1}"
                shelters.append({
                    "lat": slat, "lon": slon,
                    "name": name, "address": addr,
                    "type": "shelter", "source": "ebot",
                })
                break
            except ValueError:
                continue
        else:
            # 2. No GPS — try backtick-quoted address: `вул. Перспективна, 14`
            backtick_addr = re.findall(r'`([^`]+)`', block)
            for addr_candidate in backtick_addr:
                if re.search(r'(?:вул|пр\.|просп|пров|бул|площа|набер)', addr_candidate, re.I):
                    coords = _geocode_street(addr_candidate, user_lat, user_lon)
                    if coords:
                        slat, slon = coords
                        # Extract shelter type hint from parentheses
                        hint_m = re.search(r'\(([^)]+)\)', block)
                        hint = hint_m.group(1) if hint_m else ""
                        name = f"Укриття ({hint})" if hint else "Укриття"
                        shelters.append({
                            "lat": slat, "lon": slon,
                            "name": name, "address": addr_candidate,
                            "type": "shelter", "source": "ebot",
                        })
                        log.info(f"Geocoded ebot address '{addr_candidate}' → {slat},{slon}")
                        break

    if not shelters:
        log.debug(f"ebot: could not extract shelters from: {text[:200]}")
    return shelters


async def fetch_from_ebot(user_client, lat: float, lon: float, timeout: int = 60) -> list:
    """
    Send GPS location to @UkraineShelterStfalconBot via userbot and parse shelter response.
    Sends /start first if no prior conversation history.
    Returns [] on timeout, error, or parse failure.
    """
    if user_client is None:
        return []
    try:
        from telethon.tl.functions.messages import SendMediaRequest
        from telethon.tl.types import InputMediaGeoPoint, InputGeoPoint

        _EBOT_USERNAMES = [
            "UkraineShelterStfalconBot",
            "shelter_ua_bot",
            "eshelterbot",
        ]
        peer = None
        for _uname in _EBOT_USERNAMES:
            try:
                peer = await user_client.get_input_entity(_uname)
                log.info(f"Resolved shelter bot as @{_uname}")
                break
            except Exception:
                continue
        if peer is None:
            log.warning("fetch_from_ebot: could not resolve any shelter bot username")
            return []

        history = await user_client.get_messages(peer, limit=3)
        last_id = history[0].id if history else 0

        # Send /start if no history or last outgoing message was a location (re-init)
        if not history:
            await user_client.send_message(peer, "/start")
            log.info("Sent /start to shelter bot (first contact)")
            await asyncio.sleep(2)
            # Record last_id again after /start response
            history = await user_client.get_messages(peer, limit=1)
            last_id = history[0].id if history else 0

        await user_client(SendMediaRequest(
            peer=peer,
            media=InputMediaGeoPoint(geo_point=InputGeoPoint(lat=lat, long=lon)),
            message="",
            random_id=random.randint(-(2**63), 2**63 - 1),
        ))
        log.info(f"Sent location to shelter bot: {lat}, {lon}")

        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(3)
            new_msgs = await user_client.get_messages(peer, limit=10, min_id=last_id)
            for msg in reversed(new_msgs):
                if not msg.out and msg.text:
                    shelters = _parse_ebot_response(msg.text, lat, lon)
                    log.info(f"ebot response received ({len(shelters)} shelters): {msg.text[:100]}")
                    return shelters

        log.warning(f"fetch_from_ebot: no response within {timeout}s")
        return []
    except Exception as e:
        log.warning(f"fetch_from_ebot error: {e}")
        return []


async def find_shelters_enhanced(user_client, lat: float, lon: float,
                                  radius_m: int = 5000, top_n: int = 5) -> list:
    """
    Async fallback chain: @e_shelter_bot → Overpass OSM → seed file.
    Results are cached for 24h.
    """
    cache_key = f"{round(lat, 3)}:{round(lon, 3)}"
    cache = _load_cache()
    entry = cache.get(cache_key)
    if entry and (time.time() - entry.get("ts", 0)) < CACHE_TTL:
        return _enrich_and_sort(list(entry["shelters"]), lat, lon, top_n)

    shelters = await fetch_from_ebot(user_client, lat, lon)

    if not shelters:
        loop = asyncio.get_event_loop()
        shelters = await loop.run_in_executor(None, _query_overpass, lat, lon, radius_m)

    if not shelters:
        city_key = _city_key_from_coords(lat, lon)
        if city_key:
            shelters = _load_seed(city_key)

    shelters = _enrich_and_sort(shelters, lat, lon, top_n * 2)
    cache[cache_key] = {"ts": time.time(), "shelters": shelters}
    _save_cache(cache)
    return _enrich_and_sort(list(shelters), lat, lon, top_n)


def _dedup_by_proximity(shelters: list, min_dist_m: int = 100) -> list:
    """Remove shelters that are within min_dist_m of a closer one (same location duplicates)."""
    kept = []
    for s in shelters:
        too_close = False
        for k in kept:
            if _haversine(s["lat"], s["lon"], k["lat"], k["lon"]) < min_dist_m:
                too_close = True
                break
        if not too_close:
            kept.append(s)
    return kept


def _enrich_and_sort(shelters: list, lat: float, lon: float, top_n: int) -> list:
    """Додати адреси, відстань, посилання; дедублікувати за відстанню; посортувати."""
    for s in shelters:
        if not s.get("address"):
            s["address"] = _nominatim_address(s["lat"], s["lon"])
        s["distance_m"] = _haversine(lat, lon, s["lat"], s["lon"])
        s["maps_link"] = f"https://maps.google.com/?q={s['lat']},{s['lon']}"
    shelters.sort(key=lambda x: x["distance_m"])
    shelters = _dedup_by_proximity(shelters)
    return shelters[:top_n]


def find_shelters_sync(lat: float, lon: float,
                       radius_m: int = 5000, top_n: int = 5) -> list:
    """
    Синхронна версія — для виклику з не-async контексту (Sharon/LangGraph).
    Повертає список dict: {name, address, lat, lon, distance_m, type, maps_link}
    """
    cache_key = f"{round(lat, 3)}:{round(lon, 3)}"
    cache = _load_cache()
    entry = cache.get(cache_key)
    if entry and (time.time() - entry.get("ts", 0)) < CACHE_TTL:
        shelters = entry["shelters"]
    else:
        shelters = _query_overpass(lat, lon, radius_m)
        if not shelters:
            city_key = _city_key_from_coords(lat, lon)
            shelters = _load_seed(city_key)
        shelters = _enrich_and_sort(shelters, lat, lon, top_n * 2)
        cache[cache_key] = {"ts": time.time(), "shelters": shelters}
        _save_cache(cache)
    return _enrich_and_sort(list(shelters), lat, lon, top_n)


async def find_shelters(lat: float, lon: float,
                        radius_m: int = 5000, top_n: int = 5) -> list:
    """Async версія — для /shelter команди і фонового refresh."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, find_shelters_sync, lat, lon, radius_m, top_n
    )


def format_shelters_for_chat(shelters: list) -> str:
    """Форматує список укриттів для Telegram. Координати вказані одразу."""
    if not shelters:
        return (
            "Укриттів в базі відкритих карт (OSM) для цього місця не знайдено.\n\n"
            "Знайди укриття:\n"
            "• Додаток «Є Укриття» (iOS / Android)\n"
            "• ДСНС: 101\n"
            "• Зараз: нижній поверх, 2 несучих стіни між тобою і вулицею, далі від вікон."
        )
    lines = ["Найближчі укриття:"]
    for i, s in enumerate(shelters, 1):
        d = s["distance_m"]
        dist_str = f"{d} м" if d < 1000 else f"{d / 1000:.1f} км"
        name = s.get("name") or "Укриття"
        addr = s.get("address") or ""
        lat, lon = s["lat"], s["lon"]
        line = f"{i}. {name}"
        if addr:
            line += f" — {addr}"
        line += f" ({dist_str})"
        line += f"\n   GPS: {lat:.5f}, {lon:.5f}"
        line += f"\n   {s['maps_link']}"
        lines.append(line)
    lines.append(
        "\n⚠️ Дані потребують верифікації.\n"
        "Перевір самостійно: @UkraineShelterStfalconBot, додаток «Є Укриття» або ДСНС 101."
    )
    return "\n".join(lines)


async def refresh_shelters_kb(project_root: str, city_lat: float, city_lon: float,
                               kb_path: str = None, user_client=None):
    """
    Оновити кеш укриттів міста і перезаписати секцію в KB-файлі 07-shelters.md.
    Викликається при старті і кожні 24 год.
    """
    shelters = await find_shelters_enhanced(user_client, city_lat, city_lon,
                                             radius_m=5000, top_n=20)
    if not kb_path:
        kb_path = os.path.join(project_root, "consultant", "knowledge", "07-shelters.md")

    if shelters:
        rows = []
        for s in shelters:
            d = s["distance_m"]
            dist_str = f"{d} м" if d < 1000 else f"{d / 1000:.1f} км"
            name = s.get("name") or "Укриття"
            addr = s.get("address") or ""
            rows.append(f"| {name} | {addr} | {dist_str} | {s['maps_link']} |")
        table = (
            "## Актуальні укриття (авто-оновлення)\n\n"
            "| Назва | Адреса | Відстань від центру | Карта |\n"
            "|-------|--------|---------------------|-------|\n"
            + "\n".join(rows)
        )
    else:
        table = (
            "## Актуальні укриття (авто-оновлення)\n\n"
            "Дані відсутні в OSM для цього міста. Використовуй додаток «Є Укриття» або ДСНС 101.\n"
        )

    try:
        content = Path(kb_path).read_text(encoding="utf-8")
        marker = "## Актуальні укриття"
        if marker in content:
            content = content[:content.index(marker)] + table + "\n"
        else:
            content = content.rstrip() + "\n\n" + table + "\n"
        Path(kb_path).write_text(content, encoding="utf-8")
        log.info(f"Shelter KB updated: {len(shelters)} entries → {kb_path}")
    except Exception as e:
        log.error(f"Shelter KB update error: {e}")
