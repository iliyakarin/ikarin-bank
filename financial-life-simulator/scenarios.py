"""Static content and scenarios describing a realistic simulated financial life."""
import random
from typing import Optional

# Retail and daily spending merchants
MERCHANTS = [
    # Morning / Coffee & Breakfast
    {"name": "Blue Bottle Coffee", "category": "dining", "min_cents": 450, "max_cents": 1250, "time_slot": "morning"},
    {"name": "Starbucks", "category": "dining", "min_cents": 525, "max_cents": 1400, "time_slot": "morning"},
    # Lunch & Quick Bites
    {"name": "Chipotle Mexican Grill", "category": "dining", "min_cents": 1150, "max_cents": 2100, "time_slot": "day"},
    {"name": "Sweetgreen", "category": "dining", "min_cents": 1450, "max_cents": 2400, "time_slot": "day"},
    {"name": "Shake Shack", "category": "dining", "min_cents": 1200, "max_cents": 2600, "time_slot": "day"},
    # Groceries (higher on weekends)
    {"name": "Whole Foods Market", "category": "groceries", "min_cents": 3500, "max_cents": 16500, "time_slot": "any"},
    {"name": "Trader Joe's", "category": "groceries", "min_cents": 2200, "max_cents": 9500, "time_slot": "any"},
    {"name": "HEB Grocery", "category": "groceries", "min_cents": 2800, "max_cents": 12000, "time_slot": "any"},
    # Transportation & Gas
    {"name": "Shell Gas Station", "category": "transport", "min_cents": 3500, "max_cents": 6800, "time_slot": "day"},
    {"name": "Chevron", "category": "transport", "min_cents": 3000, "max_cents": 6500, "time_slot": "day"},
    {"name": "Uber", "category": "transport", "min_cents": 1150, "max_cents": 4200, "time_slot": "any"},
    {"name": "Lyft", "category": "transport", "min_cents": 950, "max_cents": 3800, "time_slot": "any"},
    # Subscriptions & Digital
    {"name": "Netflix", "category": "subscription", "min_cents": 1599, "max_cents": 1599, "time_slot": "any"},
    {"name": "Spotify", "category": "subscription", "min_cents": 1099, "max_cents": 1099, "time_slot": "any"},
    {"name": "Apple Services", "category": "subscription", "min_cents": 999, "max_cents": 2999, "time_slot": "any"},
    # Shopping & Home
    {"name": "Amazon", "category": "shopping", "min_cents": 1800, "max_cents": 14500, "time_slot": "any"},
    {"name": "Target", "category": "shopping", "min_cents": 2400, "max_cents": 9800, "time_slot": "any"},
    # Entertainment & Fitness
    {"name": "AMC Theatres", "category": "entertainment", "min_cents": 1600, "max_cents": 4800, "time_slot": "evening"},
    {"name": "24 Hour Fitness", "category": "health", "min_cents": 4999, "max_cents": 4999, "time_slot": "any"},
]

# Fixed recurring monthly expenses
RENT_MERCHANT = "Sunset Ridge Apartments LLC"
CAR_INSURANCE_MERCHANT = "State Farm Insurance"
SALARY_SOURCE = "Acme Corp Payroll"

# Monthly utilities & telecom bills (handled via vendor payment / p2p with subscriber ID)
UTILITY_BILLS = [
    {
        "name": "Austin Energy",
        "category": "Utilities",
        "email": "billing@austinenergy.com",
        "subscriber_id": "AE-982143",
        "min_cents": 8500,
        "max_cents": 15500,
        "day": 10,
    },
    {
        "name": "T-Mobile",
        "category": "Telecommunications",
        "email": "billing@t-mobile.com",
        "subscriber_id": "TM-552910",
        "min_cents": 7500,
        "max_cents": 9500,
        "day": 18,
    },
    {
        "name": "Comcast",
        "category": "Telecommunications",
        "email": "billing@comcast.com",
        "subscriber_id": "CC-104928",
        "min_cents": 7000,
        "max_cents": 7000,
        "day": 12,
    },
]

# External card deposit sources
CARD_DEPOSIT_SCENARIOS = [
    {"source": "Freelance Consulting Invoice", "min_cents": 35000, "max_cents": 95000},
    {"source": "Family Gift / Birthday Transfer", "min_cents": 10000, "max_cents": 25000},
    {"source": "Expense Reimbursement", "min_cents": 12000, "max_cents": 45000},
    {"source": "Online Marketplace Sale (eBay/Craigslist)", "min_cents": 5000, "max_cents": 18000},
]

# P2P Memos
P2P_MEMOS = [
    "splitting dinner at Sweetgreen",
    "rent contribution",
    "paying you back for groceries",
    "concert tickets split",
    "thanks for lunch!",
    "road trip gas contribution",
    "movie night tickets",
    "coffee run ☕",
]

# Payment Request Scenarios
PAYMENT_REQUEST_SCENARIOS = [
    {"purpose": "Dinner split at Chipotle", "min_cents": 1250, "max_cents": 2400},
    {"purpose": "Uber ride home", "min_cents": 1400, "max_cents": 2800},
    {"purpose": "Groceries from Trader Joe's", "min_cents": 2200, "max_cents": 4500},
    {"purpose": "Group birthday gift split", "min_cents": 2500, "max_cents": 5000},
]


def random_merchant(time_slot: Optional[str] = None, is_weekend: bool = False) -> dict:
    if time_slot:
        candidates = [m for m in MERCHANTS if m["time_slot"] in (time_slot, "any")]
        if candidates:
            return random.choice(candidates)
    return random.choice(MERCHANTS)


def random_amount(merchant: dict, multiplier: float = 1.0) -> int:
    base = random.randint(merchant["min_cents"], merchant["max_cents"])
    return int(base * multiplier)

