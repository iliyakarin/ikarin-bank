# Karin Bank Mock Fed Gateway

This service simulates the US Federal Reserve (ACH) and major Bill Pay aggregators for development and testing purposes.

## Features
- **Stateless API**: Validates requests against a "Directory of Truth" (Seeded DB).
- **ACH Simulation**: Supports `POST /fed/ach/originate` with Routing Number validation.
- **Bill Pay Simulation**: Supports `POST /billpay/validate-subscriber` and `POST /billpay/execute`.
- **Failure Injection**:
  - `R01 (NSF)`: Triggered if ACH amount ends in `.01`.
  - `INVALID_SUBSCRIBER`: Triggered if subscriber ID contains `00000`.

## Security Evolution Roadmap
High-integrity simulation of the US Federal Reserve ACH and Wire systems.

## 🏗 Features
- **ACH Origination**: Simulate NACHA-style batch transfers.
- **Bank Directory**: Validates routing numbers against major US entities (Chase, BoA, etc.).
- **Failure Simulation**: Trigger-based returns (e.g., R01 NSF).
- **Security**: Mandatory `X-API-KEY` header validation.

## 🚀 Getting Started
The gateway is part of the Karin Bank ecosystem. Ensure the root `docker-compose.yml` is running.

### API Endpoints
- `POST /fed/ach/originate`: Simulates an ACH transfer.
  - Headers: `X-API-KEY: ${GATEWAY_API_KEY}`
  - Body: `{"routing_number": "...", "account_number": "...", "amount": 100.00}`

### Failure Triggers
- **R01 (NSF)**: Use any amount ending in `.01` (e.g., `100.01`).
- **R03 (No Account)**: Use any account number containing `00000`.

## 🧪 Testing
Run the local test suite (requires `requests`):
```bash
python3 test_api.py
```
