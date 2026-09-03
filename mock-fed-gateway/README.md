# Karin Bank Mock Federal Reserve Gateway

High-fidelity simulation of the United States Federal Reserve payment rails and routing infrastructure, built with FastAPI, SQLAlchemy 2.0 (asyncpg), and PostgreSQL (`fed-gateway-db`).

## Core Payment Rails & Capabilities

### 1. E-Payments Routing Directory (`/fed/directory`)
- **12 Federal Reserve Districts:** Authentic routing prefix ranges across all 12 FRB districts (Boston, New York, Philadelphia, Cleveland, Richmond, Atlanta, Chicago, St. Louis, Minneapolis, Kansas City, Dallas, San Francisco).
- **Directory of Truth:** 40+ seeded major national/regional US commercial banks and credit unions (JPMorgan Chase, Bank of America, Wells Fargo, Citibank, US Bank, etc.).
- **Mod-10 ABA Checksum:** Strict Mod-10 check digit verification ($3(d_1+d_4+d_7) + 7(d_2+d_5+d_8) + 1(d_3+d_6+d_9) \equiv 0 \pmod{10}$).
- **Endpoints:**
  - `GET /fed/directory/{routing_number}` — Validate routing number and retrieve bank details & rail participation.
  - `GET /fed/directory/search?q={query}` — Search banks by name or prefix.

### 2. Fedwire® Funds Service (`/fed/fedwire`)
- **Real-Time Gross Settlement (RTGS):** Immediate finality for wholesale, time-critical, and large-value transfers.
- **Tracking Data:** Generates authentic IMAD (Input Message Accountability Data, `YYYYMMDD-FRBNY-000001`) and OMAD identifiers.
- **Business Function Codes:** Supports `CTR` (Customer Transfer) and `BTR` (Bank Transfer).
- **Endpoint:** `POST /fed/fedwire/originate`

### 3. FedNow® Instant Payment Service (`/fed/fednow`)
- **24/7/365 Instant Settlement:** Immediate credit transfer rails with end-to-end identification (`E2E-YYYYMMDD-XXXX`).
- **Sub-Second Processing:** Real-time liquidity validation against sender master account reserve balances.
- **Endpoint:** `POST /fed/fednow/originate`

### 4. FedACH® Batch & Single Origination (`/fed/ach`)
- **NACHA Format Simulation:** Supports standard SEC codes (`PPD`, `CCD`, `WEB`, `TEL`, `CIE`).
- **Return Code Simulation:**
  - `R01 (Insufficient Funds / NSF)`: Triggered when transfer amount ends in `.01` (e.g., `$100.01`).
  - `R03 (No Account / Unable to Locate)`: Triggered when account number contains `00000`.
- **Endpoint:** `POST /fed/ach/originate`

### 5. Fed Master Account & Reserve Ledger (`/fed/master-account`)
- **Reserve Balances:** Real-time ledger tracking KarinBank's reserve balance and daylight overdraft allowances.
- **Account Statements:** Automated statement generation reflecting debits, credits, and closing balances across all three rails.
- **Endpoints:**
  - `GET /fed/master-account/{routing_number}` — Retrieve live balance and overdraft headroom.
  - `GET /fed/statement` — Retrieve consolidated activity statement.

---

## Infrastructure & Service Architecture

| Attribute | Value |
|-----------|-------|
| **Service Port** | `8002` (Internal Docker network & local dev) |
| **Database** | PostgreSQL 16 (`fed-gateway-db:5432/fed_gateway_db`) |
| **Authentication** | Header `X-API-KEY: ${GATEWAY_API_KEY}` |
| **Healthcheck Endpoint** | `GET http://127.0.0.1:8002/health` |
| **Healthcheck Command** | `python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"` |

---

## Diagnostic & Admin Endpoints

- `GET /health` — Service liveness and database connectivity check.
- `GET /fed/status` — Operational status and participation statistics.
- `POST /fed/seed/reset` — Reset institutions and master account balances to clean baseline.

---

## Testing

Run the dedicated test suite:
```bash
cd mock-fed-gateway
pytest tests/ -v
```
Tests verify directory validation, Mod-10 checksum calculation, FedACH returns, Fedwire RTGS processing, FedNow instant transfers, and settlement ledger updates.
