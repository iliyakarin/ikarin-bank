# High-Fidelity US Federal Reserve Mock Gateway Design Specification

## Overview
This specification details the architecture, data models, API endpoints, and validation logic for the enhanced **`mock-fed-gateway`** service. The goal is to provide Karin Bank with a realistic, high-integrity simulation of the United States Federal Reserve System banking rails:
1. **FedACH®** (Automated Clearing House file & batch transfers with standard NACHA return codes R01-R29).
2. **Fedwire® Funds Service** (Real-Time Gross Settlement / RTGS with IMAD/OMAD tracking, Business Function Codes CTR/BTR, and daylight reserve accounting).
3. **FedNow® Service** (24/7/365 instant payments and Request-for-Payment flows).
4. **E-Payments Routing Directory** (All 12 Federal Reserve Districts, 40+ authentic national/regional US banks & credit unions, and Mod-10 ABA routing checksum validation).
5. **Fed Master Account Settlement Ledger** (Depository institution reserve accounts and statement summaries).

---

## 1. System Architecture & Components

```
+-----------------------------------------------------------------------------------+
|                            Mock Federal Reserve Gateway                           |
|                                (FastAPI / Port 8002)                              |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +---------------------------+  +--------------------------+  +----------------+  |
|  | E-Payments Directory      |  | FedACH Engine            |  | Fedwire RTGS   |  |
|  | - 12 Fed Districts        |  | - Single & Batch ACH     |  | - IMAD / OMAD  |  |
|  | - 40+ US Banks/CUs        |  | - NACHA Return Codes     |  | - CTR/BTR Fnc  |  |
|  | - ABA Mod-10 Checksum     |  | - Settlement Windows     |  | - RTGS Balance |  |
|  +---------------------------+  +--------------------------+  +----------------+  |
|                                                                                   |
|  +---------------------------+  +--------------------------+  +----------------+  |
|  | FedNow Instant Rails      |  | Master Account Ledger    |  | Admin & Health |  |
|  | - 24/7 Credit Transfers   |  | - Reserve Balances       |  | - Diagnostics  |  |
|  | - Request for Payment     |  | - Daylight Overdraft     |  | - Re-seeding   |  |
|  | - Sub-second Settlement   |  | - Daily Statements       |  | - Key Auth     |  |
|  +---------------------------+  +--------------------------+  +----------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                PostgreSQL Database                                |
|                                (fed-gateway-db:5432)                              |
+-----------------------------------------------------------------------------------+
|  - fed_districts                                                                  |
|  - institutions (banks & routing transit numbers)                                 |
|  - master_accounts (reserve balances & overdraft limits)                          |
|  - ach_transactions & ach_batches                                                 |
|  - fedwire_transfers                                                              |
|  - fednow_transfers                                                               |
+-----------------------------------------------------------------------------------+
```

---

## 2. Database Schema (`mock-fed-gateway/models.py`)

### 2.1. `FederalReserveDistrict`
Represents the 12 Federal Reserve Districts.
* `id` (`Integer`, Primary Key: 1–12)
* `code` (`String(2)`, e.g., `"01"`, `"02"`, ..., `"12"`)
* `name` (`String(100)`, e.g., `"Federal Reserve Bank of New York"`)
* `district_letter` (`String(1)`, e.g., `"B"`)
* `head_office_city` (`String(50)`, e.g., `"New York"`)
* `head_office_state` (`String(2)`, e.g., `"NY"`)
* `routing_prefix_ranges` (`JSON`, e.g., `["02", "21", "22", "23", "24", "25", "26", "27", "28", "29"]`)

