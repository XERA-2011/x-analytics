---
name: python-development
description: "⚠️ MANDATORY: Read before modifying ANY .py files. Contains Python 3.9 syntax requirements, caching patterns, and anti-scraping rules."
---

# Python Development Standards

## 1. Architecture & Layering Principles

The backend is organized into three distinct, decoupled layers. AI agents must respect these architectural boundaries without needing a static file inventory:

### 1.1 Infrastructure Layer (`analytics/core/`)
Houses shared platform capabilities:
- **Centralized Config & TTLs**: `config.py` holds all timeout, interval, and cache TTL definitions (`settings.CACHE_TTL`).
- **Caching Engine**: `cache.py` provides the Redis interface and `@cached` decorator.
- **Data Provider & Anti-Scraping**: `data_provider.py`, `throttler.py`, and `patch.py` encapsulate AkShare wrappers, request rate-limiting, and client impersonation.
- **Background Scheduler**: `scheduler.py` manages background tasks for periodic cache warmup and index calculations.
- **Shared Utilities**: `utils.py` contains defensive helpers like `safe_float`, `akshare_call_with_retry`, and Beijing timezone helpers.
- **Persistence Bootstrap**: `db.py` initializes Tortoise ORM.

### 1.2 Domain Business Layer (`analytics/modules/`)
Contains domain-specific calculations, financial metrics, and indicator logic organized by asset class or market.
- **Stateless Mandate**: Business modules MUST NOT hold mutable in-memory state. All cached outputs must be stored in Redis.
- **Zero Raw External Calls**: Never invoke raw `ak.*` directly in business modules. Always wrap external data access through `akshare_call_with_retry` or core helpers.
- **Centralized TTL**: Never hardcode cache durations. Always use `settings.CACHE_TTL["category"]`.
- **Defensive Parsing**: Always use `safe_float(val, default=None)` on external API responses to avoid `ValueError` or unexpected null crashes.

### 1.3 Persistence Layer (`analytics/models/`)
Tortoise ORM models for long-term historical records and analytics snapshots.
- **Async-Only**: All database interactions must be `await`ed.
- **Multi-DB Compatibility**: Must support both SQLite (local dev) and PostgreSQL (production) via `settings.DATABASE_URL`.

---

## 2. Data Fetching & Anti-Scraping Rules

Direct, unguarded calls to `akshare` in business logic are **STRICTLY FORBIDDEN**.

```python
# ✅ REQUIRED: Wrap external calls with retry and backoff
from analytics.core.utils import akshare_call_with_retry

df = akshare_call_with_retry(ak.fund_purchase_em, max_retries=3)
```

- **Throttling**: High-frequency or rate-sensitive data sources must pass through `fetch_with_throttle`.
- **Patches**: Entry points (`server.py`, CLI scripts) must ensure `apply_patches()` is executed on startup.

---

## 3. Caching Strategy & Redis-First Policy

- **Decorator Usage**:
  ```python
  @cached("namespace:key", ttl=settings.CACHE_TTL["category"])
  async def get_market_data(): ...
  ```
- **Passive Serving**: During rate-limiting or cold start, endpoints return structured `"warming_up"` status instead of blocking user requests.
- **Cache Key Versioning**: When data structure or calculation logic changes significantly, increment the cache key version (e.g. `qdii:passive_funds_v46`) to safely invalidate legacy cache without flushing entire Redis databases in production.

---

## 4. Python 3.9 Compatibility (CRITICAL)

> ⚠️ **CRITICAL CONSTRAINT**: The production Docker container runs **Python 3.9**.
> **Python 3.10+ syntax will crash the container on boot!**

### Forbidden Syntax vs. 3.9 Compatible
| Python 3.10+ (❌ FORBIDDEN) | Python 3.9 (✅ REQUIRED) | Import Required |
|:----------------------------|:-------------------------|:----------------|
| `X \| Y`                   | `Union[X, Y]`            | `from typing import Union` |
| `X \| None`                | `Optional[X]`            | `from typing import Optional` |
| `dict[K, V]`                | `Dict[K, V]`             | `from typing import Dict` |
| `list[T]`                   | `List[T]`                | `from typing import List` |
| `tuple[T, ...]`             | `Tuple[T, ...]`          | `from typing import Tuple` |

### Pre-commit Verification Command
Run this grep command before committing any Python changes:
```bash
grep -rn ": dict\[\|: list\[\| | None\|-> dict\[\|-> list\[" analytics/ --include="*.py"
```

---

## 5. Code Hygiene & Quality Standards

- **Type Hints**: All public function signatures MUST have explicit type annotations.
- **No Magic Numbers**: Extract domain thresholds into named constants (e.g. `STALE_THRESHOLD_SECONDS = 300`).
- **No Wildcard Imports**: `from module import *` is strictly forbidden.
- **Clean Temporary Files**: Always delete debug/test scripts (`test_*.py`, `debug_*.py`) created during development before marking tasks complete.
