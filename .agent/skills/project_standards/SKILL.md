---
name: Project Standards
description: "⚠️ MANDATORY: Core principles governing data integrity, user experience, and development philosophy. Read this FIRST before any development work."
---

# Project Standards

> **Priority**: This document defines project-level constraints. Technical implementation details are in the domain-specific skills (`frontend_development`, `python_development`).

---

## 1. Data Integrity Policy

> ⚠️ **ABSOLUTE RULE**: No misleading data. No fake data. Ever.

### Core Principle
```
Error > Misleading Data > Fake Data
        ↑ ACCEPTABLE      ↑ FORBIDDEN
```

**Truth Hierarchy**:
1. ✅ **Real Data** - Verified from source
2. ✅ **Error State** - Honest "data unavailable" message
3. ❌ **Misleading Data** - Partially true but misrepresents reality
4. ❌ **Fake Data** - Fabricated numbers with no basis

### Forbidden Patterns

| Pattern | Example | Why Forbidden |
|:--------|:--------|:--------------|
| Hardcoded fallbacks | `return fallback_value if error` | User sees fake data as real |
| Default zero values | `price = data.get('price', 0)` | 0 is a valid price, misleading |
| Estimated values (unlabeled) | `avg = (high + low) / 2` | User assumes it's actual data |
| Cached stale data (unlabeled) | Showing yesterday's price as current | Misleads trading decisions |
| Mock data in production | `if DEBUG: return mock_data` | Can leak into production |
| Placeholder text as data | `"Loading..."` that never updates | Infinite misleading state |
| Stale high-volatility data | Using yesterday's price for Bitcoin/Gold | Misleads decision making (Time-Sensitive Integrity) |

### Required Data Handling

**Backend**:
```python
# ❌ FORBIDDEN: Silent fallback to fake data
def get_price():
    try:
        return fetch_real_price()
    except:
        return 100.0  # Fake fallback!

# ✅ REQUIRED: Explicit error propagation
def get_price() -> Dict[str, Any]:
    try:
        price = fetch_real_price()
        return {"status": "ok", "data": {"price": price}}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
```

**Frontend**:
```javascript
// ❌ FORBIDDEN: Showing 0 or fake value
const price = response.data?.price || 0;
element.textContent = price;

// ✅ REQUIRED: Explicit handling of missing data
const price = response.data?.price;
element.textContent = price != null ? formatNumber(price) : '--';
```

### Data Source Requirements
- **STRICT SOURCE POLICY**: All financial data MUST be fetched exclusively via the **AkShare** library.
- **FORBIDDEN**: Direct web scraping, using `requests` to fetch third-party HTML/JSON endpoints directly, or reverse-engineering private APIs.
- If AkShare does not provide specific data, you MUST:
  1. Use an alternative available indicator from AkShare.
  2. Implement a custom calculation based on other available AkShare data.
  3. Mark the data as unavailable rather than scraping it yourself.
- Estimation/interpolation logic is **FORBIDDEN** unless:
  1. Clearly labeled as "Estimated" in the UI with visual distinction.
  2. Documented with calculation methodology.
  3. User explicitly understands it's not real data.

### Warming Up State
- New data that has not yet been fetched should display "Warming Up" status.
- Warming Up state MUST have a timeout (max 60s), after which it becomes an error state.
- **Never show stale data as current** - if cache expired, show warming_up, not old data.

