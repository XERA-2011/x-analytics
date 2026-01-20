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
python3 .shared/code-sentinel/scripts/check.py --quick
```

### 2. Full Audit (Strict)
Run all checks including strict type analysis.
```bash
python3 .shared/code-sentinel/scripts/check.py --full
```

### 3. Auto Fix
Attempt to automatically fix linting and formatting errors.
```bash
python3 .shared/code-sentinel/scripts/check.py --fix
```

## Setup
If tools are missing, install them:
```bash
pip install ruff mypy
# For web
npm install -g prettier
```
