"""
geo_monitor.py â Dynamic region pattern builder.
Reads all current family locations from DB, queries Overpass API for
settlements within radius_m, builds a combined regex pattern.
"""
import asyncio
import logging
import re
import time
import urllib.parse
import urllib.request
import json

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RADIUS_M = 30_000  # 30 km
CACHE_TTL = 3600   # 1 hour per location bucket

# Cache: {(rounded_lat, rounded_lon): {"ts": float, "names": [str]}}
_settlement_cache: dict = {}
_cache_lock = asyncio.Lock()


def _round_coords(lat: float, lon: float, precision: int = 2) -> tuple:
    """Round coordinates to ~1km grid for cache key."""
    return (round(lat, precision), round(lon, precision))


async def fetch_settlements(lat: float, lon: float) -> list[str]:
    """Return settlement names within RADIUS_M of (lat, lon). Cached."""
    key = _round_coords(lat, lon)

    async with _cache_lock:
        cached = _settlement_cache.get(key)
        if cached and (time.monotonic() - cached["ts"]) < CACHE_TTL:
            return cached["names"]

    # Run blocking HTTP in thread pool
    loop = asyncio.get_event_loop()
    names = await loop.run_in_executor(None, _query_overpass, lat, lon)

    async with _cache_lock:
        _settlement_cache[key] = {"ts": time.monotonic(), "names": names}

    log.info(f"Overpass: {len(names)} settlements within {RADIUS_M//1000}km of ({lat:.4f},{lon:.4f})")
    return names



def _query_overpass(lat: float, lon: float) -> list[str]:
    """Blocking Overpass API call."""
    query = f"""
[out:json][timeout:20];
(
  node["place"~"^(city|town|village|hamlet|suburb)$"]["name"](around:{RADIUS_M},{lat},{lon});
  way["place"~"^(city|town|village|hamlet|suburb)$"]["name"](around:{RADIUS_M},{lat},{lon});
);
out tags;
"""
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(
            OVERPASS_URL, data=data,
            headers={"User-Agent": "UAVWatcher/1.0 (family safety)"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            result = json.loads(resp.read())

        names = set()
        for el in result.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name:uk") or tags.get("name")
            if name and len(name) >= 3:
                names.add(name.strip())
        return sorted(names)
    except Exception as e:
        log.warning(f"Overpass error for ({lat},{lon}): {e}")
        return []


def get_all_active_locations(db_path: str, max_age_hours: int = 8) -> list[tuple]:
    """
    Return (lat, lon) pairs for all location check-ins updated within max_age_hours.
    """
    import sqlite3
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT lat, lon FROM location_checkins WHERE updated_at >= ?",
            (cutoff,)
        ).fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows if r[0] and r[1]]
    except Exception as e:
        log.warning(f"DB location query error: {e}")
        return []


async def build_pattern_from_locations(
    db_path: str,
    base_keywords: list[str],
) -> re.Pattern:
    """
    Build a combined regex pattern from:
    - base_keywords (city name + city_keywords from config)
    - All settlements within 30km of any active family member location
    Returns the compiled Pattern.
    """
    locations = get_all_active_locations(db_path)
    log.info(f"Dynamic geo: {len(locations)} active member location(s) found")

    all_names: set[str] = set(base_keywords)

    if locations:
        tasks = [fetch_settlements(lat, lon) for lat, lon in locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_names.update(r)

    if not all_names:
        # Fallback: base keywords only
        log.warning("No locations found, using base_keywords only")
        all_names = set(base_keywords)

    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(all_names) if k),
        re.IGNORECASE | re.UNICODE,
    )
    log.info(f"Dynamic region pattern: {len(all_names)} terms")
    return pattern
