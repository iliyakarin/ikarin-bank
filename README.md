# Karin Bank

A modern, high-performance digital neobank platform built with Next.js 15 (React 19), FastAPI, PostgreSQL 16, ClickHouse, and Apache Kafka. Featuring authentic US banking rails (Fedwire RTGS, FedNow 24/7 instant settlement, FedACH), an autonomous financial life simulator, real-time analytics, and a signature dark glassmorphism aesthetic inspired by Tinkoff and Plata Bank.

---

## Key Features

### Banking & Neobank Capabilities
- **Between-Accounts Internal Transfers:** Instant movement between checking, sub-accounts, and savings vaults with 1-click direction swap, available balance checks, and quick-amount chips.
- **High-Yield Savings Vaults (4.85% APY):** Dedicated vaults with daily compounding interest, goal tracking, and direct 1-tap Deposit & Withdrawal modals.
- **Interactive Neobank UI Suite:**
  - **Stories & Financial Highlights:** Timed auto-advancing slides covering APY vaults, FedNow instant rails, cashback, and FDIC protection.
  - **Multi-Product Hero Carousel:** Swipeable cards for Primary Checking, High-Yield Vault, and Black Platinum card with 3D tilt and 1-tap CVV reveal.
  - **Quick Action Hub & Fast Pay:** 1-tap glass action buttons and favorite avatars with pre-filled payment sheets.
  - **Daily Activity Feed & Receipts:** Chronologically grouped transactions with rail badges (`⚡ FedNow`, `🏛️ Fedwire`, `⏱️ FedACH`, `💳 Debit Card`) and authentic digital watermark receipts with full reference IDs.
- **Real-Time ClickHouse Analytics Studio (`/client/analytics`):** Dynamic timeframe filtering (`24h`, `7d`, `30d`, `90d`, `1y`), cashflow trends, spending by category, merchant leaderboards, and rail distribution meters.
- **Admin Banking Governance (`/admin`):** Bank-wide transaction audit ledger, real-time banking metrics, and Federal Reserve reconciliation controls.
- **Developer `⚡ Sim Lab` Drawer:** Floating drawer role-gated strictly to administrators (`role: "admin"`) for live Federal Reserve Master Account liquidity inspection and 1-click scenario injection.

### Reliability & Infrastructure Patterns
- **45-Second Auto-Settlement Engine:** Background worker (`backend/sync_checker.py`) that monitors in-flight transactions and transitions them to `cleared` status with outbox event synchronization.
- **Transactional Outbox Pattern:** Guarantees event delivery to Kafka without distributed transactions or state loss, preserving terminal settlement states.
- **Integer Cents Precision:** Strict monetary policy storing all currency as integers (cents), eliminating floating-point rounding errors.
- **Mod-10 ABA Routing Validation:** Real-time routing number directory lookup with official Federal Reserve District resolution and checksum verification.
- **Hardened Healthchecks:** Container healthchecks bound to `127.0.0.1` via Python `urllib.request` to prevent IPv6 DNS resolution issues and autoheal restart loops.

---

## Service Architecture & Ports

```
+----------------------------------------------------------------------------------------------------+
|                                      Karin Bank Ecosystem                                          |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ Frontend (Next.js 15) ] --------------------> [ Nginx Reverse Proxy ]                           |
|       Port 3000                                          Port 80 / 443                             |
|                                                                |                                   |
|                                                                v                                   |
|                                                     [ Backend API (FastAPI) ]                      |
|                                                              Port 8000                             |
|                                                                |                                   |
|               +-----------------------+------------------------+-----------------------+           |
|               |                       |                        |                       |           |
|               v                       v                        v                       v           |
|      [ PostgreSQL 16 ]       [ ClickHouse ]            [ Apache Kafka ]       [ Sync Checker ]     |
|          Port 5432              Port 8123                 Port 9092              (45s Worker)      |
|                                                                |                                   |
|                                                                v                                   |
|                                                     [ Transaction Consumer ]                       |
|                                                                                                    |
|  [ Autonomous Simulators & Mock Rails ]                                                            |
|  ├── mock-fed-gateway (Port 8002)     : Fedwire RTGS, FedNow 24/7, FedACH, 12 FRB Districts        |
|  ├── vendor-simulator (Port 8001)     : Bill-pay aggregator (Utilities, Telecom, Insurance)       |
|  ├── financial-life-simulator (8004)  : Autonomous persona lifecycle engine (300s tick cadence)   |
|  └── deposit-funds-mock (Port 8003)   : External top-up mock provider                              |
+----------------------------------------------------------------------------------------------------+
```

