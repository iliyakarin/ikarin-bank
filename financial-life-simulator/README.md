# Financial Life Simulator

Runs alongside karin-bank and simulates an ongoing "financial life" for two
demo personas, purely by calling the real backend API (no direct DB access) -
so every simulated event goes through the same auth, ownership, and business
logic checks a real user's request would.

## What it simulates

| Event | Cadence | Persona | Amount (default) |
|---|---|---|---|
| Salary deposit | 1st & 15th of each month | `ikarin@admin.com` | $2,500.00 |
| Rent | 1st of each month | `ikarin@admin.com` (debit) | $1,800.00 |
| Car insurance | 5th of each month | `ikarin@admin.com` (debit) | $120.00 |
| One-time merchant purchase | ~15% chance per tick | `ikarin@admin.com` | varies by merchant |
| P2P transfer, both directions | ~5% chance per tick, each direction | `ikarin@admin.com` <-> `ikarin6@example.com` | random $10-$150 |

Default tick interval is 1 hour (`TICK_INTERVAL_SECONDS`).

## Why it needs backend changes

Two gaps in the existing API blocked a pure "standalone client" implementation
(see `backend/routers/auth.py` and `backend/routers/admin.py`):

1. **`POST /auth/login` requires solving a live Cloudflare Turnstile challenge
   in production** - unautomatable. Fixed with a shared-secret header
   (`X-Service-Key`, checked via `_is_trusted_service()`) that lets this
   service bypass it on `/auth/login` and `/auth/register` only. No other
   endpoint is affected; real users are unaffected since they never send this
   header.
2. **No endpoint credits a balance from outside the two-user ledger.** Every
   existing transfer endpoint moves money from one account to another; salary
   needs to originate money. Fixed with `POST /admin/credit`
   (`admin`-role only), which mutates balance directly and records it via
   `emit_transactional_event`, mirroring exactly how
   `services/transfer_service.py` handles P2P transfers.

## Required environment variables

```
API_BASE_URL=http://api:8000          # internal docker network address
ADMIN_EMAIL=...                       # reuses the backend's seeded admin account
ADMIN_PASSWORD=...
SIM_USER2_EMAIL=ikarin6@example.com
SIM_USER2_PASSWORD=...                # auto-registered on first run if missing
SIMULATOR_SERVICE_KEY=...             # must match the backend's SIMULATOR_SERVICE_KEY
```

See `.env.example` at the repo root. Optional tuning: `TICK_INTERVAL_SECONDS`,
`SALARY_AMOUNT_CENTS`, `RENT_AMOUNT_CENTS`, `CAR_INSURANCE_AMOUNT_CENTS`,
`PURCHASE_CHANCE_PER_TICK`, `P2P_CHANCE_PER_TICK`.

## Control API

- `GET /health` - liveness check
- `GET /status` - last tick time, tick interval, recently fired events
- `POST /trigger/{event_type}` - fires one event immediately, ignoring date
  gating. `event_type` is one of `salary`, `rent`, `insurance`, `purchase`,
  `p2p`. Useful mid-demo instead of waiting for the 1st/15th.

Not exposed externally by default - reachable only on the internal docker
network, same as `vendor-simulator` and `mock-fed-gateway`.

## Known limitations

- **Access tokens expire in 15 minutes.** The simulator re-authenticates both
  personas at the start of every tick rather than caching tokens, so this
  only matters if a single tick's work somehow took >15 minutes (it won't).
- **No rollback.** A failed step partway through a tick (e.g. salary posts
  but a later purchase call fails) leaves prior effects in place - each event
  type is independent and doesn't roll back siblings.
