# Spendant Backend

FastAPI backend foundation for Spendant, an iPhone cash-flow planning app focused on answering:

> Tell me how much I can safely spend, save, and invest this month.

This project includes the local API foundation, a Plaid service boundary,
real Plaid sandbox calls, managed JWT authentication for staging/production,
encrypted Plaid token storage, Plaid webhooks, and Postgres-ready migrations.

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
| `API_PUBLIC_BASE_URL` | URL | Public API URL for Plaid webhooks (required in production) |
| `DATABASE_URL` | Postgres URL | Optional managed Postgres URL; defaults to SQLite at `PLAID_STORAGE_PATH` |
| `TOKEN_ENCRYPTION_KEY` | string | Symmetric key material for encrypting Plaid access tokens at rest |
| `TOKEN_KEY_VERSION` | string | Active encryption key version label |
| `AUTH_REQUIRED` | `true`/`false` | Require Bearer JWT auth (defaults to `true` outside `local`) |
| `AUTH_ISSUER` | URL | Managed auth issuer |
| `AUTH_AUDIENCE` | string | Expected JWT audience |
| `AUTH_JWKS_URL` | URL | JWKS endpoint for JWT validation |
| `AUTH_USER_ID_CLAIM` | string | JWT claim used as Spendant user id (default `sub`) |

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

Readiness check:

```bash
curl http://127.0.0.1:8000/health/ready
```

Create a Plaid link token:

```bash
curl -X POST http://127.0.0.1:8000/api/plaid/create-link-token \
  -H "Content-Type: application/json" \
  -d '{"client_user_id":"spendant-local-user"}'
```

Exchange a Plaid public token:

```bash
curl -X POST http://127.0.0.1:8000/api/plaid/exchange-public-token \
  -H "Content-Type: application/json" \
  -d '{"public_token":"public-sandbox-token","client_user_id":"spendant-local-user"}'
```

Get dashboard summary:

```bash
curl "http://127.0.0.1:8000/api/dashboard/summary?client_user_id=spendant-local-user"
```

## Production Deployment

Build and run with Docker:

```bash
docker build -t spendant-api .
docker run --env-file .env -p 8000:8000 spendant-api
```

Required production/staging secrets:

```bash
APP_ENV=production
PLAID_ENV=production
API_PUBLIC_BASE_URL=https://api.spendant.app
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/spendant
TOKEN_ENCRYPTION_KEY=...
AUTH_ISSUER=https://your-auth-provider/
AUTH_AUDIENCE=spendant-api
AUTH_JWKS_URL=https://your-auth-provider/.well-known/jwks.json
PLAID_CLIENT_ID=...
PLAID_SECRET=...
```

Apply Postgres schema migrations:

```bash
alembic upgrade head
```

Protected routes require `Authorization: Bearer <jwt>` outside local development.
The iOS app stores the session token in Keychain and attaches it automatically.

## Environment Errors

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

This stores the Plaid Item server-side with an encrypted access token. The API
response does not include the raw Plaid access token.

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
- `GET /health` and `GET /health/ready`
- Managed JWT authentication for staging/production
- Real Plaid link token creation with webhook registration
- Real Plaid public token exchange with encrypted token storage
- Local SQLite storage for linked Plaid Items (Postgres-ready via Alembic)
- Real Plaid accounts, balances, and transaction sync endpoints
- Plaid webhook endpoint with idempotent event storage
- Multi-bank support: multiple Plaid Items per user with institution metadata
- Dashboard summary endpoint with rule-based Spendant buckets
- Structured request logging and stable API error codes
- Docker image and GitHub Actions CI
- Environment-based configuration
