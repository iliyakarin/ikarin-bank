"""
Money formatting utilities for the backend.
Provides safe conversion between cents and dollar strings to avoid floating point precision issues.
"""

def from_cents(cents: int) -> str:
    """
    Safely converts integer cents to a dollar string.
    Avoids floating point precision issues by using integer arithmetic.
    Returns a string with exactly 2 decimal places.

    Args:
        cents: Integer amount in cents

    Returns:
        String representation of dollars with 2 decimal places

    Examples:
        >>> from_cents(12345)
        '123.45'
        >>> from_cents(-12345)
        '-123.45'
        >>> from_cents(100)
        '1.00'
    """
    if cents is None:
        return '0.00'
    
    # Ensure it's an integer
    cents = int(cents)
    is_negative = cents < 0
    abs_cents = abs(cents)

    dollars = abs_cents // 100
    remaining_cents = abs_cents % 100

    result = f"{dollars}.{remaining_cents:02d}"
    return f"-{result}" if is_negative else result


def to_cents(amount: str | int) -> int:
    """
    Safely converts a dollar amount (string) or integer cents to integer cents.
    Avoids floating point precision issues by using string manipulation.

    Args:
        amount: Dollar amount as string or integer cents

    Returns:
        Integer amount in cents

    Examples:
        >>> to_cents("10.50")
        1050
        >>> to_cents("10")
        1000
    """
    if amount is None or amount == '':
        return 0
    
    if isinstance(amount, float):
        raise ValueError("Float amount not allowed in to_cents. Use string or integer cents.")

    if isinstance(amount, int):
        return amount

    # Ensure we have a string, remove commas (if any) and whitespace
    s = str(amount).replace(',', '').strip()

    if not s or s == '.':
        return 0

    parts = s.split('.')
    dollars = parts[0] or '0'
    cents = parts[1] if len(parts) > 1 else '00'

    # Handle negative sign
    is_negative = dollars.startswith('-')
    if is_negative:
        dollars = dollars[1:]

    # Normalize cents to exactly 2 digits
    cents = cents.ljust(2, '0')[:2]

    total_cents = int(dollars) * 100 + int(cents)
    return -total_cents if is_negative else total_cents