# Vendor Simulator

Mock service simulating third-party bill pay vendors (utilities, telecom, etc.).

## Stack
- FastAPI, SQLite (in-memory)

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/billpay/validate-subscriber` | Validate subscriber ID against vendor directory |
| `POST` | `/billpay/execute` | Execute a simulated vendor payment |
| `GET` | `/vendors` | List available mock vendors |

## Failure Triggers
- Subscriber ID containing `00000` → `INVALID_SUBSCRIBER`
- Amount ending in `.01` → simulated processing failure