### 2.2. `Institution`
Directory of truth for depository financial institutions holding ABA Routing Transit Numbers (RTNs).
* `routing_number` (`String(9)`, Primary Key, Unique, Indexed)
* `name` (`String(255)`, e.g., `"JPMorgan Chase Bank, N.A."`)
* `short_name` (`String(50)`, e.g., `"CHASE NY"`)
* `district_id` (`Integer`, ForeignKey to `fed_districts.id`)
* `office_code` (`String(1)`, `"O"` = Main Office, `"B"` = Branch)
* `servicing_frb_number` (`String(9)`, Servicing Federal Reserve Routing Number)
* `address` (`String(255)`)
* `city` (`String(100)`)
* `state` (`String(2)`)
* `zip_code` (`String(10)`)
* `phone` (`String(20)`)
* `fedach_participant` (`Boolean`, default True)
* `fedwire_participant` (`Boolean`, default True)
* `fednow_participant` (`Boolean`, default True)
* `settlement_only` (`Boolean`, default False)
* `status` (`String(20)`, `"ACTIVE"`, `"SUSPENDED"`, `"IN_RECEIVERSHIP"`)
* `created_at` (`DateTime(timezone=True)`)
* `updated_at` (`DateTime(timezone=True)`)

### 2.3. `MasterAccount`
Simulated Federal Reserve Master Account / Reserve Balances.
* `id` (`Integer`, Primary Key, autoincrement)
* `account_number` (`String(30)`, Unique, e.g., `"FRB-021000021-01"`)
* `routing_number` (`String(9)`, ForeignKey to `institutions.routing_number`, Unique)
* `currency` (`String(3)`, default `"USD"`)
* `balance_cents` (`BigInteger`, default `1000000000` = $10M)
* `daylight_overdraft_limit_cents` (`BigInteger`, default `500000000` = $5M)
* `status` (`String(20)`, `"OPEN"`, `"RESTRICTED"`, `"FROZEN"`)
* `updated_at` (`DateTime(timezone=True)`)

### 2.4. `ACHTransaction`
Records single and batch FedACH origination entries.
* `id` (`String(36)`, Primary Key, UUID)
* `batch_id` (`String(36)`, Optional)
* `sec_code` (`String(3)`, `"PPD"`, `"CCD"`, `"WEB"`, `"TEL"`, `"CIE"`)
* `originator_routing` (`String(9)`)
* `originator_name` (`String(100)`)
* `originator_account` (`String(50)`)
* `receiver_routing` (`String(9)`)
* `receiver_name` (`String(100)`)
* `receiver_account` (`String(50)`)
* `amount_cents` (`Integer`)
* `entry_class` (`String(10)`, `"DEBIT"`, `"CREDIT"`)
* `payment_description` (`String(100)`)
* `status` (`String(20)`, `"SETTLED"`, `"RETURNED"`, `"PENDING"`)
* `return_code` (`String(3)`, Nullable, e.g., `"R01"`, `"R02"`, `"R03"`, `"R04"`, `"R08"`, `"R10"`, `"R16"`)
* `return_reason` (`String(255)`, Nullable)
* `settlement_date` (`Date`)
* `trace_number` (`String(15)`)
* `created_at` (`DateTime(timezone=True)`)

### 2.5. `FedwireTransfer`
Records Fedwire Funds RTGS transfers with IMAD/OMAD identifiers.
* `imad` (`String(24)`, Primary Key, e.g., `"20260821B1Q00000100001"`)
* `omad` (`String(24)`, Unique, e.g., `"20260821B1Q00000100002"`)
* `business_function_code` (`String(3)`, `"CTR"`, `"BTR"`, `"DEP"`, `"DRC"`)
* `sender_routing` (`String(9)`)
* `sender_name` (`String(100)`)
* `sender_account` (`String(50)`)
* `receiver_routing` (`String(9)`)
* `receiver_name` (`String(100)`)
* `receiver_account` (`String(50)`)
* `amount_cents` (`BigInteger`)
* `charge_details` (`String(3)`, `"OUR"`, `"BEN"`, `"SHA"`)
* `payment_reference` (`String(100)`, Optional)
* `status` (`String(20)`, `"SETTLED"`, `"REJECTED"`, `"PENDING_SETTLEMENT"`)
* `rejection_reason` (`String(255)`, Nullable)
* `settlement_timestamp` (`DateTime(timezone=True)`)

