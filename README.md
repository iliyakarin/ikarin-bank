# Karin Bank

A full-stack banking application built with Next.js 15, FastAPI, PostgreSQL, ClickHouse, and Kafka.

## Features

### Banking Capabilities
- **Account Management**: UUID-based account identities with secure encryption
- **Scheduled Payments**: Recurring or one-time orchestration via `transfer_service`
- **P2P Transfers**: Simplified flow using integer-cents for precision
- **Money Requests**: Atomic request/pay cycle with idempotency
- **Transaction History**: Real-time sync between Postgres (ledger) and ClickHouse (analytics)
- **Contact Management**: Reusable contact types (karinbank, merchant, bank)

### System Features
- **Event-Driven Architecture**: Async transaction processing via Kafka
- **Idempotency**: All operations use idempotency keys to prevent duplicates
- **Analytics**: Real-time analytics with ClickHouse
- **Persistent Storage**: All data persists across container restarts
- **User Preferences**: Customize time format (12h/24h) and date format (US/EU)

## Architecture

### Backend Stack
- **FastAPI** (Python) - REST API with thin router handlers
- **PostgreSQL 16** - Primary relational ledger (integers for money, UUIDs for accounts)
- **ClickHouse** - Scalable analytics and audit logs
- **Apache Kafka** - High-throughput event streaming with SASL auth

### Frontend Stack
- **Next.js 15** (App Router) - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Recharts** - Data visualization

### Infrastructure
- **Docker Compose** - Service orchestration
- **Nginx** - Reverse proxy
- **Persistent Volumes** - Data persistence

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Node.js 20+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd karin-bank
   ```

2. **Setup environment**
   ```bash
   cp .env.dev .env
   # The application will automatically use .env based on the ENV variable
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - ClickHouse: http://localhost:8123

## Development

### Backend Development

1. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Access running services**
   ```bash
   docker-compose exec api python main.py
   ```

### Frontend Development

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server**
   ```bash
   npm run dev
   ```

3. **Run tests**
   ```bash
   npx playwright test
   ```

## Database Models

### PostgreSQL Tables
- `users` - User accounts and authentication
- `accounts` - Account records and balances
- `scheduled_payments` - Recurring payment configurations
- `payment_requests` - Money request records
- `contacts` - Contact management
- `transactions` - Transaction ledger
- `idempotency_keys` - Idempotency tracking
- `outbox` - Event publishing outbox

### ClickHouse Analytics
- `transactions` - Transaction analytics and reporting
- `transaction_ledger` - Detailed transaction history

## Configuration

### Environment Variables (.env)

The application uses `backend/config.py` as the source of truth.

```env
# System
ENV=development # or production
JWT_SECRET_KEY=...

# Postgres (Integer cents, UUID accounts)
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=banking_db
POSTGRES_HOST=db

# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=...

# Kafka (SASL Auth)
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_USER=user
KAFKA_PASSWORD=...

# External Integrations
STRIPE_API_KEY=...
STRIPE_WEBHOOK_SECRET=...
SIMULATOR_URL=http://vendor-simulator:8001
```

## Project Structure

```
karin-bank/
├── backend/                # FastAPI application
│   ├── main.py            # API routes and endpoints
│   ├── database.py       # SQLAlchemy models
│   ├── consumer.py        # Kafka consumer
│   ├── scheduled_payments_worker.py
│   ├── outbox_worker.py
│   ├── sync_checker.py
│   ├── account_service.py
│   ├── activity.py
│   └── tests/             # Pytest test suite
├── frontend/              # Next.js application
│   ├── app/             # App Router pages
│   ├── components/      # React components
│   └── tests/          # Playwright E2E tests
├── init-db/            # Database initialization scripts
├── vendor-simulator/    # Vendor payment simulation
├── mock-fed-gateway/   # Federal payment gateway mock
├── nginx.conf         # Nginx configuration
├── docker-compose.yml # Service orchestration
├── .env.dev           # Development environment
└── README.md          # This file
```

## User Roles

- **user** - Regular user with full access
- **admin** - Administrator with elevated privileges
- **restricted_user** - Limited access user

## Key Features

### Security
- Bcrypt password hashing
- JWT authentication with refresh tokens
- Idempotency key management
- SASL_PLAINTEXT for Kafka
- CORS configuration
- Persistent secure storage

### Architecture Patterns
- **Outbox Pattern**: Ensures event consistency
- **Idempotency**: Prevents duplicate operations
- **Async Processing**: Event-driven architecture
- **Microservices**: Separated workers and services

## Testing

### Backend Tests (pytest)
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests (Playwright)
```bash
cd frontend
npx playwright test
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment instructions
- **[PERSISTENCE.md](PERSISTENCE.md)** - Database persistence details
- **[DASHBOARD_IMPLEMENTATION.md](DASHBOARD_IMPLEMENTATION.md)** - Dashboard features
- **[GEMINI.md](GEMINI.md)** - Additional implementation notes

## Database Management

### View logs
```bash
docker-compose logs -f api
docker-compose logs -f consumer
docker-compose logs -f frontend
```

### Access databases
```bash
# PostgreSQL
psql -h localhost -p 5432 -U admin -d banking_db

# ClickHouse
clickhouse-client --host localhost --port 8123
```

### Clean data
```bash
rm -rf ./data/*
docker-compose down -v
docker-compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is proprietary software.

## Support

For issues and questions, please refer to the documentation files or contact the development team.