"""Static content describing the simulated financial life."""
import random

MERCHANTS = [
    {"name": "Whole Foods Market", "category": "groceries", "min_cents": 2500, "max_cents": 14000},
    {"name": "Trader Joe's", "category": "groceries", "min_cents": 1500, "max_cents": 8000},
    {"name": "Blue Bottle Coffee", "category": "dining", "min_cents": 400, "max_cents": 1200},
    {"name": "Chipotle", "category": "dining", "min_cents": 900, "max_cents": 1800},
    {"name": "Shell Gas Station", "category": "transport", "min_cents": 3000, "max_cents": 7000},
    {"name": "Uber", "category": "transport", "min_cents": 800, "max_cents": 4000},
    {"name": "Netflix", "category": "subscription", "min_cents": 1599, "max_cents": 1599},
    {"name": "Spotify", "category": "subscription", "min_cents": 1099, "max_cents": 1099},
    {"name": "Amazon", "category": "shopping", "min_cents": 1500, "max_cents": 12000},
    {"name": "Target", "category": "shopping", "min_cents": 2000, "max_cents": 9000},
    {"name": "AMC Theatres", "category": "entertainment", "min_cents": 1200, "max_cents": 4000},
    {"name": "24 Hour Fitness", "category": "health", "min_cents": 4999, "max_cents": 4999},
]

RENT_MERCHANT = "Sunset Ridge Apartments LLC"
CAR_INSURANCE_MERCHANT = "State Farm Insurance"
SALARY_SOURCE = "Acme Corp Payroll"

P2P_MEMOS = [
    "splitting dinner",
    "rent contribution",
    "paying you back",
    "concert tickets",
    "thanks!",
    "for the trip",
]


def random_merchant() -> dict:
    return random.choice(MERCHANTS)


def random_amount(merchant: dict) -> int:
    return random.randint(merchant["min_cents"], merchant["max_cents"])
