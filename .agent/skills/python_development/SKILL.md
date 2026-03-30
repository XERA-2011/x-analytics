---
name: Python Development Standards
description: "⚠️ MANDATORY: Read before modifying ANY .py files. Contains Python 3.9 syntax requirements, caching patterns, and anti-scraping rules."
---

# Development Standards

## 1. Project Architecture
- **Core (`analytics/core/`)**: Infrastructure code only.
  - `config.py`: Centralized configuration (TTLs, Intervals).
  - `cache.py`: Redis interface and decorators.
  - `data_provider.py`: Shared data provider (AkShare wrapper with singleton pattern).
  - `scheduler.py`: Background task scheduler (periodic data refresh, warmup).
  - `patch.py`: Anti-scraping patches (User-Agent, Headers).
  - `throttler.py`: Global request rate limiting.
  - `rate_limiter.py`: API endpoint rate limiting (public/admin).
  - `security.py`: Authentication and security middleware.
  - `utils.py`: Shared utilities (`safe_float`, `akshare_call_with_retry`, `get_beijing_time`).
  - `db.py`: Database initialization (Tortoise ORM).
  - `decorators.py`: Shared decorators.
  - `logger.py`: Logging configuration.
  - `fear_greed.py`: Base fear & greed index calculation logic.
- **Modules (`analytics/modules/`)**: Business logic grouped by domain.
  - `market_cn/`: A-share market (indices, leaders/sectors, bonds, LPR, fear & greed).
  - `market_hk/`: Hong Kong market (indices, fear & greed).
  - `market_us/`: US market (indices, leaders, treasury, fear & greed, heat map).
  - `metals/`: Precious metals (spot prices, gold/silver, fear & greed).
  - `signals/`: Cross-market technical signals (overbought/oversold).
  - Modules should focus on data fetching and processing.
  - **Stateless**: Modules should not hold state; rely on Redis cache.

## 2. Data Fetching & Anti-Scraping
Direct calls to `akshare` are **FORBIDDEN** in production code. You MUST use the shared infrastructure to prevent blocking.

- **Use Retry Logic**:
  ```python
  from ...core.utils import akshare_call_with_retry
  df = akshare_call_with_retry(ak.some_api, symbol="...", max_retries=3)
  ```
- **Use Throttling**: Heavy interfaces must pass through `fetch_with_throttle`.
- **Patching**: Entry points (scripts/server) must verify `apply_patches()` is called.

## 3. Caching Strategy
- **Centralized TTL**: Do NOT hardcode TTLs. Use `settings.CACHE_TTL["key"]`.
- **Decorator Usage**:
  ```python
  @cached("namespace:key", ttl=settings.CACHE_TTL["category"])
  def get_data(): ...
  ```
- **Passive Mode**: In "Extreme Rate Limiting" mode, ensure code handles cache misses gracefully (return None/Loading) or triggers async separate from the user request if possible.
- **Cache Invalidation**:
  - If logic changes significantly, update the cache key version (e.g., `market:data_v2`) to force invalidation of persistent Redis data.
  - Do NOT rely on manual Redis flushing in production.

## 4. Database & ORM
- **Tortoise ORM**: Use Tortoise ORM for all database interactions.
- **Code First**: Define models in `analytics/models/` and let the app handle schema generation.
- **Async Only**: All database operations must be `await`ed.
- **Migration**: Schema changes in development (SQLite) are automatic, but production (Postgres) requires careful management.
- **Connection**: Use `settings.DATABASE_URL` to support both SQLite (local) and Postgres (remote).

## 5. Error Handling
- **Never Crash**: API endpoints must return a valid JSON structure even on failure.
  ```python
  except Exception as e:
      print(f"❌ Error: {e}")
      return {"error": str(e), "data": []} # Graceful fallback
  ```
- **Safe Conversions**: Use `safe_float(val, default=None)` for financial data. Avoid `float()` directly on API responses.

## 6. Code Hygiene & Readability (Strict)
### Type Hinting
- **Mandatory**: All function signatures MUST have type hints.
  ```python
  # ✅ Good
  def calculate_yield(price: float, dividend: float) -> Optional[float]: ...
  
  # ❌ Bad
  def calculate_yield(price, dividend): ...
  ```
- **Explicit Returns**: If a function returns nothing, explicit `-> None` is preferred.

### Documentation (Docstrings)
- **Google Style**: Use Google-style docstrings for all complex functions.
- **AI-Readable**: Explain *why* logic exists, not just *what* it does. This helps future Agents understand intent.

### Imports
- **Grouping**: Standard Lib -> Third Party -> Local Application.
- **Sorting**: Alphabetical order (or use `isort`).
- **No Wildcards**: `from module import *` is STRICTLY FORBIDDEN.

### Constants & Magic Numbers
- **No Magic Numbers**: Do not use hardcoded numbers (e.g. `if ratio > 90`) in logic.
- **Extraction**: Extract them as clear constants (e.g. `RATIO_THRESHOLD_HIGH = 90`) at the class or module level.

### Temporary Files & Debugging
- **Cleanup Required**: Temporary test files created for debugging or verification **MUST** be deleted before completing the task.
- **File Naming**: Debug scripts should be prefixed with `debug_` or `test_`.
- Do not commit `debug_*.py` files unless they are converted to permanent unit tests.

## 7. Python 3.9 Compatibility

> ⚠️ **CRITICAL**: Docker environment uses **Python 3.9**. Python 3.10+ syntax is FORBIDDEN!

### Forbidden Syntax
```python
# ❌ Python 3.10+ syntax (will crash Docker)
def func(x: str | None) -> dict[str, Any]: ...

# ✅ Python 3.9 compatible syntax
from typing import Optional, Dict, List, Any
def func(x: Optional[str]) -> Dict[str, Any]: ...
```

### Replacement Rules
| Python 3.10+ | Python 3.9 Compatible | Import |
|-------------|----------------------|--------|
| `X \| Y` | `Union[X, Y]` | `from typing import Union` |
| `X \| None` | `Optional[X]` | `from typing import Optional` |
| `dict[K, V]` | `Dict[K, V]` | `from typing import Dict` |
| `list[T]` | `List[T]` | `from typing import List` |

### Pre-commit Check Commands
```bash
# Scan for incompatible syntax before committing
grep -rn ": dict\[" analytics/ --include="*.py"
grep -rn ": list\[" analytics/ --include="*.py"
grep -rn " | None" analytics/ --include="*.py"
```

---

## 📚 Lessons Learned Reminder

> After resolving major issues or discovering new best practices, check if the following files need updates:
> - `.agent/skills/python_development/SKILL.md` - Python development guidelines
> - `.agent/skills/frontend_development/SKILL.md` - Frontend development guidelines
> - `.agent/workflows/*.md` - Workflow configurations

---

## ⚙️ Language Policy

> **All content in `.agent/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
