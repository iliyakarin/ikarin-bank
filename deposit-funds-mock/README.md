# Deposit Funds Mock

Mock service simulating external deposit/top-up providers (Stripe-like).

## Stack
- FastAPI

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/deposit` | Simulate a deposit into a user account |

## Usage
- Called by `backend/services/deposit_service.py`
- Part of the Docker Compose stack — no standalone usage needed