### 2.6. `FedNowTransfer`
Records FedNow 24/7 Instant Payments and Requests for Payment.
* `end_to_end_id` (`String(36)`, Primary Key)
* `instruction_id` (`String(36)`)
* `message_type` (`String(20)`, `"CREDIT_TRANSFER"`, `"REQUEST_FOR_PAYMENT"`)
* `debtor_routing` (`String(9)`)
* `debtor_name` (`String(100)`)
* `debtor_account` (`String(50)`)
* `creditor_routing` (`String(9)`)
* `creditor_name` (`String(100)`)
* `creditor_account` (`String(50)`)
* `amount_cents` (`Integer`)
* `status` (`String(10)`, `"ACCP"`, `"RJCT"`, `"PEND"`)
* `status_reason_code` (`String(10)`, Nullable)
* `status_reason_description` (`String(255)`, Nullable)
* `created_at` (`DateTime(timezone=True)`)

---

## 3. Seed Directory Dataset

### 3.1. 12 Federal Reserve Districts
1. **01 - Boston (A)**: MA, ME, NH, RI, VT, CT (portion)
2. **02 - New York (B)**: NY, Northern NJ, Fairfield County CT, PR, VI
3. **03 - Philadelphia (C)**: Eastern PA, Southern NJ, DE
4. **04 - Cleveland (D)**: OH, Western PA, Eastern KY, Northern WV
5. **05 - Richmond (E)**: MD, VA, NC, SC, WV (most), DC
6. **06 - Atlanta (F)**: AL, FL, GA, Eastern TN, Southern MS, Southern LA
7. **07 - Chicago (G)**: Northern IL, Northern IN, IA, Lower MI, Southern WI
8. **08 - St. Louis (H)**: AR, Southern IL, Southern IN, Western KY, Northern MS, Eastern MO, Western TN
9. **09 - Minneapolis (I)**: MN, MT, ND, SD, Upper MI, Northern WI
10. **10 - Kansas City (J)**: CO, KS, NE, OK, WY, Western MO, Northern NM
11. **11 - Dallas (K)**: TX, Northern LA, Southern NM
12. **12 - San Francisco (L)**: AK, AZ, CA, HI, ID, NV, OR, UT, WA, Guam, American Samoa

### 3.2. 40+ Depository Institutions (Authentic US Banks & Routing Numbers)
* **JPMorgan Chase**: `021000021` (New York), `122241255` (California), `071000013` (Illinois)
* **Bank of America**: `111000012` (Texas), `121000358` (California), `053000196` (North Carolina)
* **Wells Fargo Bank**: `121000248` (California), `091000019` (Minnesota), `102000076` (Colorado)
* **Citibank, N.A.**: `021000089` (New York), `321171184` (Delaware)
* **U.S. Bank, N.A.**: `091000022` (Minnesota), `123000848` (Oregon)
* **PNC Bank, N.A.**: `043000096` (Pennsylvania), `071921891` (Illinois)
* **Truist Bank**: `061000104` (Georgia), `053101121` (North Carolina)
* **Goldman Sachs Bank USA**: `026002561` (New York)
* **Morgan Stanley Private Bank**: `026013576` (New York)
* **Capital One, N.A.**: `051405515` (Virginia), `056073573` (Louisiana)
* **TD Bank, N.A.**: `011103093` (Maine), `031201360` (Delaware)
* **The Bank of New York Mellon**: `021000018` (New York)
* **State Street Bank & Trust**: `011000028` (Massachusetts)
* **Charles Schwab Bank, SSB**: `121202211` (Texas)
* **Fidelity / UMB Bank**: `101000695` (Missouri)
* **Navy Federal Credit Union**: `256074974` (Virginia)
* **State Employees' Credit Union**: `253177093` (North Carolina)
* **Pentagon Federal Credit Union**: `256078420` (Virginia)
* **Ally Bank**: `124003116` (Utah)
* **Silicon Valley Bank / First Citizens**: `121140399` (California)
* **M&T Bank**: `022000046` (New York)
* **Fifth Third Bank**: `042000314` (Ohio)
* **KeyBank, N.A.**: `041001039` (Ohio)
* **Citizens Bank, N.A.**: `011500120` (Rhode Island)
* **Regions Bank**: `062000019` (Alabama)
* **Huntington National Bank**: `044000024` (Ohio)
* **BMO Bank, N.A.**: `071000288` (Illinois)
* **First Republic Bank (Historical / Chase)**: `321081669` (California)
* **Karin Bank Node (Local System Member)**: `123400010` & `123456780` (District 12 / San Francisco)

