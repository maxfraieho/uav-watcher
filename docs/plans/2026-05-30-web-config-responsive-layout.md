# Web-Config Responsive Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the web-config responsive layout so LLM proxy rows do not overflow on mobile screen sizes.

**Architecture:** Modify `web_config.py`'s `renderProxies()` JS generator to output a two-row mobile-friendly layout card for each proxy, and update `.card` CSS styling to allow visible overflow, while preventing overflow in `.card-header`.

**Tech Stack:** Python (HTML/JS generator), HTML, CSS, JavaScript.

---

### Task 1: Check Git Status and Pull Latest

**Files:**
- None

**Step 1: Check current git status and pull**

Run:
```bash
cd /data/data/com.termux/files/home/projects/uav-watcher
git status
git pull
```
Expected: Repository is clean, pull succeeds.

---

### Task 2: Modify `renderProxies()` in `web_config.py`

**Files:**
- Modify: `web_config.py` (around line 2592)

**Step 1: Locate the existing `el.innerHTML +=` block in `renderProxies()`**

Look for the block beginning with:
```javascript
el.innerHTML += '<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">' +
```
Ensure it matches the targets to be replaced.

**Step 2: Replace with two-row card structure**

Replace that block with:
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

---

### Task 3: Modify CSS `.card` and `.card-header` in `web_config.py`

**Files:**
- Modify: `web_config.py` (around line 1183 and `.card-header` section)

**Step 1: Locate `.card` style**
Find:
```css
border-radius: 2px; overflow: hidden;
```
inside `.card { ... }`.

**Step 2: Replace with visible overflow**
Change to:
```css
border-radius: 2px; overflow: visible;
```

**Step 3: Update `.card-header` to have hidden overflow**
Find `.card-header {` block, and add `overflow: hidden;` and `border-radius: 2px 2px 0 0;` if not already present.

---

### Task 4: Copy to Server, Restart and Verify

**Files:**
- None

**Step 1: Copy `web_config.py` to Server**
Run:
```bash
scp /data/data/com.termux/files/home/projects/uav-watcher/web_config.py vokov@192.168.3.184:/home/vokov/projects/uav-watcher/web_config.py
```

**Step 2: Restart Web Config Service on Server**
Run:
```bash
sshpass -p '805235io.' ssh vokov@192.168.3.184 'sudo rc-service uav-web-config restart'
```

**Step 3: Verify the site is responsive/active**
Run:
```bash
curl -s http://192.168.3.184:8422/ | grep -c "proxy-list"
```
Expected: output is `1` (or greater).

---

### Task 5: Commit, Diary, Tasks Update, and Push

**Files:**
- Modify: `TASKS.md`

**Step 1: Git Commit local changes**
Run:
```bash
git add web_config.py
git commit -m "fix(web-config): responsive LLM proxy rows — fix overflow on mobile (TASK-83)"
```

**Step 2: Update TASKS.md**
Mark `[x] TASK-83` as completed.
Commit:
```bash
git add TASKS.md
git commit -m "chore: mark TASK-83 as complete"
```

**Step 3: Push changes**
Run:
```bash
git push origin main
```

**Step 4: Write Diary entry**
Run:
```bash
python3 -m mempalace diary write --agent agt-ogy3 'SESSION:2026-05-30|TASK-83:web-config-responsive-proxy|commit:<commit-hash>|fix:renderProxies-2row-layout+card-overflow-visible|★★★'
```
