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

Update `.env` with your Plaid credentials and environment settings:

```bash
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox
PLAID_STORAGE_PATH=data/plaid.sqlite3
APP_ENV=local
LOG_LEVEL=INFO
DEFAULT_CLIENT_USER_ID=spendant-local-user
```

### Environment tiers

| Variable | Values | Purpose |
|---|---|---|
| `APP_ENV` | `local`, `staging`, `production` | Backend deployment tier |
| `PLAID_ENV` | `sandbox`, `development`, `production` | Plaid API environment |
| `LOG_LEVEL` | e.g. `INFO`, `DEBUG` | Logging verbosity |
| `DEFAULT_CLIENT_USER_ID` | string | Dev fallback when clients omit `client_user_id` |
| `CORS_ORIGINS` | comma-separated URLs | Optional browser CORS allowlist |
| `API_PUBLIC_BASE_URL` | URL | Optional public API URL for future webhooks/redirects |

For local development:

```bash
APP_ENV=local
PLAID_ENV=sandbox
DEFAULT_CLIENT_USER_ID=spendant-local-user
```

For staging/production, use the matching `APP_ENV`, HTTPS `API_PUBLIC_BASE_URL`, and the appropriate `PLAID_ENV`.

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
balance, and transaction calls. You can optionally pass `institution_id` and
`institution_name` from the Plaid Link success callback; otherwise the backend
resolves institution metadata from Plaid.

List linked institutions:

```bash
curl "http://127.0.0.1:8000/api/plaid/items?client_user_id=local-user"
```

Disconnect one linked institution:

```bash
curl -X DELETE "http://127.0.0.1:8000/api/plaid/items/{item_id}?client_user_id=local-user"
```

Get accounts:

```bash
curl "http://127.0.0.1:8000/api/plaid/accounts?client_user_id=local-user"
```

The accounts response includes both a flat `accounts` list and an `institutions`
array grouped by linked bank. Each account and balance also includes
`item_id`, `institution_id`, and `institution_name` when available.

Sync transactions:

```bash
curl "http://127.0.0.1:8000/api/plaid/transactions?client_user_id=local-user"
```

Get balances:

```bash
curl "http://127.0.0.1:8000/api/plaid/balances?client_user_id=local-user"
```

Get dashboard summary:

```bash
curl "http://127.0.0.1:8000/api/dashboard/summary?client_user_id=spendant-local-user"
```

The dashboard summary uses Plaid `personal_finance_category` primary and detailed
values for classification. The older Plaid `category` field is kept only as a
fallback for older locally cached transactions.

The backend explicitly requests Plaid Personal Finance Categories v2 from
`/transactions/sync` and maps Plaid categories into Spendant buckets:

- `INCOME`
- `HOUSING`
- `EXPENSES`
- `SUBSCRIPTIONS`
- `TRANSFER`
- `IGNORE`

The classifier covers the Plaid Personal Finance Category taxonomy at the
detailed-category level where the Spendant bucket needs special treatment. For
example, rent, utilities, and mortgage payments map to `HOUSING`; account
movement and credit card payments map to `TRANSFER`; and normal spending maps
to `EXPENSES`. Merchant/name fallbacks are still used for subscriptions because
Plaid's transaction taxonomy does not represent every subscription as a unique
category.

When Plaid Recurring Transactions access is available, the dashboard also calls
`/transactions/recurring/get` and uses active recurring outflow streams to improve
subscription and bill detection. If recurring access is not enabled for the Plaid
account, the dashboard logs a warning and falls back to transaction-level PFC
classification.

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

Test linking two sandbox institutions for the same user:

```bash
python scripts/smoke_plaid.py --create-sandbox-token --link-second-institution
```

The full smoke test creates a sandbox public token directly through Plaid,
exchanges it through this API, then fetches items, accounts, balances, and transactions.

After linking a Plaid item, smoke test the dashboard endpoint:

```bash
python scripts/smoke_dashboard.py --client-user-id spendant-local-user
```

To clear locally cached transactions and force a fresh Plaid sync on the next
transaction or dashboard request:

```bash
python scripts/reset_transaction_cache.py --client-user-id spendant-local-user
```

Reset cache for one linked institution only:

```bash
python scripts/reset_transaction_cache.py --client-user-id spendant-local-user --item-id ITEM_ID
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
- Real Plaid public token exchange
- Local SQLite storage for linked Plaid Items
- Real Plaid accounts, balances, and transaction sync endpoints
- Multi-bank support: multiple Plaid Items per user with institution metadata
- Dashboard summary endpoint with rule-based Spendant buckets
- Plaid personal finance category storage for synced transactions
- Plaid service boundary
- Environment-based configuration
- Local setup documentation

Not implemented yet:

- Production-grade encrypted token storage
- Authentication
- User accounts
- Plaid webhooks
