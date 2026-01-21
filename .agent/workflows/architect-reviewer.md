---
description: Perform deep architectural reviews and logic analysis
---
# Architect & Reviewer Workflow

This workflow is for deep, intelligent analysis of code structure, logic, and design patterns.

## Philosophy
- **Security First**: Always check for injection, leakage, and permission flaws.
- **Performance**: Look for O(n^2) loops, unnecessary IO, and cache misses.
- **Maintainability**: Enforce DRY (Don't Repeat Yourself) and SOLID principles.
- **Frontend Excellence**: Enforce Mobile-First, consistent styling, and responsive design.

## Usage

### 1. Structured Review
Ask the agent to review a specific file or module against the guidelines.
> "Run Architect Review on `analytics/market.py` focusing on caching strategy."
> "Run Architect Review on `web/js/main.js` checking for UI compliance."

### 2. Architecture Plan
Before starting a big feature, ask for an architectural plan.
> "Draft an architecture plan for the new 'User Portfolio' module."

## Checklist to Enforce
### General
1.  **Error Handling**: Are try/except blocks too broad? Are errors logged?
2.  **Config**: Are secrets hardcoded? (MUST be in env vars).
3.  **Typos**: Check function names and variable consistency.
4.  **Complexity**: Is a function doing too much? (Split it).

### UI/UX & Frontend
1.  **UI Standards**: Does it follow [Frontend Skills](../skills/frontend_development/SKILL.md)?
2.  **Responsive**: Is layout functional on small screens? (Mobile-First verification).
3.  **Clean Code**: Are CSS variables (`styles.css`) used instead of hardcoded hex values?
4.  **Structure**: Are semantic HTML tags used? Is JS rendering decoupled?

## Reference
See `.agent/skills/` for the specific standards of this project.
- [Frontend Development Standards](../skills/frontend_development/SKILL.md)
- [Python Development Standards](../skills/python_development/SKILL.md)

---

## 📚 Lessons Learned Reminder

> After resolving major issues or discovering new best practices, check if the following files need updates:
> - `.agent/skills/python_development/SKILL.md`
> - `.agent/skills/frontend_development/SKILL.md`
> - `.agent/workflows/*.md`

---

## ⚙️ Language Policy

> **All content in `.agent/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
