# Karin Bank Test Suites

Comprehensive testing structure covering frontend unit/integration tests, backend domain and integration tests, Federal Reserve mock gateway test suites, ISO 20022 settlement tests, and Playwright end-to-end browser suites.

---

## Directory Overview

```
tests/
├── unit/                      # Fast, isolated unit tests (pytest)
├── integration/               # Database, Kafka, and auth integration tests (pytest)
├── v2/                        # FedLine Direct & ISO 20022 messaging tests
│   ├── banking/               # ABA routing and ACH simulator tests
│   └── fed_gateway/           # pacs.008, pacs.002, camt.053 XML & MQ tests
└── e2e/                       # Playwright browser end-to-end test suite

frontend/__tests__/            # Frontend Component & Neobank Unit Tests (Jest / RTL)
mock-fed-gateway/tests/        # Federal Reserve multi-rail gateway test suite (pytest)
```

---

## 1. Frontend Test Suites (`frontend/__tests__/`)

Modular unit and integration tests verifying neobank components, state management, and role gating:

| Test Suite | Coverage & Test Cases |
|------------|-----------------------|
| `BetweenAccountsTab.test.ts` | Bi-directional account selection, swap source/destination action, available balance checks, quick-amount chips, APY compounding notes, and `/api/v1/accounts/transfer/internal` integration |
| `HeroProductCarousel.test.ts` | Slide transitions between Checking, High-Yield Vault (4.85% APY), and Platinum Card; 1-click copy for routing/account numbers |
| `SimLabDrawer.test.ts` | Strict role-based isolation (unmounted when `role === 'user'`, mounted when `role === 'admin'`), scenario injection triggers |
| `SmartTransferHub.test.ts` | Real-time ABA directory lookup, Mod-10 checksum validation, smart rail selection (FedNow vs Fedwire vs ACH) |
| `AnalyticsStudio.test.ts` | Timeframe filters (24h, 7d, 30d, 90d, 1y), cashflow trends, spending by category, merchant leaderboard |
| `CardSecurityHub.test.ts` | 3D card flip animation, 1-click freeze toggle, spending limit slider adjustments |
| `StoriesBar.test.ts` | Financial highlights rendering, story modal viewer, auto-advance timers |
| `DailyActivityFeed.test.ts` | Chronological date grouping, settlement rail badge styling, receipt modal data extraction |
| `neobank/utils.test.ts` | ABA check-digit math, currency formatting, vault compound interest math |

### Run Frontend Tests:
```bash
cd frontend
npm test
```

---

## 2. Federal Reserve Gateway Tests (`mock-fed-gateway/tests/`)

Validates multi-rail clearing logic, directory checksums, and master account balance accounting:

| Test Suite | Coverage & Test Cases |
|------------|-----------------------|
| `test_routing_utils.py` | Mod-10 ABA check digit algorithm ($3, 7, 1$ weights), Federal Reserve District mapping |
| `test_directory_router.py` | Bank directory queries, routing verification, rail participation flags |
| `test_fedwire_router.py` | Wholesale RTGS execution, IMAD/OMAD generation, daylight reserve deductions |
| `test_fednow_router.py` | 24/7 instant credit settlement, end-to-end identification formatting |
| `test_ach_router.py` | NACHA batch origination, simulated return codes (`R01 NSF` on `.01` amounts, `R03 No Account` on `00000`) |
| `test_settlement_router.py` | Master account reserve ledger, daylight overdraft limits, statement queries |

### Run Fed Gateway Tests:
```bash
cd mock-fed-gateway
pytest tests/ -v
```

---

## 3. Backend Integration Tests (`tests/integration/`)

Verifies core ledger integrity, concurrency, and security policies:
- `test_p2p_transfer.py` — Atomic peer-to-peer transfers and balance consistency.
- `test_account_service.py` — Sub-account creation, ownership checks, and ledger limits.
- `test_turnstile.py` — Cloudflare Turnstile token validation and trusted service key bypasses.
- `test_admin_routes.py` — Privilege verification and balance adjustments.
- `test_security_audit.py` — Protection against unauthorized cross-tenant data access.

### Run Backend Integration Tests:
```bash
pytest tests/integration/ -v
```

---

## 4. End-to-End Browser Tests (`tests/e2e/`)

Full user journey verification executed in headless Chromium using Playwright:
- `auth.spec.ts` — User registration, login, and session persistence.
- `p2p.spec.ts` — End-to-end money transfer between accounts with balance verification.
- `admin_dashboard.spec.ts` — Administrator login, bank-wide transaction ledger, Fed reconciliation.
- `visual_and_smoke_qa.spec.ts` — Visual smoke test verifying obsidian glassmorphism theme and layout integrity.

### Run E2E Tests:
```bash
cd tests/e2e
npx playwright test
```
*(Requires the KarinBank stack running on `http://localhost:3000` or the target test node `http://192.168.11.160`)*
