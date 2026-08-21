import re
from typing import Dict, Any, List

ROUTING_REGEX = re.compile(r"^\d{9}$")
WEIGHTS = [3, 7, 1, 3, 7, 1, 3, 7]

def compute_routing_check_digit(digits: str) -> int:
    d8 = digits[:8] if len(digits) >= 8 else digits
    if len(d8) != 8 or not d8.isdigit():
        raise ValueError(f"Expected 8 numeric digits, got '{digits}'")
    
    total = sum(int(d8[i]) * WEIGHTS[i] for i in range(8))
    return (10 - (total % 10)) % 10

def get_district_from_routing(routing_number: str) -> int:
    digits = re.sub(r"\D", "", routing_number)
    if len(digits) < 2:
        return 0
    p = int(digits[:2])
    if 1 <= p <= 12:
        return p
    if 21 <= p <= 29:
        return 2   # NY
    if 30 <= p <= 32:
        return 3   # Philadelphia
    if 61 <= p <= 69:
        return 12  # San Francisco
    if 70 <= p <= 72:
        return 11  # Dallas
    if p == 80:
        return 8   # St. Louis / US Treasury
    if 90 <= p <= 92:
        return 12  # San Francisco
    return 12 if p >= 60 else (p % 12 or 12)

def validate_routing_number(routing_number: str) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(routing_number, str):
        return {"valid": False, "errors": ["Routing number must be a string"], "district_id": 0}
    
    cleaned = routing_number.strip()
    if not ROUTING_REGEX.match(cleaned):
        return {"valid": False, "errors": [f"Expected 9 digits, got '{cleaned}'"], "district_id": 0}
    
    if cleaned == "000000000":
        return {"valid": False, "errors": ["Routing number cannot be all zeros"], "district_id": 0}
    
    expected_check = compute_routing_check_digit(cleaned[:8])
    actual_check = int(cleaned[8])
    if actual_check != expected_check:
        return {
            "valid": False,
            "errors": [f"Invalid check digit: expected {expected_check}, got {actual_check}"],
            "district_id": get_district_from_routing(cleaned),
        }
    
    district_id = get_district_from_routing(cleaned)
    return {
        "valid": True,
        "errors": [],
        "district_id": district_id,
        "check_digit": actual_check,
    }

def format_routing_number(digits: str) -> str:
    clean = re.sub(r"\D", "", digits)
    if len(clean) == 9:
        return f"{clean[:4]}-{clean[4:]}"
    return digits
