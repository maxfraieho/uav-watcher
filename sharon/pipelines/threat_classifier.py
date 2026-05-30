import os
import json
import logging
import time
import httpx
import re
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

log = logging.getLogger(__name__)

PROJECT_ROOT = "/home/vokov/projects/uav-watcher"
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")

class ThreatState(TypedDict):
    text: str
    threat_type: str       # Шахед, Ракета, Балістика, Розвідник, Невідомо
    region: str
    time: str
    severity: str          # LOW, MEDIUM, HIGH, CRITICAL
    formatted_text: str
    job_id: str
    error: Optional[str]

def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"[Sharon Pipeline] Failed to load config: {e}")
        return {}

def log_trace(job_id: str, node_name: str, event_type: str, data: dict = None):
    if not job_id:
        return
    trace_file = os.path.join(PROJECT_ROOT, "data", f"trace_{job_id}.jsonl")
    try:
        os.makedirs(os.path.dirname(trace_file), exist_ok=True)
        event = {
            "timestamp": time.time(),
            "event": event_type,
            "node": node_name,
            "data": data or {}
        }
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        log.error(f"[Sharon Pipeline] Failed to log trace for job {job_id}: {e}")

async def extract_entities(state: ThreatState) -> ThreatState:
    job_id = state.get("job_id", "")
    log_trace(job_id, "extract_entities", "node_start")
    text = state.get("text", "")

    threat_type = "Невідомо"
    region = ""
    event_time = time.strftime("%H:%M")

    text_lower = text.lower()
    if any(k in text_lower for k in ["шахед", "shahed", "бпла", "дрон", "мопед"]):
        threat_type = "Шахед"
    elif any(k in text_lower for k in ["крилат", "ракет", "калібр", "х-101"]):
        threat_type = "Ракета"
    elif any(k in text_lower for k in ["баліст", "іскандер", "кинджал", "с-300"]):
        threat_type = "Балістика"
    elif any(k in text_lower for k in ["розвід", "орлан", "суперкам"]):
        threat_type = "Розвідник"

    time_match = re.search(r"\b([0-1]?[0-9]|2[0-3])[:.][0-5][0-9]\b", text)
    if time_match:
        event_time = time_match.group(0).replace(".", ":")

    cfg = load_config()
    _llm_url = cfg.get("llm_proxy_url") or cfg.get("goclaw_url", "")
    _llm_key = cfg.get("llm_proxy_token") or cfg.get("goclaw_api_key", "")
    _llm_model = cfg.get("llm_proxy_model") or cfg.get("goclaw_model", "")

    _proxy_list = cfg.get("llm_proxies")
    if _proxy_list and isinstance(_proxy_list, list):
        _proxies = [{"url": p["url"].rstrip("/") + "/chat/completions",
                     "token": p.get("token", "not-needed"),
                     "model": p.get("model", _llm_model or "gemini-2.5-flash"),
                     "name": p.get("name", p["url"])} for p in _proxy_list if p.get("url")]
    elif _llm_url:
        _url = _llm_url.rstrip("/")
        if not _url.endswith("/chat/completions"): _url += "/chat/completions"
        _proxies = [{"url": _url, "token": _llm_key,
                     "model": _llm_model or "gemini-2.5-flash", "name": "single"}]
    else:
        _proxies = []

    if _proxies:
        prompt = (
            "Ти — Sharon, інтелектуальний аналітик загроз UAV та ракетних атак в Україні.\n"
            "Тобі надано текст повідомлення з моніторингового каналу.\n"
            "Витягни наступні сутності та поверни результат СУВОРО в форматі JSON без маркдауну та зайвого тексту:\n"
            "{\n"
            "  \"threat_type\": \"Шахед\" | \"Ракета\" | \"Балістика\" | \"Розвідник\" | \"Невідомо\",\n"
            "  \"region\": \"назва області, міста або району України\",\n"
            "  \"time\": \"час події у форматі HH:MM (якщо вказано, інакше поточний час)\"\n"
            "}\n\n"
            f"Текст повідомлення: \"{text}\""
        )

        for _p in _proxies:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        _p["url"],
                        headers={
                            "Authorization": f"Bearer {_p['token']}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": _p["model"],
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 150,
                            "temperature": 0,
                        },
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
                    result = json.loads(content)

                    threat_type = result.get("threat_type", threat_type)
                    region = result.get("region", region)
                    event_time = result.get("time", event_time)
                    break
            except Exception as e:
                log.warning(f"[threat_classifier] proxy {_p['name']} failed: {e}")

    if not region:
        region = cfg.get("city_region", "")

    state["threat_type"] = threat_type
    state["region"] = region
    state["time"] = event_time

    log_trace(job_id, "extract_entities", "node_done", {
        "threat_type": threat_type,
        "region": region,
        "time": event_time
    })
    return state

