# expense-splitter

## Purpose
A small FastAPI service for splitting group expenses: create a group of named
members (no auth), record who paid for what, split each expense equally among
chosen members, then read net balances and a short list of settle-up transfers.

## Layout
- `app/db.py` – SQLAlchemy engine/session (`DATABASE_URL`, default `sqlite:///./expense_splitter.db`) and ORM models: `Group`, `Member`, `Expense`, `ExpenseShare`.
- `app/schemas.py` – Pydantic request/response models.
- `app/splitting.py` – pure money logic (equal split, net balances, greedy settle, ₹ formatting). No I/O; test it directly.
- `app/main.py` – FastAPI app and routes.
- `tests/test_api.py` – pytest tests using `TestClient` and an in-memory SQLite DB via a `get_session` dependency override.

## Conventions
- Money is always **integer paise** (`*_paise` fields). Never use floats. Rupee strings are only produced for display (`format_rupees`).
- Equal splits must sum exactly to the expense: leftover paise go one each to the lowest member ids.
- Each expense stores its per-member shares (`ExpenseShare`), so balances are `paid - owed` and always sum to zero.
- Keep the project small (~5 source files, < 600 lines). Target Python 3.11 syntax.
- Tables are created at startup with `create_all`; there are no migrations.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
```

## Test
```bash
pytest
```
