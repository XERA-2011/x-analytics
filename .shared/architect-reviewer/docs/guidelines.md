# Project Architecture Guidelines

## 1. Python Backend (FastAPI + Pandas)
- **Type Hinting**: All new functions MUST have type hints.
- **Async**: Use `async def` for all I/O bound operations (DB, API calls).
- **Pandas**: Avoid looping over DataFrames. Use vectorization.
- **Caching**: Use the `@cached` decorator for any external API call (AkShare).

## 2. Web Frontend (Vanilla JS + CSS)
- **Design System**: "Black Glass". Minimalist. No colored icons unless data-driven.
- **Performance**: Avoid forced reflows. Use `requestAnimationFrame` for animations.
- **Structure**: Separation of concerns.
    - `data.js`: Data fetching logic.
    - `ui.js`: DOM manipulation.
    - `app.js`: Controller/Glue code.

## 3. General Principles
- **KISS**: Keep It Simple, Stupid.
- **YAGNI**: You Ain't Gonna Need It. Don't over-engineer for hypothetical futures.
- **Boy Scout Rule**: Leave the code cleaner than you found it.
