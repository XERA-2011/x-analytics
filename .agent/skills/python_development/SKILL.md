---
name: Python Development Standards
description: "⚠️ MANDATORY: Read before modifying ANY .py files. Contains Python 3.9 syntax requirements, caching patterns, and anti-scraping rules."
---

# Development Standards

## 1. Project Architecture
- **Core (`analytics/core/`)**: Infrastructure code only.
  - `config.py`: Centralized configuration (TTLs, Intervals).
  - `cache.py`: Redis interface and decorators.
  - `patch.py`: Anti-scraping patches (User-Agent, Headers).
  - `throttler.py`: Global request rate limiting.
- **Modules (`analytics/modules/`)**: Business logic grouped by domain (e.g., `market_cn`, `metals`).
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

## 4. Error Handling
- **Never Crash**: API endpoints must return a valid JSON structure even on failure.
  ```python
  except Exception as e:
      print(f"❌ Error: {e}")
      return {"error": str(e), "data": []} # Graceful fallback
  ```
- **Safe Conversions**: Use `safe_float(val, default=None)` for financial data. Avoid `float()` directly on API responses.

## 5. Testing and Debugging
1. **Test Location**: All debug scripts, temporary test files, and exploration code **MUST** be created in the `tests/` directory.
   - ❌ Do NOT create debug scripts in the project root.
   - ✅ Create `tests/debug_market.py` instead of `debug_market.py`.
2. **File Naming**: Debug scripts should be prefixed with `debug_` or `test_`.

## 6. Python 3.9 Compatibility

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
> - `.shared/*/docs/guidelines.md` - Project guidelines

---

## ⚙️ Language Policy

> **All content in `.agent/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
