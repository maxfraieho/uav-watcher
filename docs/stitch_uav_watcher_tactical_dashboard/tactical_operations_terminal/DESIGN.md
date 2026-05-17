---
name: Tactical Operations Terminal
colors:
  surface: '#11131c'
  surface-dim: '#11131c'
  surface-bright: '#373942'
  surface-container-lowest: '#0b0e16'
  surface-container-low: '#191b24'
  surface-container: '#1d1f28'
  surface-container-high: '#272a33'
  surface-container-highest: '#32343e'
  on-surface: '#e1e1ee'
  on-surface-variant: '#e0c0b1'
  inverse-surface: '#e1e1ee'
  inverse-on-surface: '#2e3039'
  outline: '#a78b7d'
  outline-variant: '#584237'
  surface-tint: '#ffb690'
  primary: '#ffb690'
  on-primary: '#552100'
  primary-container: '#f97316'
  on-primary-container: '#582200'
  inverse-primary: '#9d4300'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#bcc7de'
  on-tertiary: '#263143'
  tertiary-container: '#909bb1'
  on-tertiary-container: '#283345'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbca'
  primary-fixed-dim: '#ffb690'
  on-primary-fixed: '#341100'
  on-primary-fixed-variant: '#783200'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#d8e3fb'
  tertiary-fixed-dim: '#bcc7de'
  on-tertiary-fixed: '#111c2d'
  on-tertiary-fixed-variant: '#3c475a'
  background: '#11131c'
  on-background: '#e1e1ee'
  surface-variant: '#32343e'
typography:
  display-lg:
    fontFamily: Barlow Condensed
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: 0.02em
  headline-lg:
    fontFamily: Barlow Condensed
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.02em
  headline-md:
    fontFamily: Barlow Condensed
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  button:
    fontFamily: Barlow Condensed
    fontSize: 14px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
spacing:
  sidebar-width: 300px
  topbar-height: 64px
  gutter: 16px
  margin-page: 24px
  unit: 8px
---

## Brand & Style

This design system is engineered for high-stakes, data-intensive environments where speed of recognition and functional clarity are paramount. The aesthetic is rooted in **tactical brutalism**—a style that prioritizes utility over decoration, utilizing high-contrast elements and a utilitarian grid to manage complex information densities.

The UI should evoke the feeling of a mission-critical terminal: authoritative, precise, and uncompromising. Visual noise is eliminated to ensure that "ember" alerts and "electric sky" focus states are immediately actionable. A subtle dot-grid background (4px intervals) provides a sense of mathematical structure across the entire canvas.

## Colors

The palette is optimized for low-light "command center" environments.

*   **Primary (Ember Orange):** Reserved for primary calls to action, active status indicators, and critical alerts. It represents the "active" or "warning" layer.
*   **Secondary (Electric Sky Blue):** Used for interactive borders, focus states, and system-level metadata. It represents the "logical" or "navigational" layer.
*   **Neutral (Void Black):** The #060810 base ensures maximum contrast and reduces eye strain in dark rooms.
*   **Surface:** Use #0f172a for card backgrounds and #1e293b for headers/borders to create subtle tonal layering without relying on shadows.

## Typography

The typographic system utilizes a dual-font approach to separate narrative and data.

*   **Barlow Condensed:** Used for headers, titles, and button labels. Its narrow width allows for high-impact text in space-constrained terminal environments.
*   **JetBrains Mono:** Used for all body text, data points, code, and input fields. The monospaced nature ensures that columns of numbers and technical data align perfectly for quick scanning.

**Hierarchy Rules:**
- All headers and buttons must be **Uppercase**.
- Data points should use `data-tabular` for fixed-width alignment.
- Labels are always paired with a technical icon or colon.

## Layout & Spacing

The layout follows a rigid two-column structure designed for persistent monitoring.

1.  **Main Content Area:** A fluid-width region for data visualizations, maps, or primary tables.
2.  **Sidebar:** A fixed 300px wide panel on the right for supplemental data, telemetry, or filter controls.
3.  **Topbar:** A 64px sticky header containing the system clock, breadcrumbs, and global search.

**Grid System:**
- Use an 8px spacing rhythm for all internal component padding.
- 16px gutters between cards.
- 24px margins for the primary container.
- Layout sections should be separated by 1px Electric Sky Blue (#38bdf8) lines rather than white space.

## Elevation & Depth

Depth is conveyed through **tonal layers and outlines** rather than shadows. 

- **Background:** Void Black (#060810) with a subtle 4px dot-grid overlay.
- **Surface Level 1:** #0f172a for cards and containers.
- **Surface Level 2:** #1e293b for headers within cards or active sidebar items.
- **Outlines:** All containers use a 1px border. Default borders are #1e293b. Active or Focused containers use Electric Sky Blue (#38bdf8).
- **Z-Index:** Modals and overlays should have no shadow; they are distinguished by a solid 2px Electric Sky Blue border and a darkened semi-transparent backdrop.

## Shapes

The shape language is severe and technical. 

- **Corner Radius:** All elements utilize a strict 2px corner radius. This is enough to prevent a jagged appearance on high-DPI screens while maintaining a "sharp" tactical feel.
- **Icons:** Use stroke-based, geometric icons. Avoid filled icons unless indicating an active toggle.
- **Dividers:** Horizontal and vertical lines are 1px thick.

## Components

### Buttons
- **Ghost Primary:** 1px border of Electric Sky Blue (#38bdf8), Barlow Condensed Bold Uppercase text. 2px corner radius. On hover, background fills with 10% opacity blue.
- **Action Ember:** Solid #f97316 background with Void Black text. Reserved for "Fire", "Submit", or "Execute" actions.

### Cards
- **Tactical Container:** Background #0f172a, 1px border #1e293b. 
- **Header Accent:** Every card must have a 2px top border of Ember Orange (#f97316) to denote it as a functional module.

### Input Fields
- **Terminal Input:** Background #060810, 1px border #1e293b. On focus, border changes to Electric Sky Blue. Text is always JetBrains Mono.
- **Status Tags (Chips):** Small, sharp-cornered rectangles. Background: Tonal variant of the status; Text: Uppercase Barlow Condensed.

### Lists & Tables
- **Data Grid:** Zebra-striping using #0f172a and #131c2e. 1px horizontal dividers.
- **Row Hover:** On hover, the row should gain a 1px Electric Sky Blue outline.

### Navigation
- **Sidebar Items:** Simple text labels with a vertical 2px indicator on the left that glows Electric Sky Blue when the item is active.