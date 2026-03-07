# Karin Bank

Karin Bank is a modern, distributed full-stack banking application built with real-time architectures and robust event-driven patterns. It features capabilities such as peer-to-peer (P2P) transfers, sub-accounts, scheduled recurring payments, and comprehensive activity logging.

## Architecture & Technologies
- **Frontend**: A React/Next.js-based client application delivering a responsive client experience.
- **Backend API**: A Python backend (FastAPI) handling core banking logic, accounts, limits, and user authentication.
- **Transactional Database**: PostgreSQL stores the authoritative ledger, active accounts, payment requests, and transactional states.
- **Event Streaming**: Kafka is utilized alongside the Transactional Outbox pattern to dependably queue system activities, synchronize read models, and process side-effects without slowing down core workflows.
- **Analytics & Audit Logs**: ClickHouse provides blazing-fast ingestion and query performance for the immutable activity events and transaction histories.
- **Background Workers**: Specialized Docker containers (outbox-worker, sync-checker, scheduled-payments-worker, consumer) operate asynchronously to manage background processing and consistency across data stores.

## Getting Started

Run the entire application stack fully containerized using Docker Compose:

```bash
docker compose up -d
```

This will initialize the database schema, spin up the Kafka broker, and launch the API, frontend, and all asynchronous workers.

## Development & Testing

### Running Backend Tests
The backend test suite verifies core banking logic, P2P transfers, security checks, and background workers. Run them using Docker Compose:

```bash
docker compose exec -e PYTHONPATH=. api pytest tests/
```

### Deployment
To rebuild and deploy the services after changes:
```bash
docker compose up --build -d
```

## License

This project is licensed under a non-commercial license. The code and its derivatives may **not** be used for commercial purposes.
