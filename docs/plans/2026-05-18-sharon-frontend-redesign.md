# Sharon Frontend Redesign Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Переписати frontend Sharon з inline-HTML-в-Python на підтримуваний SvelteKit SPA з власним дизайном.

**Architecture:** SvelteKit SPA (port 5173 dev / статика в dist/) + існуючий FastAPI consultant (:8770) як API backend. Python HTTP server (:8422) залишається для адмін-функцій або замінюється FastAPI роутами. Дизайн: "Tactical Operations Terminal" — темна тема, orange accent, Barlow Condensed + JetBrains Mono.

**Tech Stack:** SvelteKit 2, TypeScript, Vite, CSS Variables (no Tailwind — кастомна дизайн-система), EventSource для live feed.

---

## Поточний стан (аналіз)

| Параметр | Зараз | Ціль |
|----------|-------|------|
| Файл | `web_config.py` 3071 рядків inline HTML | SvelteKit компоненти |
| Реактивність | Форми + page reload | Svelte stores, live SSE |
| Дизайн | Хороший, але монолітний | Компонентний, той самий стиль |
| Мобільний | Частково | Bottom tab bar, bottom sheet |
| Chat panel | Fixed 380px slide | Responsive drawer |
| Maintainability | ❌ HTML in Python strings | ✅ .svelte files |

---

## Design System (Stitch DESIGN.md)

```css
--bg: #060810;
--surface: #0f172a;
--surface-low: #191b24;
--elevated: #0b0e16;
--border: #1e293b;
--border-focus: #38bdf8;
--text: #e1e1ee;
--muted: #a78b7d;
--dim: #6b7280;
--accent: #f97316;      /* L2 orange */
--primary: #ffb690;
--blue: #38bdf8;
--green: #10b981;       /* L0 calm */
--yellow: #eab308;      /* L1 regional */
--red: #f43f5e;         /* L3 explosion */

--font-display: 'Barlow Condensed', sans-serif;  /* headings, uppercase */
--font-mono: 'JetBrains Mono', monospace;        /* data, timestamps */

--radius: 2px;          /* sharp tactical corners */
--radius-sm: 2px;
--radius-md: 4px;
```

Threat level colors: L0 `--green`, L1 `--yellow`, L2 `--accent`, L3 `--red`

---

## Phase 1: Scaffold + Design System

### Task 1: SvelteKit project scaffold

**Files:**
- Create: `/home/vokov/projects/uav-watcher/frontend/` (new directory)
- Create: `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.ts`
- Create: `frontend/src/app.css` (design system variables)
- Create: `frontend/src/app.html`

**Step 1: Init SvelteKit**
```bash
cd /home/vokov/projects/uav-watcher
npm create svelte@latest frontend
# → Skeleton project, TypeScript, no additional libraries
cd frontend && npm install
```

**Step 2: Додати шрифти в `src/app.html`**
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

**Step 3: Написати `src/app.css`** з усіма CSS variables + базові reset стилі (body dot-grid background, font-smoothing).

**Step 4: Перевірити що dev сервер стартує**
```bash
npm run dev -- --host 0.0.0.0 --port 5173
# → http://192.168.3.184:5173 доступний
```

**Step 5: Commit**
```bash
git add frontend/
git commit -m "feat: scaffold SvelteKit frontend with design system"
```

---

### Task 2: Layout + Topbar компонент

**Files:**
- Create: `frontend/src/routes/+layout.svelte`
- Create: `frontend/src/lib/components/Topbar.svelte`
- Create: `frontend/src/lib/stores/status.ts`

**Step 1: `status.ts` store**
```typescript
import { writable } from 'svelte/store';
export const serviceStatus = writable<'ok' | 'err' | 'unknown'>('unknown');
export const threatLevel = writable<0 | 1 | 2 | 3>(0);
```

**Step 2: `Topbar.svelte`**
```svelte
<script lang="ts">
  import { serviceStatus } from '$lib/stores/status';
</script>

<header class="topbar">
  <div class="dot" />
  <span class="topbar-title">SHARON</span>
  <span class="topbar-sub">— система моніторингу загроз</span>
  <span class="status-pill" class:ok={$serviceStatus === 'ok'} class:err={$serviceStatus === 'err'}>
    {$serviceStatus === 'ok' ? 'ONLINE' : 'OFFLINE'}
  </span>
</header>
```

**Step 3: `+layout.svelte`** — topbar + slot + chat panel drawer.

**Step 4: Перевірити що layout рендериться без помилок**

**Step 5: Commit**

---

## Phase 2: Core Screens

### Task 3: Dashboard (Monitor) screen

**Files:**
- Create: `frontend/src/routes/+page.svelte`
- Create: `frontend/src/lib/components/ThreatCard.svelte`
- Create: `frontend/src/lib/components/ChannelFeed.svelte`
- Create: `frontend/src/lib/components/StatsRow.svelte`