### Real-time Injection Strategy
For 24/7 markets (Crypto, Metals) or high-volatility assets:
- **Problem**: Daily historical data (OHLC) is often lagging by 1 day.
- **Requirement**: You MUST inject the latest real-time price (via minute-level API) into the historical dataset before calculating indicators (RSI, Fear & Greed).
- **Failure to do this** results in "Misleading Data" (e.g., showing "Greed" based on yesterday's high, while market crashed 10% today).

---

## 2. User Experience Principles

### 2.1 Mobile-First Design
- **Primary Target**: iPhone SE / mini (smallest common screen).
- Design for single-column layouts first, then expand for larger screens.
- Touch targets must be at least 44×44px.

### 2.2 Immediate Feedback
- Every user action (tap, click) MUST provide visual feedback within 100ms.
- Loading states must appear immediately upon data request.
- **FORBIDDEN**: Silent failures or infinite loading spinners.

### 2.3 Graceful Degradation
- Partial data is acceptable; show what's available.
- One failed API should NOT block the entire page.
- Use `Promise.allSettled` for independent parallel requests.

### 2.4 Clarity Over Density
- Prefer whitespace and readability over cramming more data.
- Each card/section should have ONE clear purpose.
- Avoid cognitive overload: max 5-7 items per list visible without scrolling.

### 2.5 Color Semantics
- Colors must convey meaning consistently:
  | Context | Up/Positive | Down/Negative |
  |:--------|:------------|:--------------|
  | CN/HK Market | Red 🔴 | Green 🟢 |
  | US Market | Green 🟢 | Red 🔴 |
  | Crypto/Metals | Red 🔴 | Green 🟢 |

---

## 3. Development Philosophy

### 3.1 Defensive Programming
- **Assume failure**: Every external call can fail.
- **Explicit null checks**: Never assume data exists.
- **Safe defaults**: Use `safe_float()`, `value ?? '--'` patterns.

### 3.2 Code Clarity Over Cleverness
- Prefer readable code over "clever" one-liners.
- Extract magic numbers into named constants.
- Comments should explain **WHY**, not **WHAT**.

### 3.3 Separation of Concerns
- **Backend**: Data fetching + processing + caching.
- **Frontend**: Rendering + interaction + state display.
- **API Contract**: Backend returns structured JSON; Frontend handles presentation.

### 3.4 Fail-Safe Defaults
- UI elements default to hidden/disabled until data confirms activation.
- Buttons that require data should not be clickable until loaded.

### 3.5 Comment Standards

> [!IMPORTANT]
> Comments must add value. Process notes, redundant explanations, and outdated comments are **FORBIDDEN**.

#### Forbidden Comment Patterns (❌)

| Pattern | Example | Why It's Bad |
|:--------|:--------|:-------------|
| **Process notes** | `# TODO: refactor this later` | Development artifacts, not production code |
| **Self-explanatory code** | `# Increment counter by 1` above `counter += 1` | Adds no value |
| **Outdated comments** | Comment says "returns 50" but code returns None | Misleading |
| **Placeholder text** | `# ... (Keep existing methods) ...` | Incomplete code |
| **Debug notes** | `# This fixed the bug from issue #123` | Belongs in git commit, not code |

#### Required Comment Practices (✅)

1. **Explain WHY, not WHAT**
   ```python
   # ❌ Bad: Get the VIX value
   # ✅ Good: VIX > 30 indicates market panic, invert score accordingly
   ```

2. **Keep comments in sync with code**
   - When modifying code, **MUST** update related comments in the same commit.
   - Stale comments are worse than no comments.

3. **Concise and clear**
   - One line per concept.
   - No filler words ("basically", "essentially", "in order to").

4. **Docstrings for public APIs only**
   - Public functions: Include docstring with Args/Returns.
   - Private helpers: Docstring optional if name is self-explanatory.

---

## 4. Quality Gates

### Before Committing Code
- [ ] No hardcoded mock/fake data
- [ ] All error paths handled (no infinite loading)
- [ ] Mobile layout tested (Chrome DevTools)
- [ ] Type hints present (Python) / JSDoc comments (JavaScript)
- [ ] No Python 3.10+ syntax (Docker uses 3.9)
- [ ] Clean up temporary files (e.g., `test_*.py`, `debug.json`)

### Before Merging
- [ ] Tested on real data source (not cached/stale)
- [ ] Verified warming up → loaded → error states work
- [ ] No console errors in browser
- [ ] Responsive design checked on 3 breakpoints

---

## 6. Redis-First Architecture

> **Core Principle**: Redis is the single source of truth for all user-facing data.

### 6.1 Data Flow Model
```
┌──────────────────────────────────────────────────────────────────┐
│                        BACKGROUND                                │
│  ┌──────────────┐      ┌─────────┐      ┌─────────────────────────┐
│  │  Scheduler   │ ───► │ AkShare │ ───► │  Redis Cache / Postgres │
│  │  (Periodic)  │      │  APIs   │      │  (Persist & Cache)      │
│  └──────────────┘      └─────────┘      └────────────┬────────────┘
└──────────────────────────────────────────────────────┼─────────────┘
                                                       │
┌──────────────────────────────────────────────────────┼─────────────┐
│                        USER REQUEST                  ▼             │
│  ┌──────────────┐      ┌─────────┐      ┌────────────────────────┐ │
│  │   Browser    │ ───► │   API   │ ───► │  Redis (Hot)           │ │
│  │   Request    │ ◄─── │ Endpoint│ ◄─── │  Postgres (History)    │ │
│  └──────────────┘      └─────────┘      └────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 6.2 User Request Policy

| Rule | Description |
|:-----|:------------|
| **Read-Only from Redis** | User API requests ONLY read from Redis cache. |
| **No Direct Fetching** | User requests NEVER trigger external API calls (AkShare, etc.). |
| **Instant Response** | API must return within 500ms. No blocking on data availability. |
| **Passive Mode** | If cache is empty/expired, return "warming_up" status, don't fetch. |

### 6.3 Response State Machine

Every API endpoint MUST return one of these states:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SUCCESS   │     │ WARMING_UP  │     │    ERROR    │
│  (有数据)   │     │  (预热中)   │     │   (错误)    │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ status: ok  │     │ status:     │     │ status:     │
│ data: {...} │     │ warming_up  │     │ error       │
│             │     │ message:    │     │ message:    │
│             │     │ "数据预热中"│     │ "具体错误"  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 6.4 Warming Up Timeout Policy

> **CRITICAL**: "Warming Up" is NOT an excuse for infinite loading.

| Scenario | Max Duration | Action After Timeout |
|:---------|:-------------|:---------------------|
| Initial startup (cold start) | 60 seconds | Transition to ERROR state |
| Scheduler failed silently | 5 minutes | Backend logs alert, return ERROR |
| Data source unavailable | N/A | Return ERROR with specific message |

**Frontend Implementation**:
```javascript
// ❌ FORBIDDEN: Infinite warming up display
if (response.status === 'warming_up') {
    showLoading(); // Could show forever!
}

// ✅ REQUIRED: Warming up with timeout
if (response.status === 'warming_up') {
    showWarmingUp();
    setTimeout(() => {
        if (stillWarmingUp) {
            showError('Data unavailable. Please try again later.');
        }
    }, 60000); // 60s max
}
```

### 6.5 Scheduler Responsibilities

The background scheduler is the ONLY component that fetches external data:

| Responsibility | Implementation |
|:---------------|:---------------|
| Periodic refresh | Run every N minutes based on data type |
| Pre-warm on startup | Fetch critical data before accepting requests |
| TTL management | Set appropriate expiry for each data type |
| Failure handling | Log errors, do NOT crash; stale data > no data |
| Health monitoring | Track last successful fetch time per endpoint |

### 6.6 API Response Contract

**Standard Response Structure**:
```python
# Backend (Python)
{
    "status": "ok" | "warming_up" | "error",
    "data": {...} | None,
    "message": str | None,  # Required for warming_up/error
    "cached_at": "ISO8601 timestamp",  # When data was cached
    "ttl": int  # Seconds until cache expires
}
```

**Frontend Handling**:
```javascript
// EVERY API call must handle all 3 states
async function loadData(endpoint) {
    const response = await api.fetch(endpoint);
    
    switch (response.status) {
        case 'ok':
            renderData(response.data);
            break;
        case 'warming_up':
            renderWarmingUp(response.message);
            scheduleRetry(endpoint, 5000); // Retry in 5s
            break;
        case 'error':
            renderError(response.message);
            break;
    }
}
```

---

## 7. Related Skills

| Skill | Path | When to Read |
|:------|:-----|:-------------|
| Frontend Standards | `.agent/skills/frontend_development/SKILL.md` | Modifying `.js`, `.html`, `.css` |
| Python Standards | `.agent/skills/python_development/SKILL.md` | Modifying `.py` files |

---

## ⚙️ Language Policy

> **All content in `.agent/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
