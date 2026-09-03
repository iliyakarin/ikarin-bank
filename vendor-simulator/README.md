# Vendor Simulator

Mock service simulating third-party bill pay aggregators and utility merchants (power companies, telecom providers, insurers).

## Tech Stack & Architecture

- **Framework:** FastAPI (Python 3.10+)
- **Database:** PostgreSQL 16 (`vendor-simulator-db:5432/vendor_simulator_db`) via SQLAlchemy 2.0 (asyncpg)
- **Service Port:** `8001` (Internal Docker network & local dev)
- **Authentication:** Header `X-API-KEY: ${SIMULATOR_API_KEY}` (required on bill-pay and transactions endpoints)

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/vendors` | None | List available merchants & billing emails (also used for healthcheck) |
| `POST` | `/billpay/validate-subscriber` | `X-API-KEY` | Validate subscriber account ID against vendor directory |
| `POST` | `/billpay/execute` | `X-API-KEY` | Execute and persist a simulated bill payment transaction |
| `GET` | `/transactions` | `X-API-KEY` | List transaction audit log ordered by recent timestamp |

## Seeded Merchants

The simulator automatically seeds default vendors on startup if empty:
1. **Austin Energy** (`austin-energy-1`, Category: `Utilities`)
2. **T-Mobile** (`t-mobile-1`, Category: `Telecommunications`)
3. **GEICO** (`geico-1`, Category: `Insurance`)

## Failure Simulation Rules

- **Invalid Subscriber:** Any `subscriber_id` containing `00000` raises `404 Not Found` with `{"error_code": "INVALID_SUBSCRIBER"}`.
- **Insufficient Funds (NSF):** Any payment `amount` ending in `.01` (e.g. `$75.01`, `$120.01`) settles as `status: "FAILED"` with `failure_reason: "Insufficient Funds"`.
- **Standard Clearing:** All other payments generate a unique UUID `trace_id`, next-day settlement date, and `status: "CLEARED"`.

## Healthcheck Configuration

Configured in `docker-compose.prod.yml`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/vendors')\" || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```
