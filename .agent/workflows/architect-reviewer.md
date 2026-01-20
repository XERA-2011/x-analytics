---
description: Perform deep architectural reviews and logic analysis
---
# Architect & Reviewer Workflow

This workflow is for deep, intelligent analysis of code structure, logic, and design patterns.

## Philosophy
- **Security First**: Always check for injection, leakage, and permission flaws.
- **Performance**: Look for O(n^2) loops, unnecessary IO, and cache misses.
- **Maintainability**: Enforce DRY (Don't Repeat Yourself) and SOLID principles.

## Usage

### 1. Structured Review
Ask the agent to review a specific file or module against the guidelines.
> "Run Architect Review on `analytics/market.py` focusing on caching strategy."

### 2. Architecture Plan
Before starting a big feature, ask for an architectural plan.
> "Draft an architecture plan for the new 'User Portfolio' module."

## Checklist to Enforce
1.  **Error Handling**: Are try/except blocks too broad? Are errors logged?
2.  **Config**: Are secrets hardcoded? (MUST be in env vars).
3.  **Typos**: Check function names and variable consistency.
4.  **Complexity**: Is a function doing too much? (Split it).

## Reference
See `.shared/architect-reviewer/docs/guidelines.md` for the full knowledge base of this project's best practices.