async def assess_severity(state: ThreatState) -> ThreatState:
    job_id = state.get("job_id", "")
    log_trace(job_id, "assess_severity", "node_start")
    text = state.get("text", "")
    text_lower = text.lower()

    cfg = load_config()
    city = cfg.get("city", "Олександрія").lower()

    score = 1
    # Boost score if LLM already identified a real threat type
    if state.get("threat_type", "Невідомо") != "Невідомо":
        score += 2
    if city in text_lower:
        score += 3
    for m in ["над містом", "над нами", "над районом", "низько", "поряд", "поруч", "напрямок міста"]:
        if m in text_lower:
            score += 3
            break

    # Air raid alert in monitored region/city -> at minimum MEDIUM
    _airraid_kw = ["повітряна тривог", "оголошено тривог", "тривогу оголош"]
    if any(k in text_lower for k in _airraid_kw):
        city_keywords = cfg.get("city_keywords", [city])
        region_lower = cfg.get("city_region", "").lower()
        city_root = city[:7] if len(city) >= 7 else city  # handles adjective forms: "олексан" -> "олександрійськ"
        _airraid_hit = (
            city in text_lower
            or city_root in text_lower
            or (region_lower and region_lower in text_lower)
            or any(kw.lower() in text_lower for kw in city_keywords)
        )
        if _airraid_hit:
            score = max(score, 4)  # MEDIUM: air raid alert for monitored region

    severity = "LOW"

    if any(k in text_lower for k in ["вибух", "прильот", "влучання", "удар", "бахнув", "бах"]) and (city in text_lower or "над нами" in text_lower):
        severity = "CRITICAL"
    elif score >= 6 or any(k in text_lower for k in ["над містом", "прямо над", "курсом на", "підлітає до"]) and (city in text_lower or "місто" in text_lower):
        severity = "HIGH"
    elif score >= 4 or any(k in text_lower for k in ["рух бпла", "напрямок", "вектор", "в напрямку"]):
        severity = "MEDIUM"
    else:
        severity = "LOW"

    if any(k in text_lower for k in ["відбій", "чисто", "скасовано"]):
        severity = "LOW"

    state["severity"] = severity
    log_trace(job_id, "assess_severity", "node_done", {"severity": severity})
    return state

def decide_alert(state: ThreatState) -> str:
    severity = state.get("severity", "LOW")
    if severity in ["MEDIUM", "HIGH", "CRITICAL"]:
        return "format_message"
    return END

async def format_message(state: ThreatState) -> ThreatState:
    job_id = state.get("job_id", "")
    log_trace(job_id, "format_message", "node_start")

    threat_type = state.get("threat_type", "Невідомо")
    region = state.get("region", "")
    event_time = state.get("time", "")
    severity = state.get("severity", "LOW")

    cfg = load_config()
    city = cfg.get("city", "ВашеМісто").upper()

    if severity == "CRITICAL":
        header = f"🔴 КРИТИЧНА ЗАГРОЗА — {city}"
        action = "Негайно перейдіть в укриття або скористайтеся правилом двох стін! Зафіксовано вибухи чи безпосередній обстріл!"
    elif severity == "HIGH":
        header = f"🚨 ВИСОКА ЗАГРОЗА — {city}"
        action = "Загроза безпосередньо над містом або підлітає. Перебувайте в безпечних місцях!"
    else:
        header = f"⚠️ УВАГА — {city} (МОНІТОРИНГ)"
        action = "Будьте уважні та стежте за офіційними повідомленнями."

    formatted_text = (
        f"{header}\n\n"
        f"Тип загрози: {threat_type}\n"
        f"Регіон: {region}\n"
        f"Час фіксації: {event_time}\n\n"
        f"Рекомендовані дії: {action}"
    )

    state["formatted_text"] = formatted_text
    log_trace(job_id, "format_message", "node_done", {"formatted_text": formatted_text})
    return state

def build_graph():
    g = StateGraph(ThreatState)
    g.add_node("extract_entities", extract_entities)
    g.add_node("assess_severity", assess_severity)
    g.add_node("format_message", format_message)

    g.set_entry_point("extract_entities")
    g.add_edge("extract_entities", "assess_severity")
    g.add_conditional_edges(
        "assess_severity",
        decide_alert,
        {
            "format_message": "format_message",
            END: END
        }
    )
    g.add_edge("format_message", END)
    return g.compile()

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
