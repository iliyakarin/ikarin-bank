# Karin Bank Financial Precision Policy

> [!IMPORTANT]
> **Floating-point arithmetic (using `float` or `double`) and standard `round()` functions are STRICTLY PROHIBITED for financial calculations and data storage in Karin Bank.**

## Core Principles

1.  **All Internal Representation in Cents**: Every currency value MUST be handled as an integer representing the total amount in cents (e.g., $10.00 is represented as `1000`).
2.  **Integer Arithmetic Only**: All calculations (addition, subtraction, multiplication for interest/tax) must use integer arithmetic. 
3.  **No Division to Floats**: Use floor division (`//` in Python) if necessary, but ideally, avoid any operation that introduces decimal points until the absolute final formatting layer for the user interface.
4.  **Formatting at View Layer**: Formatting from cents to a "dollar" display string (e.g., `1000` -> `"10.00"`) must be done using string manipulation or dedicated internationalization libraries that avoid floating-point math internally.
5.  **API Consistency**: The backend API MUST return currency values as integers (cents). The frontend hooks MUST treat these values as integers.

## Why?
Floating-point numbers use binary representation (IEEE 754) which cannot accurately represent many base-10 decimals. This leads to cumulative errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). In banking, even a difference of 0.0000000001 is unacceptable.

## Code Constraints for AI Agents
- **FE**: Do not use `Number.toFixed()` for anything other than final display. Prefer a custom `formatCents` utility.
- **BE**: Never cast a database numeric field to `float()`. Use `int()` or keep it as a `Decimal` if using a database driver that supports it, but preference is for raw integers.
