# Spendant Backend

FastAPI backend foundation for Spendant, an iPhone cash-flow planning app focused on answering:

> Tell me how much I can safely spend, save, and invest this month.

This project currently includes the local API foundation and Plaid integration boundaries only. It does not include database storage, authentication, or full Plaid API calls yet.

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

Routes depend on services, and services depend on configuration. This keeps Plaid-specific code outside the route layer and leaves room to add persistence later.

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
```

Supported `PLAID_ENV` values are `sandbox`, `development`, and `production`.

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

Exchange a mock public token:

```bash
curl -X POST http://127.0.0.1:8000/api/plaid/exchange-public-token
```

Get mock accounts:

```bash
curl http://127.0.0.1:8000/api/plaid/accounts
```

Get mock transactions:

```bash
curl http://127.0.0.1:8000/api/plaid/transactions
```

Get mock balances:

```bash
curl http://127.0.0.1:8000/api/plaid/balances
```

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
- Mock Plaid exchange, accounts, transactions, and balances endpoints
- Plaid service boundary
- Environment-based configuration
- Local setup documentation

Not implemented yet:

- Full Plaid API calls
- Database persistence
- Authentication
- User accounts