---

## 4. API Endpoints Specification

### 4.1. E-Payments Routing Directory
* `GET /fed/directory/institutions`
  * Query parameters: `q` (name/short_name search), `state`, `district_id`, `fedach_only`, `fedwire_only`, `fednow_only`, `limit`, `offset`.
  * Response: paginated list of institutions with full routing data, district info, and capability flags.
* `GET /fed/directory/routing/{routing_number}`
  * Validates 9-digit ABA routing checksum:
    `[pos 0*3 + pos 1*7 + pos 2*1 + pos 3*3 + pos 4*7 + pos 5*1 + pos 6*3 + pos 7*7 + pos 8*1] mod 10 == 0`.
  * Returns detailed institution data, district letter/name, office code, and service capabilities.
* `GET /fed/districts`
  * Returns array of 12 Federal Reserve Districts with their letters, head offices, and valid prefix lists.
* `GET /banks`
  * Backward compatibility endpoint returning:
    `{"banks": [{"name": str, "routing_number": str}]}`.

### 4.2. FedACH® Origination & Returns
* `POST /fed/ach/originate`
  * Request Body:
    ```json
    {
      "originator_routing": "123400010",
      "originator_name": "Karin Bank Customer",
      "originator_account": "1001001",
      "receiver_routing": "021000021",
      "receiver_name": "John Doe",
      "receiver_account": "9876543210",
      "amount": 15000,
      "sec_code": "PPD",
      "entry_class": "DEBIT",
      "payment_description": "Payroll Direct Deposit"
    }
    ```
  * Deterministic Failure Triggers (NACHA Return Codes):
    * Amount ending in `.01` or `1` cent -> `R01: Insufficient Funds`
    * Amount ending in `.02` or `2` cents -> `R02: Account Closed`
    * Receiver account containing `"00000"` -> `R03: No Account / Unable to Locate Account`
    * Receiver routing not in directory -> `R04: Invalid Routing Number`
    * Amount ending in `.08` or `8` cents -> `R08: Payment Stopped`
    * Amount ending in `.10` or `10` cents -> `R10: Customer Advises Not Authorized`
    * Amount ending in `.16` or `16` cents -> `R16: Account Frozen`
    * Amount ending in `.20` or `20` cents -> `R20: Non-Transaction Account`
    * Header override: `X-Fed-Simulate-Return: R01`
  * Response: Status, Trace Number, Settlement Date, Return Code (if failed).

* `POST /fed/ach/batches`
  * Request Body: File header, Company/Batch header, Array of Entry details.
  * Processes all entries, returns summary (total debits, total credits, settled count, returned count).

* `GET /fed/ach/transactions/{id}`
  * Fetches ACH transaction status and settlement details.

