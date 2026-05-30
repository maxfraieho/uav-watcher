# UAV-Watcher Tasks

[x] TASK-83
## Fix: web-config responsive layout — LLM proxy rows overflow on mobile

### Проблема
`renderProxies()` (~рядок 2592 в web_config.py) рендерить рядок з 4 інпутами:
- Назва (width:100px)
- URL (flex:1)
- Token (width:120px)
- Модель (width:150px)
- 3 кнопки вгору/вниз/видалити

Рядок `display:flex` БЕЗ `flex-wrap` → загальна ширина ~600px+.
`.card { overflow:hidden }` обрізає всі елементи справа.
На мобільному (< 768px) Token, Модель і кнопки недоступні.

### Що виправити

**Файл:** `/home/vokov/projects/uav-watcher/web_config.py`

**1. Функція `renderProxies()` (~рядок 2592):**

Знайди рядок (починається з):
```
el.innerHTML += '<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">' +
```

Замінити весь блок `el.innerHTML +=` (від `<div style="display:flex` до кінця `'</div>'`) на
двострокову картку:

```javascript
el.innerHTML +=
  '<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:2px">' +
    '<div style="display:flex;gap:6px;align-items:center">' +
      '<span style="color:#888;font-size:11px;min-width:22px;flex-shrink:0">#'+(i+1)+'</span>' +
      '<input class="ch-input" placeholder="Назва" value="'+escHtml(p.name||'')+'" oninput="_proxies['+i+'].name=this.value;syncProxies()" style="width:90px;flex-shrink:0;font-size:12px;padding:7px 10px">' +
      '<input class="ch-input" placeholder="URL (https://...)" value="'+escHtml(p.url||'')+'" oninput="_proxies['+i+'].url=this.value;syncProxies()" style="flex:1;min-width:0;font-size:12px;padding:7px 10px">' +
    '</div>' +
    '<div style="display:flex;gap:6px;align-items:center">' +
      '<span style="min-width:22px;flex-shrink:0"></span>' +
      '<input class="ch-input" placeholder="Token" value="'+escHtml(p.token||'')+'" oninput="_proxies['+i+'].token=this.value;syncProxies()" style="flex:1;min-width:0;font-size:12px;padding:7px 10px">' +
      '<input class="ch-input" placeholder="Модель" value="'+escHtml(p.model||'')+'" oninput="_proxies['+i+'].model=this.value;syncProxies()" style="width:140px;flex-shrink:0;font-size:12px;padding:7px 10px">' +
      '<button type="button" onclick="moveProxy('+i+',-1)" style="background:var(--surface-low);color:var(--dim);border:1px solid var(--border);border-radius:2px;padding:5px 9px;cursor:pointer;flex-shrink:0" title="Вгору">↑</button>' +
      '<button type="button" onclick="moveProxy('+i+',1)" style="background:var(--surface-low);color:var(--dim);border:1px solid var(--border);border-radius:2px;padding:5px 9px;cursor:pointer;flex-shrink:0" title="Вниз">↓</button>' +
      '<button type="button" onclick="removeProxy('+i+')" style="background:transparent;color:#f87171;border:1px solid #991b1b;border-radius:2px;padding:5px 9px;cursor:pointer;flex-shrink:0">✕</button>' +
    '</div>' +
  '</div>';
```

**2. CSS `.card` (~рядок 1183):**

Знайди:
```
border-radius: 2px; overflow: hidden;
```
(в блоці `.card {`)

Замінити рядок `border-radius: 2px; overflow: hidden;` на:
```
border-radius: 2px; overflow: visible;
```

Потім знайди `.card-header {` і додай `overflow: hidden;` до його стилів:
```css
.card-header {
    /* existing styles... */
    overflow: hidden;
    border-radius: 2px 2px 0 0;
}
```

Перевір що `.card-header` вже є в CSS та дописати `overflow: hidden;` до нього.

### Верифікація
```bash
# SSH до 192.168.3.184:
sudo rc-service uav-web-config restart
curl -s http://localhost:8422/ | grep -c "proxy-list"
# Має бути 1 (означає сторінка генерується)
```

Відкрий http://192.168.3.184:8422 секцію "AI / LLM Proxy" —
проксі-рядки мають відображатись у 2 рядки і повністю вміщатись на вузькому екрані.

### Коміт
```
fix(web-config): responsive LLM proxy rows — fix overflow on mobile (TASK-83)
```

