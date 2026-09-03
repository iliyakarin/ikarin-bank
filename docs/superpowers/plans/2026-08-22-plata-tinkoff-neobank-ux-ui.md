# Plata & Tinkoff Pure Neobank UX/UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform KarinBank into a high-performance, pristine digital neobank inspired by Tinkoff and Plata Bank, with US financial rails (FedNow, Fedwire, FedACH, APY Vaults), real-time ClickHouse analytics, and strict role-based isolation for developer/admin simulation tools.

**Architecture:** Highly modular, atomic React 19 / Next.js 15 components built with Tailwind CSS and Framer Motion. All shared calculations (Mod-10 checksum, ABA directory resolver, date grouping, currency formatting) reside in dedicated pure utility modules following SOLID, DRY, and KISS principles. TDD workflow: write failing unit test -> implement minimal clean component -> verify test passes -> commit.

**Tech Stack:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Framer Motion, Recharts, Lucide Icons, Jest, React Testing Library.

**Spec:** [`docs/superpowers/specs/2026-08-22-plata-tinkoff-neobank-ux-ui-design.md`](file:///home/ikarin/claude/karin-bank/docs/superpowers/specs/2026-08-22-plata-tinkoff-neobank-ux-ui-design.md)

## Global Constraints
- Strictly preserve KarinBank's signature dark glassmorphism theme (`#050510`, `backdrop-filter: blur(24px)`, subtle purple/indigo and emerald glows).
- Do not clutter client views with developer/debug features. All simulation triggers and FRB liquidity meters are strictly restricted to `user.role === 'admin'`.
- All monetary amounts are handled in integer cents in models/APIs and formatted cleanly with currency symbols.
- TDD is mandatory for every component: unit tests in `frontend/__tests__/` must run and pass with `npm test`.

---

### Task 1: Core Pure Neobank Utilities & Helpers

**Files:**
- Create: `frontend/lib/neobank/utils.ts`
- Create: `frontend/lib/neobank/types.ts`
- Test: `frontend/__tests__/neobank/utils.test.ts`

**Interfaces:**
- Produces: 
  - `validateAbaRouting(routing: string): { valid: boolean; district?: string }`
  - `groupTransactionsByDate(events: any[]): Record<string, any[]>`
  - `formatFedRailBadge(rail: string): { label: string; color: string; icon: string }`
  - `calculateVaultYield(balanceCents: number, apyPercent: number): { monthlyCents: number; annualCents: number }`

- [x] **Step 1: Write the failing unit tests for utilities**
- [x] **Step 2: Run `npm test frontend/__tests__/neobank/utils.test.ts` to verify tests fail**
- [x] **Step 3: Implement `frontend/lib/neobank/types.ts` and `frontend/lib/neobank/utils.ts`**
- [x] **Step 4: Run `npm test frontend/__tests__/neobank/utils.test.ts` and verify 100% pass**
- [x] **Step 5: Commit changes**

---

### Task 2: Stories & Financial Highlights Bar (`StoriesBar.tsx` & `StoryViewerModal.tsx`)

**Files:**
- Create: `frontend/components/neobank/StoriesBar.tsx`
- Create: `frontend/components/neobank/StoryViewerModal.tsx`
- Test: `frontend/__tests__/components/StoriesBar.test.tsx`

**Interfaces:**
- Consumes: `useAuth` hook, story items dataset (APY savings, FedNow 24/7, Cashback, FDIC, Weekly Pulse)
- Produces: `StoriesBar` component with interactive modal viewer, timed auto-advance (5s), and CTA callback buttons.

- [x] **Step 1: Write unit tests for `StoriesBar` and `StoryViewerModal`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `StoriesBar.tsx` and `StoryViewerModal.tsx` with Framer Motion transitions**
- [x] **Step 4: Run test to verify all tests pass**
- [x] **Step 5: Commit changes**

---

### Task 3: Interactive Multi-Product Hero Carousel (`HeroProductCarousel.tsx`)

**Files:**
- Create: `frontend/components/neobank/HeroProductCarousel.tsx`
- Create: `frontend/components/neobank/VaultCard.tsx`
- Create: `frontend/components/neobank/DigitalCardPreview.tsx`
- Test: `frontend/__tests__/components/HeroProductCarousel.test.tsx`

**Interfaces:**
- Consumes: `Account[]`, `balance`, `reservedBalance`, copy helpers
- Produces: Swipeable/tabbed carousel with:
  1. Main Checking (balance, 1-tap copy of Routing `123456780` and Account number, visibility toggle).
  2. High-Yield Savings Vault (4.85% APY yield tracker, goal progress).
  3. KarinBank Black Platinum Card (3D tilt, 1-tap CVV reveal with auto-hide timer, freeze badge).

- [x] **Step 1: Write unit tests for `HeroProductCarousel`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `HeroProductCarousel`, `VaultCard`, and `DigitalCardPreview`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 4: Quick Action Hub & Fast Pay Avatars (`QuickActionHub.tsx` & `FastPayCarousel.tsx`)

**Files:**
- Create: `frontend/components/neobank/QuickActionHub.tsx`
- Create: `frontend/components/neobank/FastPayCarousel.tsx`
- Test: `frontend/__tests__/components/QuickActionHub.test.tsx`

**Interfaces:**
- Consumes: `contacts: Contact[]`, onSelectContact, onOpenSend, onOpenDeposit, onOpenBills, onOpenCardControls
- Produces: 4 animated glass action buttons + horizontal favorite contacts scroll with 1-tap payment trigger.

- [x] **Step 1: Write unit tests for `QuickActionHub` and `FastPayCarousel`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `QuickActionHub.tsx` and `FastPayCarousel.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 5: Smart Universal Transfer Hub (`SmartTransferHub.tsx`)

**Files:**
- Create: `frontend/components/transfers/SmartTransferHub.tsx`
- Modify: `frontend/app/client/send/page.tsx`
- Test: `frontend/__tests__/components/SmartTransferHub.test.tsx`

**Interfaces:**
- Consumes: `getAccounts()`, `getContacts()`, `lookupFedRouting()`, `executeTransfer()`
- Produces: Unified search bar that auto-resolves contact vs ABA routing vs biller, auto-recommends FedNow ($0 fee) vs Fedwire ($15 fee) vs ACH, instant keypad chips, and swipe-to-confirm modal.

- [x] **Step 1: Write unit tests for `SmartTransferHub` (auto-routing resolution, fee calculation, submission)**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `SmartTransferHub.tsx` and integrate into `/client/send/page.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 6: Daily Activity Feed & Interactive Digital Receipt (`DailyActivityFeed.tsx` & `ReceiptModal.tsx`)

**Files:**
- Create: `frontend/components/neobank/DailyActivityFeed.tsx`
- Create: `frontend/components/neobank/ReceiptModal.tsx`
- Test: `frontend/__tests__/components/DailyActivityFeed.test.tsx`

**Interfaces:**
- Consumes: `transactions: ActivityEvent[]`, onRepeatPayment
- Produces: Grouped activity feed with brand avatars, rail badges (`⚡ FedNow`, `🏛️ Fedwire`, `⏱️ ACH`, `💳 Card`), and digital watermark receipt modal with IMAD/OMAD, trace IDs, and print/PDF support.

- [x] **Step 1: Write unit tests for `DailyActivityFeed` and `ReceiptModal`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `DailyActivityFeed.tsx` and `ReceiptModal.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 7: Real-Time ClickHouse Analytics & Insights Studio (`/client/analytics`)

**Files:**
- Create: `frontend/components/neobank/AnalyticsStudio.tsx`
- Create: `frontend/app/client/analytics/page.tsx`
- Test: `frontend/__tests__/components/AnalyticsStudio.test.tsx`

**Interfaces:**
- Consumes: Transaction stream, category aggregates, time-range filter (`24h`, `7d`, `30d`, `90d`, `1y`)
- Produces: Multi-dimensional analytics studio:
  - Interactive cashflow trend line/area chart.
  - Category spending donut chart with interactive slice drilldown.
  - Top merchant spending leaderboard with percentage bars.
  - Rail settlement distribution meter (FedNow vs Fedwire vs ACH vs Card).

- [x] **Step 1: Write unit tests for `AnalyticsStudio`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `AnalyticsStudio.tsx` and `frontend/app/client/analytics/page.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 8: Cards & Security Controls Hub (`/client/cards` & `CardSecurityHub.tsx`)

**Files:**
- Create: `frontend/components/neobank/CardSecurityHub.tsx`
- Modify: `frontend/app/client/cards/page.tsx`
- Test: `frontend/__tests__/components/CardSecurityHub.test.tsx`

**Interfaces:**
- Consumes: Card data, security settings, limits
- Produces: 3D card visualizer with flip animation, 1-click Freeze toggle, online spending toggle, ATM withdrawal toggle, spending limit slider, and virtual card generator.

- [x] **Step 1: Write unit tests for `CardSecurityHub`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `CardSecurityHub.tsx` and update `/client/cards/page.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 9: Admin-Exclusive Floating `⚡ Sim Lab` Drawer (`SimLabDrawer.tsx`)

**Files:**
- Create: `frontend/components/admin/SimLabDrawer.tsx`
- Test: `frontend/__tests__/components/SimLabDrawer.test.tsx`

**Interfaces:**
- Consumes: `useAuth` hook (`role === 'admin'`), simulator API triggers, FRB liquidity endpoint
- Produces: Floating pulse trigger `[⚡ Sim Lab]` at bottom-right (strictly unmounted for standard users), slide-over developer drawer with live FRB reserve stats, 1-click scenario triggers (Fedwire inflow, FedNow payment, ACH batch, full day cycle), Kafka/ClickHouse telemetry stream, and database reset.

- [x] **Step 1: Write unit tests for `SimLabDrawer` (verifying role restriction: hidden for `user`, visible for `admin`)**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Implement `SimLabDrawer.tsx` with role guard**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 10: Client Dashboard Integration & Navigation Refinement (`/client/page.tsx` & `Sidebar.tsx`)

**Files:**
- Modify: `frontend/app/client/page.tsx`
- Modify: `frontend/components/Sidebar.tsx`
- Modify: `frontend/app/client/layout.tsx`
- Test: `frontend/__tests__/pages/ClientDashboard.test.tsx`

**Interfaces:**
- Integrates `StoriesBar`, `HeroProductCarousel`, `QuickActionHub`, `FastPayCarousel`, `DailyActivityFeed`, and `SimLabDrawer` into a unified, responsive client experience.
- Updates sidebar and mobile navigation with direct links to Analytics Studio (`/client/analytics`).

- [x] **Step 1: Write integration tests for `ClientDashboard`**
- [x] **Step 2: Run test to verify failure**
- [x] **Step 3: Update `page.tsx`, `Sidebar.tsx`, and `layout.tsx`**
- [x] **Step 4: Run test and verify pass**
- [x] **Step 5: Commit changes**

---

### Task 11: End-to-End Test Suite Execution & TypeScript Verification

**Files:**
- Test: Full frontend test suite (`npm test`)
- Test: TypeScript type checker (`npx tsc --noEmit`)
- Test: Backend & Fed Gateway integration test suite (`pytest`)

- [x] **Step 1: Run `npm test -- --coverage` across all frontend components**
- [x] **Step 2: Run `npx tsc --noEmit` in `frontend/` to confirm 0 type errors**
- [x] **Step 3: Run root `pytest` to confirm 114/114 backend & simulator tests remain green**
- [x] **Step 4: Commit and finalize walkthrough**

---

### Task 12: Between-Accounts Internal Transfers, Vault Modal & 45s Auto-Settlement Worker

**Files:**
- Create: `frontend/components/transfers/BetweenAccountsTab.tsx`
- Create: `frontend/components/neobank/VaultTransferModal.tsx`
- Modify: `frontend/app/client/send/page.tsx`
- Modify: `frontend/app/client/page.tsx`
- Modify: `frontend/lib/api/transfers.ts`
- Modify: `frontend/components/neobank/VaultCard.tsx`
- Modify: `frontend/components/neobank/HeroProductCarousel.tsx`
- Modify: `frontend/components/neobank/QuickActionHub.tsx`
- Modify: `backend/sync_checker.py`
- Modify: `backend/outbox_service.py`
- Test: `frontend/__tests__/components/BetweenAccountsTab.test.ts`

**Interfaces:**
- Consumes: `/api/v1/accounts/transfer/internal`, `createInternalTransfer()`, `auto_settle_transactions`
- Produces: Instant between-accounts transfer tab, direct vault deposit/withdrawal modal, and 45s background auto-settlement engine preserving terminal states.

- [x] **Step 1: Write unit tests for `BetweenAccountsTab`**
- [x] **Step 2: Implement `BetweenAccountsTab.tsx` with bi-directional account selectors, swap direction, and quick-chips**
- [x] **Step 3: Implement `VaultTransferModal.tsx` for 1-click deposit/withdrawal with 4.85% APY compounding banner**
- [x] **Step 4: Integrate between-accounts transfer tab into `/client/send` with deep link `?tab=internal`**
- [x] **Step 5: Connect `VaultCard` (Withdraw & Deposit), `StoriesBar`, and `QuickActionHub` to `VaultTransferModal`**
- [x] **Step 6: Implement `auto_settle_transactions` worker in `backend/sync_checker.py` with 15s heartbeat**
- [x] **Step 7: Update `backend/outbox_service.py` to prevent state regression on cleared/settled transactions**
- [x] **Step 8: Run unit test suite and verify 100% pass**

