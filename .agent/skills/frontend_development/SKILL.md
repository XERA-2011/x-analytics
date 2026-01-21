---
name: Frontend Development Standards
description: Guidelines for responsive web development in x-analytics
---

# Frontend Design Standards

## 1. Core Principles
- **Mobile-First**: Design for the smallest screen (iPhone SE/mini) first, then expand.
- **Simplicity**: Minimalist UI, single-column flow on mobile.
- **Unified Styles**: Use a single `styles.css` instead of fragmented files.

## 2. CSS Architecture (`styles.css`)
### Responsive Grid
Use `auto-fit` for automatic column adjustment without media queries where possible:
```css
.grid {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
}
```

### Breakpoints
- **Mobile**: Default (< 768px) -> Single column
- **Tablet**: > 768px
- **Desktop**: > 1024px

### Color System (Design Tokens)
| Token | Var | Description |
|:---|:---|:---|
| **Primary** | `--primary` | Main text, brand elements (#000000) |
| **Accent Red** | `--accent-red` | Negative values, danger (#ef4444) |
| **Accent Green** | `--accent-green` | Positive values, success (#22c55e) |
| **Accent Blue** | `--accent-blue` | Links, info (#3b82f6) |
| **Text Sec** | `--text-secondary` | Subtitles, meta info (#737373) |
| **Background** | `--bg-body` / `--bg-card` | Surface layers |

### Typography
- **Sans**: System fonts for UI (Inter/San Francisco)
- **Mono**: Data values for alignment (JetBrains Mono/Consolas)
- **Sizes**: Base 14px, Title 16px, Section Header 20px, Hero Score 36px

## 3. Component Patterns

### Cards (`.card`)
Standard container for all widgets.
- Use `.card-header` with flexbox for titles + actions.
- Use `.card-body` for content.
- **Hero Card**: Add `.hero` class for top border accent.

### Data Lists (`.list-item`)
Standard row for financial data.
- **Left**: `.item-main` (Title + Subtitle)
- **Right**: `.item-value` (Mono font) + `.item-change` (Color coded)

### Heatmap Grid (`.heat-grid`)
For displaying matrix data (Score + Metrics).
- Returns to 2-column grid even on mobile.
- Use `.heat-cell` for items.

### Horizontal Scroll (`.bond-scroll`)
For series data (Yield Curves) that exceeds screen width.
- Must enable `overflow-x: auto`.
- Hide scrollbars for cleaner UI (`scrollbar-width: none`).

## 4. HTML Structure
- Use Semantic Tags: `<header>`, `<main>`, `<section>`, `<footer>`.
- **JS-Driven**: Keep HTML skeleton simple; render data-heavy content via JS.

## 5. JavaScript Rendering & Interaction

### State Management
- **Manual Refresh Only**: Do not use `setInterval` for auto-refreshing data.
- **Loading States**: UI must show immediate feedback (spinners/skeleton) upon user action.

### Data Formatting
- **Null Handling**: Missing data (`null`/`undefined`) must render as `--`. Never show `0` or `NaN`.
- **Formatters**:
  - Use `utils.formatNumber(val)` for general stats.
  - Use `utils.formatPercentage(val)` for rates/ratios.
  - Use `utils.formatTime(ts)` for timestamps.

### Market-Specific Colors
- **CN / Metals / Crypto**:
  - Up (涨): **Red** (`var(--accent-red)`) `.text-up`
  - Down (跌): **Green** (`var(--accent-green)`) `.text-down`
- **US Market**:
  - Up (Gain): **Green** (`var(--accent-green)`) `.text-up-us`
  - Down (Loss): **Red** (`var(--accent-red)`) `.text-down-us`

### DOM Manipulation
- **Class Coupling**: JS render functions must use classes defined in `styles.css`.
- **Injection**: Use `innerHTML` with template literals for list rendering; ensure content is escaped if user-generated (not applicable for internal API data).

## 6. JavaScript Architecture
### Modular Design (Controller Pattern)
Complex logic must be split by business domain into separate modules under `web/js/modules/`:
- **Modules**: Separate files for distinct business logic (e.g., `market-cn.js`, `metals.js`).
  - Each module exports a Controller class (e.g., `CNMarketController`).
  - Controllers handle data fetching (`loadData`) and rendering (`render*`).
  - Modules **must not** hardcode global event listeners; they should focus on their specific DOM section.

### App Shell (`main.js`)
- Acts as the central orchestrator.
- **Responsibilities**:
  - Global Event Listeners (Keyboard shortcuts, window resize).
  - Tab Switching logic.
  - Instantiating Controllers in `this.modules`.
  - Routing `refreshCurrentTab()` calls to the active controller.

### Shared Utilities
- **`utils.js`**: Pure functions (formatting, DOM helpers).
- **`api.js`**: All network requests.
- **`charts.js`**: ECharts wrappers and theme configuration.


