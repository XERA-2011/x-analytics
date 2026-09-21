---
description: Automated code quality checks (Linting, Formatting, Type Checking, and Python 3.9 compatibility).
---

# Code Sentinel Workflow

Automated checks to ensure code hygiene and runtime compatibility before committing.

## Quality Checks

### 1. Fast Linting & Formatting (Ruff)
```bash
# Check code style and common bugs
ruff check analytics/ server.py

# Automatically fix fixable issues
ruff check analytics/ server.py --fix
```

### 2. Static Type Analysis (MyPy)
```bash
mypy analytics/
```

### 3. Python 3.9 Compatibility Scan (CRITICAL)
Scan for Python 3.10+ syntax that will crash the Python 3.9 Docker container:
```bash
grep -rn ": dict\[\|: list\[\| | None\|-> dict\[\|-> list\[" analytics/ --include="*.py"
```

### 4. Web Formatting (Prettier)
```bash
npx prettier --check "web/**/*.{html,css,js}"
```
