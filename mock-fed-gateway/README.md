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
Currently, the service uses a simple `X-API-KEY` header for authentication. The roadmap for production hardening includes:
1. **Mutual TLS (mTLS)**: Enforcing client-side certificates for all bank-to-gateway communication. This ensures both identity and encryption at the transport layer.
2. **Signed JWS (JSON Web Signatures)**: Implementation of JWS for payload non-repudiation. Each transaction payload will be signed by the originating bank's private key and verified by the gateway.
3. **OAuth2.0 / Client Credentials**: Transitioning to short-lived JWTs issued by a central Identity Provider (IdP) for internal service-to-service calls.

## Feature Evolution Roadmap
1. **ISO 8583 Simulation**: Implementing a simulator for the ISO 8583 messaging standard to support Debit Card rail simulations (Authorization, Reversal, Clearing).
2. **FedNow Simulation**: Adding real-time payment support (Instant Credit Transfer) to mirror the FedNow service.
3. **Webhooks**: Implementing asynchronous callback notifications for ACH settlement and returns.

## Getting Started
### Running Standalone
```bash
cd mock-fed-gateway
docker compose up -d
docker compose exec mock-fed-gateway python seed.py
```

### API Endpoints
- `POST /fed/ach/originate`: `{ "routing_number": "...", "account_number": "...", "amount": 100.00 }`
- `POST /billpay/validate-subscriber`: `{ "merchant_id": "...", "subscriber_id": "..." }`
- `POST /billpay/execute`: `{ "merchant_id": "...", "subscriber_id": "...", "amount": 50.0 }`
