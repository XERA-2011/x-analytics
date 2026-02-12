---
description: Perform deep architectural reviews and logic analysis
---
# Architect & Reviewer Workflow

This workflow is for deep, intelligent analysis of code structure, logic, and design patterns.

## Usage

### 1. Structured Review
Ask the agent to review a specific file or module against the project guidelines.
> "Run Architect Review on `analytics/modules/metals/fear_greed.py` focusing on caching strategy."
> "Run Architect Review on `web/js/modules/market-cn.js` checking for UI compliance."

### 2. Architecture Plan
Before starting a big feature, ask for an architectural plan.
> "Draft an architecture plan for a new 'Portfolio Tracker' module."

## Review Checklist

The reviewer must enforce all standards defined in the Skills documents:

### Backend (Python)
Refer to [Python Development Standards](../skills/python_development/SKILL.md) for the full rules. Key areas:
- **Type Safety**: All functions typed (`mypy` compliant)
- **No Magic Numbers**: Constants extracted (e.g., `MAX_RETRIES = 5`)
- **Python 3.9 Compatibility**: No `X | Y`, `dict[K, V]`, `list[T]` syntax
- **Caching**: Uses `@cached` decorator with centralized TTL from `settings`
- **Anti-Scraping**: Uses `akshare_call_with_retry`, never direct `ak.xxx()` calls

### Frontend (JS/HTML/CSS)
Refer to [Frontend Development Standards](../skills/frontend_development/SKILL.md) for the full rules. Key areas:
- **Mobile-First**: Layout functional on iPhone SE/mini
- **Color Conventions**: CN/HK = red-up/green-down, US = green-up/red-down
- **CSS Variables**: Uses design tokens from `styles.css`, no hardcoded hex
- **Error Handling**: Uses `utils.renderError()`, no infinite loading states
- **Semantic HTML**: Proper `<header>`, `<main>`, `<section>`, `<footer>` usage

### General
- **Complexity**: Max indent level 3. No deeply nested `if/for`
- **Naming**: Python `snake_case`, JS `camelCase`, constants `UPPER_CASE`
- **Dead Code**: No commented-out code blocks
- **DRY / KISS / YAGNI**: No over-engineering or duplication

---

## ⚙️ Language Policy

> **All content in `.agent/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
