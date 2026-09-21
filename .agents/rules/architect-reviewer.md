---
description: Perform deep architectural reviews and logic analysis against project guidelines.
---

# Architect & Reviewer Workflow

This workflow is for deep, intelligent analysis of code structure, logic, and design patterns.

## Usage

### 1. Structured Review
Request a review for a specific module or component:
> "Run Architect Review on `analytics/modules/qdii.py` focusing on caching strategy and anti-scraping."
> "Run Architect Review on `web/js/modules/qdii.js` checking for UI and null-safety compliance."

### 2. Architecture Plan
Before implementing a major feature, request an architectural plan:
> "Draft an architecture plan for a new 'Portfolio Tracker' module."

---

## Review Criteria (Single Source of Truth)

The reviewer verifies pull requests and new features against the authoritative skill guides:

1. **Backend Code**: Enforce [Python Development Standards](../skills/python-development/SKILL.md)
   - Python 3.9 syntax compatibility (no `X | Y`, no `dict[K, V]`).
   - Anti-scraping guard (`akshare_call_with_retry`).
   - Stateless business modules with centralized Redis TTLs (`settings.CACHE_TTL`).
   - Defensive parsing (`safe_float`).

2. **Frontend Code**: Enforce [Frontend Development Standards](../skills/frontend-development/SKILL.md)
   - Controller pattern in `web/js/modules/` without loose global listeners.
   - Mobile-first layout (iPhone SE responsive) and market color semantics.
   - Resilient state handling: no infinite loading, unified `utils.renderError()`, null rendered as `--`.

3. **Data Integrity & Architecture**: Enforce [Project Standards](../skills/project-standards/SKILL.md)
   - Absolute rule: Error > Misleading > Fake. No hardcoded mock/fallback data in production.
   - Redis-First data flow: user requests never trigger blocking external scrapes.

4. **Production Operations**: Enforce [Deployment & Operations](../skills/deployment-and-ops/SKILL.md)
   - Zero Foreign SSH: Deployments must be executed via local `./deploy.sh` to prevent Aliyun alerts.

5. **General Code Quality**:
   - Complexity: Max indent level 3. No deeply nested blocks.
   - DRY / KISS / YAGNI: Avoid speculative generalization or duplicated logic.
