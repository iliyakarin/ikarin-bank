# Frontend — Next.js 15

## Stack
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (strict)
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Auth**: JWT stored in cookies, managed via `AuthContext`

## API Layer

All backend calls go through `lib/api/client.ts` which handles:
- Base URL resolution, auth headers, token refresh
- Typed request/response via Zod schemas

| API Module | Endpoints |
|-----------|-----------|
| `api/auth.ts` | Login, register, logout, token refresh |
| `api/accounts.ts` | Account CRUD, balance queries |
| `api/activity.ts` | Activity feed (ClickHouse-backed) |
| `api/transfers.ts` | P2P, scheduled, payment requests |
| `api/contacts.ts` | Contact management |
| `api/deposits.ts` | Deposit/top-up flows |

## Route Structure

```
app/
├── auth/login/        # Login page
├── auth/register/     # Registration page
├── client/            # Authenticated layout (sidebar + topbar)
│   ├── page.tsx       # Dashboard home
│   ├── accounts/      # Account management
│   ├── activity/      # Activity feed (ClickHouse)
│   ├── cards/         # Card management
│   ├── contacts/      # Contact directory
│   ├── deposit/       # Top-up / deposit
│   ├── profile/       # User settings
│   ├── send/          # Send money (P2P + scheduled + requests)
│   ├── transactions/  # Full transaction history
│   └── transfer/      # Transfer details
```

## Component Organization

```
components/
├── admin/         # Admin panel components (UserManagement)
├── charts/        # Recharts wrappers
├── transfers/     # Transfer-related components
│   ├── AccountSelector, ContactSelector
│   ├── InstantTransferTab, ScheduledTransferTab, RequestTransferTab
│   ├── RecentTransactionsTable, ScheduledHistoryTable
│   └── DetailModal
└── ui/            # Shared UI primitives (Turnstile, etc.)
```

## Key Patterns
- **Money as integer cents**: Backend returns cents. Use `formatCurrency()` from `lib/transactionUtils.ts` for display.
- **Auth context**: `lib/AuthContext.tsx` provides `user`, `login()`, `logout()`, `refreshToken()`.
- **Error logging**: `lib/errorLogger.ts` — centralized error reporting.
- **No inline fetch**: All API calls go through the typed `lib/api/` layer.
