---
description: Standard development workflow. Loads project guidelines before coding.
---

# Development Workflow

Before making any code changes, complete these preliminary steps.

## 1. Identify Target Files

Determine which file types will be modified based on the user's request:
- Python backend (`.py`)
- Frontend (`.js`, `.html`, `.css`)

## 2. Load Required Guidelines

Read the relevant skill documents:

- **For Python files**: Read `.agent/skills/python_development/SKILL.md`
- **For Frontend files**: Read `.agent/skills/frontend_development/SKILL.md`

If both types are involved, read both.

## 3. Confirm Key Constraints

After reading, briefly state the 2-3 most critical constraints from the guidelines that apply to this specific task. Example:
- "Python 3.9 compatible syntax required"
- "Mobile-first responsive design"
- "Use `akshare_call_with_retry` for data fetching"

## 4. Proceed with Development

Now proceed with the user's actual coding request, ensuring all changes adhere to the loaded guidelines.

## 5. Final Cleanup & Quality Check
 
Before finishing, you **MUST** perform these final actions:

1.  **Delete Temporary Files**: Run `rm` to remove any `test_*.py`, `temp_*`, or debug scripts you created.
    -   *Pass*: "I have deleted `test_hk_api.py`."
    -   *Fail*: Leaving files in the root directory.

2.  **Database Check**:
    -   "Did I update `analytics/models/`?" -> "If yes, is the change compatible with existing data?"
    -   "Does the code support both `sqlite://` and `postgres://` connection strings?"

3.  **Resilience Review**:
    -   "If the API fails, does the UI show an error?"
    -   "Are error messages centered?"

4.  **Self-Correction**: If any check fails, fix it immediately.

---

**Usage**: `/dev <your coding request>`
