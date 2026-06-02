# Spendant Backend

FastAPI backend foundation for Spendant, an iPhone cash-flow planning app focused on answering:

> Tell me how much I can safely spend, save, and invest this month.

This project currently includes the local API foundation, a Plaid service boundary,
real Plaid sandbox calls, and local development storage for linked Plaid Items. It
does not include authentication, user accounts, production-grade token storage, or
Plaid webhooks yet.

## Project Structure

```text
.
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   │   ├── plaid.py
│   │   └── health.py
│   ├── services/
│   │   └── plaid_service.py
│   ├── models/
│   ├── schemas/
│   └── utils/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Routes depend on services, and services depend on configuration. This keeps Plaid-specific code outside the route layer and leaves room to replace local development storage with production persistence later.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your Plaid credentials:

```bash
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox
PLAID_STORAGE_PATH=data/plaid.sqlite3
```

Supported `PLAID_ENV` values are `sandbox`, `development`, and `production`.
`PLAID_STORAGE_PATH` stores linked Plaid Items locally for development.

## Run Locally

Run the API from the repository root:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Example API Calls

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Create a Plaid link token:

```bash
curl -X POST http://127.0.0.1:8000/api/plaid/create-link-token \
  -H "Content-Type: application/json" \
  -d '{"client_user_id":"local-user"}'
```

This endpoint calls Plaid and requires valid Plaid sandbox credentials in `.env`.

Exchange a Plaid public token:

```bash
curl -X POST http://127.0.0.1:8000/api/plaid/exchange-public-token \
  -H "Content-Type: application/json" \
  -d '{"public_token":"public-sandbox-token","client_user_id":"local-user"}'
```

This stores the returned Plaid access token in local SQLite storage for later account,
balance, and transaction calls.

Get accounts:

```bash
curl "http://127.0.0.1:8000/api/plaid/accounts?client_user_id=local-user"
```

Sync transactions:

```bash
curl "http://127.0.0.1:8000/api/plaid/transactions?client_user_id=local-user"
```

Get balances:

```bash
curl "http://127.0.0.1:8000/api/plaid/balances?client_user_id=local-user"
```

## Smoke Test Plaid Endpoints

Start the API:

```bash
uvicorn app.main:app --reload
```

In another terminal, run a quick health/link-token smoke test:

```bash
python scripts/smoke_plaid.py
```

Run the full Plaid sandbox smoke test without the iOS app:

```bash
python scripts/smoke_plaid.py --create-sandbox-token
```

The full smoke test creates a sandbox public token directly through Plaid,
exchanges it through this API, then fetches accounts, balances, and transactions.

## Environment Errors

The Plaid endpoints require:

- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_ENV`

If required variables are missing or invalid, the app raises a clear configuration error when a Plaid dependency is loaded.

## Current Scope

Implemented:

- FastAPI app initialization
- `GET /health`
- Real Plaid link token creation
- Real Plaid public token exchange
- Local SQLite storage for linked Plaid Items
- Real Plaid accounts, balances, and transaction sync endpoints
- Plaid service boundary
- Environment-based configuration
- Local setup documentation

Not implemented yet:

- Production-grade encrypted token storage
- Authentication
- User accounts
- Plaid webhooks
