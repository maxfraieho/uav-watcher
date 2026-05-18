# Sharon — Stitch Prompt для дизайну фронтенду

> Використовуй на https://stitch.withgoogle.com

## Головний промпт (вставити в Stitch)

```
Design a crisis monitoring dashboard called "Sharon" for Ukrainian city emergency coordinators. 
Dark military/tactical aesthetic. Orange accent (#f97316). Background #060810.

TARGET USER: City emergency coordinator who monitors real-time UAV/missile threats 
across 5+ Telegram channels and needs instant situational awareness.

MAIN SCREEN — Dashboard layout (desktop + mobile):
- Top bar: "SHARON" logo with pulsing orange dot (status indicator), service status pill 
  (ONLINE/OFFLINE), language switcher (emoji flags)
- Left sidebar (collapsible): Navigation with icons — Monitor, Channels, AI Settings, 
  Shelter Map, System
- Main content area: 
  * Threat level card (4 levels: 0=calm green, 1=yellow regional, 2=orange city, 
    3=red explosion) — large bold number + status text + progress bar
  * Live channel feed — scrolling card with timestamps, channel names, message snippets, 
    color-coded by threat level
  * Quick stats row: channels monitored, messages today, last alert time (tabular numbers)
- Right panel (slide-in): AI chat with Sharon — orange header, message bubbles, 
  quick-reply chips ("Situation?", "Shelters?", "All-clear?")

DESIGN SYSTEM:
- Fonts: Barlow Condensed (700) for headings/labels, JetBrains Mono for data/timestamps
- Colors: bg #060810, surface #0f172a, accent orange #f97316, blue #38bdf8, 
  green #10b981, red #f43f5e, muted text #a78b7d
- Components: sharp corners (border-radius: 2px), top accent border on cards, 
  dot-grid background pattern, monospace timestamps
- Motion: subtle pulse on status dot, slide-in chat panel, smooth threat level transitions

SECOND SCREEN — Channel Management:
- Table of monitored channels with: name, subscribers count, last message time, 
  threat classification badges, enable/disable toggle, delete button
- Add channel form: URL input + "Resolve" button to auto-fetch channel info
- Empty state with instructions

THIRD SCREEN — Shelter Map (mobile-first):
- Fullscreen map area (placeholder)
- Bottom sheet: list of nearest shelters with distance, address, walking time
- "Share my location" button (prominent, orange)
- Filter chips: All / < 500m / Open 24h

Mobile: bottom tab bar with 4 tabs (Monitor, Channels, Shelter, Chat)
```

## DESIGN.md (прикріпити як файл в Stitch workspace)

```markdown
# Sharon Design System

## Brand
Name: Sharon — Crisis AI Monitor
Tagline: Hyperlocal UAV threat intelligence

## Colors
--bg: #060810
--surface: #0f172a
--surface-low: #191b24
--border: #1e293b
--border-focus: #38bdf8
--accent: #f97316
--text: #e1e1ee
--muted: #a78b7d
--green: #10b981
--red: #f43f5e
--blue: #38bdf8

## Typography
Display/Labels: Barlow Condensed 700, uppercase, letter-spacing 0.16em
Data/Timestamps: JetBrains Mono 400/500
Body text: JetBrains Mono 13px, line-height 1.65

## Component Patterns
- Cards: border-radius 2px, border-top 2px solid accent, background surface
- Buttons: border-radius 2px, uppercase, letter-spacing 0.1em
- Status pills: small, monospace, colored background + border
- Inputs: background elevated, border 1px solid border, focus: border-focus
- Hit areas: minimum 40×40px

## Background
Dot-grid: radial-gradient(circle, #1e293b 1px, transparent 1px) 24px 24px

## Threat Levels
L0: #10b981 (calm)
L1: #eab308 (regional alert)
L2: #f97316 (city level)
L3: #f43f5e (explosion/direct threat)

## Motion
- Status dot: pulse animation 2s infinite
- Panels: slide cubic-bezier(0.2,0,0,1) 0.28s
- Scale on press: 0.96
- Font smoothing: antialiased
```
