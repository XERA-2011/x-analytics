---
description: Run automated code quality checks (Linting, Formatting, Type Checking)
---

# Code Sentinel Workflow

This workflow executes a suite of automated tools to ensure code quality and consistency.

## Capabilities
- **Python**: Uses `ruff` for fast linting/formatting and `mypy` for static type checking.
- **Web**: Uses `prettier` (via npx) for formatting HTML/CSS/JS.

## Usage

### 1. Quick Check (Fast)
Run basic linting and formatting without strict type checking.
```bash
python .shared/code-sentinel/scripts/check.py --quick
```

### 2. Full Audit (Strict)
Run all checks including strict type analysis.
```bash
python .shared/code-sentinel/scripts/check.py --full
```

### 3. Auto Fix
Attempt to automatically fix linting and formatting errors.
```bash
python .shared/code-sentinel/scripts/check.py --fix
```

### 4. Python 3.9 Compatibility Check
Scan for Python 3.10+ syntax that will break Docker builds.
```bash
# Check for incompatible type syntax
grep -rn ": dict\[" analytics/ --include="*.py"
grep -rn ": list\[" analytics/ --include="*.py"
grep -rn " | None" analytics/ --include="*.py"
grep -rn "-> dict\[" analytics/ --include="*.py"
```

## Setup
If tools are missing, install them:
```bash
pip install ruff mypy
# For web
npm install -g prettier
```

---

## 📚 Lessons Learned Reminder

> After resolving major bugs or discovering new best practices, check if the following files need updates:
> - `.agent/skills/python_development/SKILL.md`
> - `.agent/skills/frontend_development/SKILL.md`
> - `.agent/workflows/*.md`