### Diary
```
SESSION:2026-05-30|TASK-83:web-config-responsive-proxy|commit:<hash>|fix:renderProxies-2row-layout+card-overflow-visible|★★★
```

### !!IMPORTANT!! Де запускати
1. Клонуй або pull репо на AGY3 Termux:
   `cd ~/projects/uav-watcher && git pull`
2. Редагуй web_config.py ЛОКАЛЬНО на AGY3
3. Скопіюй на сервер:
   `scp web_config.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/web_config.py`
4. SSH до 192.168.3.184:
   `sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-web-config restart'`
5. git commit + push від імені AGY3


## [x] TASK-85

**Sharon не сповіщає про повітряну тривогу**

### Проблема
`sharon/pipelines/threat_classifier.py` → `assess_severity` не обробляє "повітряна тривога".
Коли повідомлення містить "повітряна тривога в Олександрійський район" або "Кіровоградська область ПОВІТРЯНА ТРИВОГА":
- `threat_type = "Невідомо"` (немає Шахед/Ракета/Балістика)
- `city = "олександрія"` NOT in "олександрійський" (рядок не співпадає)
- `score = 1` → severity = "LOW" → `decide_alert` → END → **сповіщення не надсилається**

### Файл для зміни
`sharon/pipelines/threat_classifier.py`

### Що змінити
В функції `assess_severity` (приблизно рядок 155), **після** блоку:
```python
    for m in ["над містом", "над нами", "над районом", "низько", "поряд", "поруч", "напрямок міста"]:
        if m in text_lower:
            score += 3
            break
```
**Перед** рядком `severity = "LOW"` — вставити:

```python
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

```

**Старий код** (для пошуку точного місця вставки):
```python
            break

    severity = "LOW"
```

**Новий код**:
```python
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
```

### Верифікація
```bash
# SSH до 192.168.3.184:
python3 -c "
text = 'Кіровоградська область ПОВІТРЯНА ТРИВОГА'
text_lower = text.lower()
cfg = {'city': 'Олександрія', 'city_region': 'Кіровоградська область', 'city_keywords': ['Олександрія', 'Олександрійськ', 'Кіровоградщина']}
city = cfg.get('city', '').lower()
score = 1
_airraid_kw = ['повітряна тривог', 'оголошено тривог', 'тривогу оголош']
if any(k in text_lower for k in _airraid_kw):
    city_root = city[:7] if len(city) >= 7 else city
    region_lower = cfg.get('city_region', '').lower()
    hit = city in text_lower or city_root in text_lower or (region_lower and region_lower in text_lower)
    if hit:
        score = max(score, 4)
print('score:', score, '-> MEDIUM' if score >= 4 else '-> LOW FAIL!')
"

# Після перезапуску сервісу — дочекатись тривоги або вручну через logs:
tail -20 /var/log/uav-watcher.log
```
Має бути `score: 4 -> MEDIUM`.

### Деплой
```bash
# Після редагування файлу на AGY3:
scp sharon/pipelines/threat_classifier.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/sharon/pipelines/threat_classifier.py
sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-watcher restart'
```

### Коміт
```
fix(threat-classifier): assess_severity handles air raid alerts for monitored region (TASK-85)
```

### Diary
```
SESSION:2026-05-30|TASK-85:airraid-severity-fix|commit:<hash>|fix:assess_severity+airraid_kw+city_root+score>=4->MEDIUM|★★★
```

### !!IMPORTANT!! Де запускати
1. Клонуй або pull репо на AGY3 Termux:
   `cd ~/projects/uav-watcher && git pull`
2. Редагуй `sharon/pipelines/threat_classifier.py` ЛОКАЛЬНО на AGY3
3. Скопіюй на сервер:
   `scp sharon/pipelines/threat_classifier.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/sharon/pipelines/threat_classifier.py`
4. SSH до 192.168.3.184:
   `sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-watcher restart'`
5. git commit + push від імені AGY3


## [ ] TASK-86

**catchup не оновлює _active_threat після пропущеного відбою**

### Проблема
При рестарті watcher-а `_catchup_history()` знаходить пропущені події і зберігає в БД,
але НЕ відправляє сповіщення і НЕ оновлює `_active_threat`.

Сценарій (трапився 2026-05-30):
1. 18:15:58 — відбій Олександрійського району в Суспільне Кропивницький
2. 18:16:07 — сервіс перезапустився (через 9 сек!)
3. 18:16 catchup: знайшов відбій, зберіг у БД → але `_active_threat` залишився True
4. Наступні відбої не надсилаються (cooldown або стан не оновлено)

