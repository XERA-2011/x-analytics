---
name: frontend-development
description: "⚠️ MANDATORY: Read before modifying ANY .js/.html/.css files. Contains critical mobile-first layout, color conventions (CN=red-up, US=green-up), and JS architecture rules."
---

# Frontend Design Standards

## 1. Core Principles
- **Mobile-First**: Design for the smallest screen (iPhone SE/mini) first, then expand.
- **Simplicity**: Minimalist UI, single-column flow on mobile (< 768px).
- **Unified Styles**: Use the central design token system in `styles.css` instead of fragmented or inline styles.

---

## 2. CSS Architecture & Color System (`web/css/styles.css`)

### 2.1 Responsive Layout
- **Mobile (< 768px)**: Default single-column layout. Touch targets must be at least 44×44px.
- **Desktop (>= 1024px)**: Expanded multi-column grid (`display: grid` with `auto-fit` / `minmax`).

### 2.2 Color Tokens & Market Conventions
| Market Context | Up / Positive | Down / Negative | CSS Classes |
|:---------------|:--------------|:----------------|:------------|
| **CN / HK / Metals / Crypto** | **Red** 🔴 (`#ef4444` / `#dc2626`) | **Green** 🟢 (`#22c55e` / `#16a34a`) | `.text-up` / `.text-down` |
| **US / Western Markets** | **Green** 🟢 (`#22c55e` / `#16a34a`) | **Red** 🔴 (`#ef4444` / `#dc2626`) | `.text-up-us` / `.text-down-us` |

- **Chart Palette**: ECharts indicators and visual gauges must adhere to the project palette `#16a34a` (green) and `#dc2626` (red).

---

## 3. Component & DOM Patterns

### 3.1 Standard Cards (`.card`)
Container for UI widgets:
- `.card-header`: Flexbox container for titles + status badges / action buttons.
- `.card-body`: Content container.
- `.hero`: Class added for prominent top-card border accents.

### 3.2 Data Formatting & Null Safety
- **Null Safety**: Missing or null data (`null`, `undefined`) MUST render as `--`. Never render `0`, `NaN`, or empty strings as data.
- **Shared Helpers**:
  - `utils.formatNumber(val)`: General numbers and prices.
  - `utils.formatPercentage(val)`: Rates, yields, and percentages.
  - `utils.formatTime(ts)`: Timestamps and dates.

---

## 4. JavaScript Architecture (Controller Pattern)

The web frontend is structured cleanly without heavy frameworks:

### 4.1 Orchestrator (`web/js/main.js`)
Acts as the central application shell:
- Manages tab switching, URL hash/query sync, and window resize listeners.
- Instantiates and orchestrates module controllers in `this.modules`.
- Routes refresh events to the currently active controller.

### 4.2 Shared Services
- **`web/js/api.js`**: Centralized HTTP client. Automatically handles `status: "ok" | "warming_up" | "error"`.
- **`web/js/charts.js`**: ECharts lifecycle manager, auto-resize handler, and unified theme configuration.
- **`web/js/utils.js`**: Shared formatting, DOM helpers, and standard error rendering.

### 4.3 Domain Controllers (`web/js/modules/*.js`)
Each business tab/view has a dedicated Controller class in `web/js/modules/`:
- **Single Responsibility**: Encapsulates data fetching (`loadData`) and DOM rendering for its specific view.
- **Scoped Events**: Controllers must never bind loose event listeners to `window` or `document`. All UI event handling must be scoped within their container element.
- **Extensible**: New views are added simply by creating a new `*Controller` in `web/js/modules/` and registering it in `main.js`. No changes to documentation required.

---

## 5. Resilience & Error Handling

- **Unified Error Display**: ALWAYS use `utils.renderError(containerId, msg)` instead of manual `innerHTML`. This guarantees consistent styling, centering, and icon layout.
- **Zero Infinite Spinners**: Every asynchronous operation MUST have an error branch. Never leave containers stuck in loading states.
- **Partial Failure Isolation**: When fetching multiple independent datasets, use `Promise.allSettled` or individual `.catch()` handlers so that one failing endpoint never breaks the entire dashboard.
