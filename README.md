# expense-splitter

A tiny FastAPI + SQLite API for splitting shared expenses within a group.
All amounts are integer **paise** (₹1 = 100 paise).

## Quick start
```bash
pip install -r requirements.txt   # Python 3.11+
uvicorn app.main:app --reload
```
Interactive docs: http://localhost:8000/docs. Data is stored in
`./expense_splitter.db` (override with `DATABASE_URL`).

Run the tests with `pytest`.

## API
| Method | Path | Body / result |
| --- | --- | --- |
| POST | `/groups` | `{"name": "Goa", "members": ["Asha", "Bala"]}` → group with member ids |
| GET | `/groups/{id}` | group and members |
| POST | `/groups/{id}/members` | `{"name": "Chetan"}` |
| POST | `/groups/{id}/expenses` | `{"payer_id": 1, "amount_paise": 90000, "description": "Hotel", "split_among": [1, 2, 3]}` |
| GET | `/groups/{id}/expenses` | expenses with per-member shares |
| GET | `/groups/{id}/balances` | `[{"member_id": 1, "name": "Asha", "balance_paise": 60000}, ...]` |
| GET | `/groups/{id}/settle` | `[{"from_name": "Chetan", "to_name": "Asha", "amount_paise": 40000, "summary": "Chetan pays Asha ₹400", ...}]` |

A positive balance means the member is owed money; negative means they owe.

## How splitting works
- An expense is split equally among `split_among`. If it doesn't divide evenly,
  the leftover paise go one each to the lowest member ids, so shares always sum
  to the exact amount.
- Settling pairs the largest debtor with the largest creditor repeatedly. This
  produces at most *n − 1* transfers for *n* members with non-zero balances
  (finding the absolute minimum is NP-hard and rarely differs in practice).