### Microservices Port Allocation

| Service | Container Name | Port | Healthcheck Endpoint | Description |
|---------|----------------|------|----------------------|-------------|
| **Frontend** | `bank-frontend` | `3000` | `GET /` | Next.js 15 neobank client & admin portal |
| **Backend API** | `bank-api` | `8000` | `GET /docs` | FastAPI core banking REST engine |
| **Vendor Simulator** | `bank-vendor-simulator` | `8001` | `GET /vendors` | Third-party bill pay aggregator |
| **Mock Fed Gateway** | `bank-fed-gateway` | `8002` | `GET /health` | US Federal Reserve multi-rail simulator |
| **Deposit Mock** | `deposit-funds-mock` | `8003` | `GET /` | Mock debit/card deposit provider |
| **Financial Simulator** | `bank-financial-life-simulator` | `8004` | `GET /status` | Background autonomous transaction engine |
| **ClickHouse** | `bank-clickhouse` | `8123` / `9000` | `GET /ping` | High-throughput analytics engine |
| **PostgreSQL** | `bank-postgres` | `5432` | `pg_isready` | Relational ledger of record |
| **Kafka Broker** | `bank-kafka` | `9092` | Broker check | Event streaming bus with SASL auth |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.10+

### Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/iliyakarin/ikarin-bank.git
   cd karin-bank
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Ensure required secrets and keys are populated (see SETUP_ENV.md)
   ```

3. **Launch the stack:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - **Frontend Application:** `http://localhost:3000` (or `http://192.168.11.160`)
   - **Interactive API Docs:** `http://localhost:8000/docs`
   - **ClickHouse HTTP Interface:** `http://localhost:8123`
   - **Federal Reserve Gateway:** `http://localhost:8002/health`
   - **Financial Life Simulator:** `http://localhost:8004/status`

---

## Testing

```bash
# Backend unit & integration tests
pytest tests/integration/ -v

# Frontend component & neobank unit tests
cd frontend && npm test

# Federal Reserve Gateway tests
cd mock-fed-gateway && pytest tests/ -v

# End-to-end browser tests
cd tests/e2e && npx playwright test
```

---

## Database Management & Operations

```bash
# PostgreSQL CLI
psql -h localhost -p 5432 -U admin -d banking_db

# ClickHouse Client
clickhouse-client --host localhost --port 8123

# Container Logs
docker-compose logs -f api
docker-compose logs -f consumer
docker-compose logs -f sync-checker
docker-compose logs -f financial-life-simulator
```

---

## Documentation Links

- **[PROJECT-DOCUMENTATION.md](PROJECT-DOCUMENTATION.md)** — Architectural blueprint & domain reference
- **[SETUP_ENV.md](SETUP_ENV.md)** — Detailed environment variable guide
- **[SECURITY.md](SECURITY.md)** — Vulnerability reporting and security controls
- **[docs/financial_precision_policy.md](docs/financial_precision_policy.md)** — Integer-cents monetary policy
- **[docs/superpowers/specs/2026-08-22-plata-tinkoff-neobank-ux-ui-design.md](docs/superpowers/specs/2026-08-22-plata-tinkoff-neobank-ux-ui-design.md)** — Plata & Tinkoff Neobank UX/UI design specification
- **[frontend/README.md](frontend/README.md)** — Frontend component catalog and routing
- **[mock-fed-gateway/README.md](mock-fed-gateway/README.md)** — Federal Reserve multi-rail gateway guide
- **[financial-life-simulator/README.md](financial-life-simulator/README.md)** — Autonomous persona engine guide
- **[vendor-simulator/README.md](vendor-simulator/README.md)** — Bill pay aggregator simulator guide
- **[scripts/DEPLOY-AGENT.md](scripts/DEPLOY-AGENT.md)** — Automated VM deployment agent architecture