### 4.3. Fedwire® Funds Service (RTGS)
* `POST /fed/wire/originate`
  * Request Body:
    ```json
    {
      "sender_routing": "123400010",
      "sender_name": "Karin Bank",
      "sender_account": "1001001",
      "receiver_routing": "021000021",
      "receiver_name": "Acme Corp",
      "receiver_account": "987654321",
      "amount_cents": 50000000,
      "business_function_code": "CTR",
      "charge_details": "OUR",
      "payment_reference": "INVOICE-98214"
    }
    ```
  * Processing:
    1. Validates sender and receiver routing numbers in Directory.
    2. Verifies sender's Fed Master Account reserve balance (including daylight overdraft headroom).
    3. Generates official IMAD (`YYYYMMDD{SenderDistrict}{Sequence}`) and OMAD (`YYYYMMDD{ReceiverDistrict}{Sequence}`).
    4. Settles reserves immediately between sender and receiver Master Accounts.
  * Response:
    ```json
    {
      "imad": "20260821L1Q00000100001",
      "omad": "20260821B1Q00000100002",
      "status": "SETTLED",
      "business_function_code": "CTR",
      "amount_cents": 50000000,
      "settlement_timestamp": "2026-08-21T19:55:00Z"
    }
    ```

* `GET /fed/wire/transfers/{imad}`
  * Query wire status by IMAD identifier.

### 4.4. FedNow® Instant Payments
* `POST /fed/fednow/transfer`
  * Request Body:
    ```json
    {
      "end_to_end_id": "FEDNOW-20260821-9872134",
      "instruction_id": "INSTR-001239",
      "debtor_routing": "123400010",
      "debtor_name": "Ikarin",
      "debtor_account": "1001001",
      "creditor_routing": "111000012",
      "creditor_name": "Alex",
      "creditor_account": "2002002",
      "amount_cents": 25000,
      "remittance_info": "Dinner split"
    }
    ```
  * Sub-second 24/7/365 response:
    * `ACCP` (Accepted & Settled)
    * `RJCT` (Rejected with ISO 20022 reason code: `AC04` Closed Account, `AM04` Insufficient Funds, `AGNT` Incorrect Routing).

* `POST /fed/fednow/rfp`
  * Request for Payment (RFP) initiation.

* `GET /fed/fednow/transfers/{end_to_end_id}`
  * Query status of FedNow instant payment.

### 4.5. Master Account & Reserve Balances
* `GET /fed/master-account/{routing_number}`
  * Returns reserve balance, available daylight credit, collateral value, account status.
* `POST /fed/master-account/adjust`
  * Simulates reserve adjustments (funding/debiting master account for testing).
* `GET /fed/statements/{routing_number}`
  * Returns daily statement summary of operations (ACH credits/debits, Fedwire debits/credits, FedNow instant debits/credits, opening/closing balance).

### 4.6. Admin & Health
* `GET /health` -> `{"status": "ok", "service": "mock-fed-gateway"}`
* `GET /fed/status` -> General operational statistics (institutions count, transactions counts across ACH/Wire/FedNow).
* `POST /fed/seed/reset` -> Re-populates districts, institutions, and pre-funded master accounts.

---

## 5. Security & Authentication
* Mandatory `X-API-KEY` header validation using `GATEWAY_API_KEY` (configured via `.env.dev` / environment variable).
* CORS configured for development and microservice interop.

---

## 6. Testing & Verification Plan
1. **Automated Unit & Integration Tests (`mock-fed-gateway/tests/`)**:
   * Routing Number ABA Mod-10 Checksum Algorithm test suite.
   * Directory lookup and search queries (filters, pagination, district associations).
   * FedACH Origination with all NACHA return codes (R01, R02, R03, R04, R08, R10, R16, R20).
   * Fedwire Funds RTGS settlement, IMAD/OMAD generator, daylight overdraft limits.
   * FedNow 24/7 Instant payment acceptance (`ACCP`) and rejection (`RJCT`).
   * Master Account balance debit/credit accounting and statement generation.
   * Backward-compatibility verification for `/banks` and existing backend calls.
2. **End-to-End Container Verification**:
   * Rebuild and restart `mock-fed-gateway` container in `docker-compose`.
   * Verify `/health`, `/banks`, `/fed/directory/institutions`, `/fed/ach/originate`, `/fed/wire/originate`, `/fed/fednow/transfer` via `curl`.
   * Confirm backend (`http://api:8000/banks`) proxies cleanly to `mock-fed-gateway`.