**ThreatCard.svelte:**
```svelte
<script lang="ts">
  export let level: 0 | 1 | 2 | 3 = 0;
  const labels = ['СПОКІЙНО', 'РЕГІОНАЛЬНА', 'МІСТО', 'ПРЯМА ЗАГРОЗА'];
  const colors = ['var(--green)', 'var(--yellow)', 'var(--accent)', 'var(--red)'];
</script>

<div class="card threat-card" style="--level-color: {colors[level]}">
  <div class="threat-level">{level}</div>
  <div class="threat-label">{labels[level]}</div>
  <div class="threat-bar">
    <div class="threat-fill" style="width: {(level / 3) * 100}%" />
  </div>
</div>
```

**ChannelFeed.svelte** — SSE підключення до `/feed/recent`:
```typescript
// src/lib/api.ts
const CONSULTANT_URL = 'http://localhost:8770'; // або проксований через SvelteKit

export async function fetchFeed(limit = 20) {
  const res = await fetch(`${CONSULTANT_URL}/feed/recent?limit=${limit}`);
  return res.json();
}
```

Polling кожні 30с (EventSource якщо додамо SSE endpoint до consultant).

**Step: Перевірити що dashboard рендериться з mock даними**

---

### Task 4: Chat Panel (Sharon AI)

**Files:**
- Create: `frontend/src/lib/components/ChatPanel.svelte`
- Create: `frontend/src/lib/stores/chat.ts`

**chat.ts store:**
```typescript
export interface Message {
  role: 'user' | 'bot';
  text: string;
  ts: number;
}
export const messages = writable<Message[]>([]);
export const chatOpen = writable(false);
```

**ChatPanel.svelte** — slide-in drawer (translateX на desktop, translateY на mobile), chips для швидких питань, textarea + send button.

API call до `POST /chat`:
```typescript
async function sendMessage(text: string) {
  const res = await fetch('http://localhost:8770/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text, session_id: sessionId })
  });
  const data = await res.json();
  // append to messages store
}
```

**Quick chips:** "Як обстановка?", "Де укриття?", "Що робити при тривозі?"

---

### Task 5: Channel Management screen

**Files:**
- Create: `frontend/src/routes/channels/+page.svelte`
- Create: `frontend/src/lib/components/ChannelRow.svelte`

Table-based layout: назва каналу, посилання, статус, кнопки delete/toggle.
Форма додавання нового каналу (POST до `web_config.py` або нового API endpoint).

---

### Task 6: Shelter screen (mobile-first)

**Files:**
- Create: `frontend/src/routes/shelter/+page.svelte`
- Create: `frontend/src/lib/components/ShelterList.svelte`
- Create: `frontend/src/lib/components/LocationButton.svelte`

**LocationButton** → `navigator.geolocation.getCurrentPosition()` → POST до consultant `/chat` з координатами.

**ShelterList** — bottom sheet на mobile, sidebar на desktop. Картки з адресою + відстанню.

---

### Task 7: Mobile navigation

**Files:**
- Create: `frontend/src/lib/components/BottomNav.svelte`

```svelte
<nav class="bottom-nav">
  <a href="/" class:active={$page.url.pathname === '/'}>
    <span class="nav-icon">📡</span>
    <span>Монітор</span>
  </a>
  <a href="/channels">
    <span class="nav-icon">📢</span>
    <span>Канали</span>
  </a>
  <a href="/shelter">
    <span class="nav-icon">🏠</span>
    <span>Укриття</span>
  </a>
  <button onclick={() => $chatOpen = !$chatOpen}>
    <span class="nav-icon">🐱</span>
    <span>Шарон</span>
  </button>
</nav>
```

Видимий тільки на `@media (max-width: 768px)`.

---

## Phase 3: Integration + Deploy

### Task 8: SvelteKit proxy до consultant API

**`vite.config.ts`** — proxy щоб уникнути CORS:
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8770',
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

Всі fetch викликим змінити на `/api/chat`, `/api/feed/recent`, `/api/health`.

### Task 9: Build + serve як статика

**Step 1:** Додати `@sveltejs/adapter-static` в `svelte.config.js`

**Step 2:** Build
```bash
cd frontend && npm run build
# → frontend/build/ (статичні файли)
```

**Step 3:** Оновити `web_config.py` або додати FastAPI static files mount:
```python
# в consultant/main.py
from fastapi.staticfiles import StaticFiles
app.mount("/ui", StaticFiles(directory="../frontend/build", html=True), name="ui")
```

**Step 4:** Доступний на `http://192.168.3.184:8770/ui`

**Step 5: Commit + push**

---

## Пріоритети

```
ЦЬОГО ТИЖНЯ:  Task 1-3 (scaffold + dashboard)
НАСТУПНИЙ:    Task 4-5 (chat + channels)
ПОТІМ:        Task 6-7 (shelter + mobile nav)
ЗАВЕРШЕННЯ:   Task 8-9 (integration + deploy)
```

## Паралельно з поточним

Python `web_config.py` (:8422) **залишається** і продовжує працювати до повної готовності SvelteKit версії. Перемикання — один рядок в конфігу Cloudflare/reverse proxy.

---

## Stitch Prompt (для генерації дизайну)

Зберігається окремо в `docs/plans/2026-05-18-sharon-frontend-stitch-prompt.md`.
