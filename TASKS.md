# UAV-Watcher Tasks

[ ] TASK-83
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
