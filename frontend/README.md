# Frontend — Next.js 15 Pure Neobank

World-class digital neobank interface inspired by Tinkoff and Plata Bank, adapted for US financial rails (Fedwire RTGS, FedNow instant settlement, FedACH, and APY Vaults), built with Next.js 15, React 19, TypeScript, Tailwind CSS, and Framer Motion.

---

## Tech Stack

- **Framework:** Next.js 15 (App Router)
- **UI Library:** React 19
- **Type Safety:** TypeScript (strict mode, `npx tsc --noEmit` verified)
- **Styling:** Tailwind CSS with custom glassmorphism design tokens (`#050510` obsidian background, `backdrop-filter: blur(24px)`)
- **Micro-Animations:** Framer Motion
- **Data Visualization:** Recharts
- **Session & Auth:** JWT tokens stored in secure cookies, managed via `AuthContext`

---

## Route Structure

```
app/
├── auth/
│   ├── login/                 # Login with Cloudflare Turnstile CAPTCHA
│   └── register/              # Self-service account registration
├── client/                    # Authenticated Client Neobank Experience
│   ├── page.tsx               # Main Dashboard (Stories, Hero Carousel, Quick Actions, Fast Pay, Activity Feed)
│   ├── accounts/              # Sub-Accounts & High-Yield Vaults manager
│   ├── activity/              # Chronological activity history with PDF/print receipt modal
│   ├── analytics/             # Real-Time ClickHouse Analytics Studio (Cashflow, Categories, Rails)
│   ├── cards/                 # 3D Card visualizer, security freeze, and spending limits
│   ├── contacts/              # Reusable contact directory (KarinBank, Merchant, Wire)
│   ├── deposit/               # Inbound funding instructions and top-up
│   ├── profile/               # User preferences (12h/24h time, US/EU date format)
│   └── send/                  # Universal transfers (P2P, ACH, Fedwire, FedNow, and Between-Accounts tab)
└── admin/                     # Administrator Portal (role: "admin" only)
    ├── page.tsx               # Bank-wide analytics, FRB reconciliation, and transaction audit ledger
    └── users/                 # RBAC user management and privileges
```

---

## Component Architecture

```
components/
├── neobank/                   # Pure Neobank UI Suite
│   ├── StoriesBar.tsx         # Stories highlights bar (Vaults, FedNow, Cashback, FDIC)
│   ├── StoryViewerModal.tsx   # Full-screen auto-advancing story modal with action CTAs
│   ├── HeroProductCarousel.tsx# Swipeable carousel (Checking, High-Yield Vault, Platinum Card)
│   ├── VaultCard.tsx          # 4.85% APY yield tracker, goal progress, and Deposit/Withdraw buttons
│   ├── VaultTransferModal.tsx # Dedicated 1-click High-Yield Vault deposit & withdrawal modal
│   ├── DigitalCardPreview.tsx # Interactive 3D card tilt with 1-tap CVV reveal & auto-hide timer
│   ├── QuickActionHub.tsx     # 4 circular animated glass quick action buttons
│   ├── FastPayCarousel.tsx    # Favorite avatars with instant transfer bottom-sheet
│   ├── DailyActivityFeed.tsx  # Grouped daily activity feed with settlement rail badges
│   ├── ReceiptModal.tsx       # Official digital watermark receipt with IMAD/OMAD & full ref IDs
│   ├── AnalyticsStudio.tsx    # Interactive multi-dimensional ClickHouse spending studio
│   └── CardSecurityHub.tsx    # 3D card flip visualizer, instant freeze toggle, and limit slider
│
├── transfers/                 # Transfer Engines & Input Forms
│   ├── BetweenAccountsTab.tsx # Instant between-accounts internal transfers with swap button
│   ├── SmartTransferHub.tsx   # Universal input with Mod-10 ABA check & smart rail selector
│   ├── InstantTransferTab.tsx # P2P direct transfer form
│   ├── ScheduledTransferTab.tsx# Recurring payment orchestration
│   └── RequestTransferTab.tsx # Idempotent money requests
│
├── admin/                     # Developer & Admin Tools
│   ├── SimLabDrawer.tsx       # Role-gated floating drawer (⚡ Sim Lab) for FRB reserve control
│   └── UserManagement.tsx     # Role modification and account status controls
│
└── ui/                        # Shared UI primitives (Buttons, Inputs, Modals, Badges, Turnstile)
```

---

## API Layer (`lib/api/`)

All HTTP interactions route through typed client helpers wrapping the backend API:

| API Module | Key Endpoints & Capabilities |
|------------|------------------------------|
| `api/transfers.ts` | `createInternalTransfer` (`/api/v1/accounts/transfer/internal`), `lookupFedRouting` (`/api/v1/fed/directory`), `originateFedWire` (`/api/v1/fed/fedwire`), `originateFedNow` (`/api/v1/fed/fednow`), `getFedMasterBalance`, `getFedStatement`, P2P & scheduled transfers |
| `api/accounts.ts` | Multi-account CRUD, sub-account creation, balance inspection |
| `api/activity.ts` | ClickHouse-backed analytics and transaction event feeds |
| `api/auth.ts` | Login, registration, token refresh, logout |
| `api/contacts.ts` | Contact directory management and beneficiary validation |
| `api/deposits.ts` | Direct deposit and mock top-up workflows |

---

## Key Design & Engineering Standards

1. **Integer Cents Precision:** Monetary values are strictly managed as integers (cents) in state and APIs. Formatting uses `formatCurrency()` from `lib/transactionUtils.ts` (or `lib/neobank/utils.ts`) without floating-point drift.
2. **Role-Based Feature Isolation:** Regular consumers (`role: "user"`) experience a distraction-free neobank interface with zero debug elements. Floating simulator drawers (`SimLabDrawer`) and admin tools are strictly role-gated to `role: "admin"`.
3. **Professional Banking Statuses:** UI renders authentic financial settlement states (`Cleared`, `Settled`, `Processing`) and avoids internal engineering queue terms (`sent_to_kafka`). Transaction reference IDs are rendered fully in receipts without truncation.
4. **Deep Linking:** Transfers page `/client/send` supports tab navigation via URL parameters (e.g. `/client/send?tab=internal` for between-accounts transfers).

---

## Testing

```bash
# Component unit & integration tests
npm test

# TypeScript type checking
npx tsc --noEmit

# End-to-end browser tests
npx playwright test
```