### Файл для зміни
`uav_watcher.py` — функція `_catchup_history()` (рядки ~672-714)

### Що змінити

Після поточного головного циклу (що зберігає події в БД), додати другий прохід:
якщо catchup знайшов all-clear для моніторованого міста та `_active_threat=True` →
оновити стан без відправки сповіщення (щоб не спамити).

Якщо catchup знайшов threshold-подію (тривога) і `_active_threat=False` →
відправити ОДНЕ запізніле сповіщення (з відміткою "(запізніло)").

**Старий код** (кінець функції `_catchup_history`, рядок ~711-713):
```python
            except Exception as _ce:
                log.warning(f"[catchup] channel {ch_id}: {_ce}")
        log.info(f"[catchup] Done. Inserted {total} missed events.")
```

**Новий код** (замінити останній рядок функції):
```python
            except Exception as _ce:
                log.warning(f"[catchup] channel {ch_id}: {_ce}")
        log.info(f"[catchup] Done. Inserted {total} missed events.")

        # --- Sync _active_threat from missed events ---
        global _active_threat
        cutoff_sync = _time.time() - 2 * 3600  # check last 2h
        had_threat = False
        had_allclear = False
        last_threat_text = ""
        last_threat_ch = ""

        for ch_id in channels:
            try:
                async for msg in client.iter_messages(ch_id, limit=100):
                    if not msg.text:
                        continue
                    if msg.date.timestamp() < cutoff_sync:
                        break
                    txt = msg.text
                    is_ac = bool(_ALLCLEAR_PATTERNS.search(txt)) and bool(_allclear_pattern.search(txt))
                    is_th = bool(region_pattern_search(txt)) and not _ALLCLEAR_PATTERNS.search(txt)
                    if is_ac:
                        had_allclear = True
                    elif is_th and not had_allclear:
                        had_threat = True
                        last_threat_text = txt
                        try:
                            chat = await client.get_entity(ch_id)
                            last_threat_ch = getattr(chat, "title", str(ch_id))
                        except Exception:
                            last_threat_ch = str(ch_id)
            except Exception:
                pass

        if had_allclear and _active_threat:
            log.info("[catchup] Missed all-clear detected → _active_threat=False")
            _active_threat = False
            _save_threat_state(False)
        elif had_threat and not _active_threat and last_threat_text:
            log.warning(f"[catchup] Missed threat detected → sending late notification")
            await send_notification(
                last_threat_text + "\n\n_(сповіщення запізнилось — watcher перезапускався)_",
                "пропущена загроза",
                cfg,
                channel_name=last_threat_ch,
            )
```

**ВАЖЛИВО:** `region_pattern_search` — це функція яка вже є в scope (глобальна або closure).
Перевір що ця функція доступна з `_catchup_history`. Якщо ні — використай:
```python
is_th = bool(_THREAT_PATTERNS.search(txt)) or any(k in txt.lower() for k in ["тривога", "бпла", "ракет"])
```

### Верифікація
```bash
# SSH до 192.168.3.184, перезапустити сервіс і перевірити лог:
sudo rc-service uav-watcher restart
sleep 5
tail -20 /var/log/uav-watcher.log | grep -E '(catchup|active_threat|Inserted)'
# Має бути "[catchup] Done. Inserted N missed events." без помилок
```

Також перевірити що синтаксично правильно:
```bash
cd /home/vokov/projects/uav-watcher
python3 -c "import uav_watcher; print('syntax OK')" 2>&1 | head -5
```

### Деплой
```bash
scp uav_watcher.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/uav_watcher.py
sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-watcher restart'
```

### Коміт
```
fix(catchup): sync _active_threat from missed all-clears on restart (TASK-86)
```

### Diary
```
SESSION:2026-05-30|TASK-86:catchup-allclear-sync|commit:<hash>|fix:_catchup_history+allclear-state-sync+late-threat-notify|★★★
```

### !!IMPORTANT!! Де запускати
1. ЛОКАЛЬНО на AGY3 Termux:
   `cd ~/projects/uav-watcher && git pull`
2. Редагуй `uav_watcher.py` локально на AGY3
3. Перевір синтаксис: `python3 -m py_compile uav_watcher.py && echo OK`
4. Скопіюй на сервер:
   `scp uav_watcher.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/uav_watcher.py`
5. SSH до сервера:
   `sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-watcher restart && sleep 3 && tail -10 /var/log/uav-watcher.log'`
6. git commit + push від імені AGY3
