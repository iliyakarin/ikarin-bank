/**
 * ABA Routing Number and Account Number Validation Utilities
 *
 * ABA routing numbers are 9-digit identifiers used in U.S. financial transactions.
 * The 9th digit is a check digit computed via a weighted sum algorithm.
 *
 * Account number check digits vary by institution. This module supports three
 * validation strategies:
 *   - 'none'  — no check digit at all (length validation only)
 *   - 'mod9'  — check digit = sum of all other digits mod 9
 *   - 'mod10' — check digit = digit that makes total sum divisible by 10
 */

// ---------------------------------------------------------------------------
// Regular expression patterns
// ---------------------------------------------------------------------------

export const ROUTING_NUMBER_REGEX = /^\d{9}$/;
export const ACCOUNT_NUMBER_REGEX = /^\d+$/;

// ---------------------------------------------------------------------------
// Validation rules
// ---------------------------------------------------------------------------

/** Allowed routing number lengths (ABA standard is always 9). */
const ROUTING_NUMBER_LENGTH = 9;

/** Minimum account length for any check-digit method. */
const MIN_ACCOUNT_LENGTH = 4;

/** Maximum account length to avoid pathological values. */
const MAX_ACCOUNT_LENGTH = 17;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Supported account-number check-digit strategies. */
export type AccountCheckMethod = 'none' | 'mod9' | 'mod10';

/** Decoded routing number components. */
export interface RoutingInfo {
  /** Is this a thrift institution (Savings/Loan) indicator. */
  thriftIndicator: '1' | '0';
  /** Federal Reserve District (1-12). */
  federalReserveDistrict: number;
  /** Institution type description. */
  institutionType: string;
}

/** Result of validating a routing number. */
export interface RoutingValidationResult {
  valid: boolean;
  errors: string[];
  checkDigit: number;
  expectedCheckDigit?: number;
  federalReserveDistrict?: number;
}

/** Result of validating an account number. */
export interface AccountValidationResult {
  valid: boolean;
  errors: string[];
  checkMethod?: AccountCheckMethod[];
}

/** Combined routing + account validation result. */
export interface PairValidationResult {
  valid: boolean;
  errors: string[];
}

// ---------------------------------------------------------------------------
// ABA routing number validation
// ---------------------------------------------------------------------------

/**
 * Compute the check digit for a 9-digit ABA routing number.
 *
 * The algorithm weights each position:
 *   pos 0 * 3 + pos 1 * 7 + pos 2 * 1 + pos 3 * 3 + pos 4 * 7 + pos 5 * 1 +
 *   pos 6 * 3 + pos 7 * 7 + pos 8 * 1   ≡ 0 (mod 10)
 *
 * Returns the expected check digit (0-9) for the first 8 digits.
 */
export function computeRoutingCheckDigit(digits: string): number {
  // Accept 8 or 9 digit strings — always use first 8
  const d8 = digits.length > 8 ? digits.slice(0, 8) : digits;
  if (d8.length !== 8) {
    throw new Error(`Expected 8 digits, got ${d8.length}`);
  }
  const weights = [3, 7, 1, 3, 7, 1, 3, 7];
  let sum = 0;
  for (let i = 0; i < d8.length; i++) {
    sum += Number(d8[i]) * weights[i];
  }
  return (10 - (sum % 10)) % 10;
}

/**
 * Validate a 9-digit ABA routing number.
 *
 * Checks:
 *   - Exactly 9 numeric characters
 *   - Passes the weighted-sum check-digit algorithm
 *   - First two digits are in valid Federal Reserve ranges
 *   - Rejects all-zeros
 *
 * @returns detailed result with flags and human-readable errors
 */
export function validateRoutingNumber(routingNumber: string): RoutingValidationResult {
  const errors: string[] = [];

  if (typeof routingNumber !== 'string') {
    return { valid: false, errors: ['Routing number must be a string'], checkDigit: -1 };
  }

  // Whitespace is OK — strip first
  const trimmed = routingNumber.trim();

  // Length & numeric check
  if (!ROUTING_NUMBER_REGEX.test(trimmed)) {
    if (trimmed.length !== 9) {
      errors.push(`Invalid length: expected 9 digits, got ${trimmed.length}`);
    }
    if (!/^\d+$/.test(trimmed)) {
      errors.push('Must contain only digits (0-9)');
    }
    return { valid: false, errors, checkDigit: -1 };
  }

  // All zeros is never valid
  if (trimmed === '000000000') {
    errors.push('Routing number cannot be all zeros');
    return { valid: false, errors, checkDigit: 0 };
  }

  // Check-digit validation
  const expectedCheckDigit = computeRoutingCheckDigit(trimmed.slice(0, 8));
  const lastDigit = Number(trimmed[8]);
  if (lastDigit !== expectedCheckDigit) {
    errors.push(`Invalid check digit: expected ${expectedCheckDigit}, got ${lastDigit}`);
    return {
      valid: false,
      errors,
      checkDigit: lastDigit,
      expectedCheckDigit,
    };
  }

  // Federal Reserve range check (first two digits)
  const frDist = getFederalReserveDistrict(Number(trimmed.slice(0, 2)));
  if (frDist === -1) {
    errors.push(`Invalid Federal Reserve range prefix: ${trimmed.slice(0, 2)}`);
    return {
      valid: false,
      errors,
      checkDigit: lastDigit,
    };
  }

  return {
    valid: true,
    errors: [],
    checkDigit: lastDigit,
    federalReserveDistrict: frDist,
  };
}

/**
 * Convenience: boolean-only routing validation.
 */
export function isRoutingNumberValid(routingNumber: string): boolean {
  return validateRoutingNumber(routingNumber).valid;
}

// ---------------------------------------------------------------------------
// Account number check-digit methods
// ---------------------------------------------------------------------------

/**
 * Compute the mod-9 check digit.
 *
 * Rule: checkDigit = sum(allOtherDigits) mod 9
 *
 * @param digits   full account string (including the check digit as last char)
 * @returns        expected check digit
 */
export function computeMod9CheckDigit(digits: string): number {
  const withoutLast = digits.slice(0, -1);
  let sum = 0;
  for (let i = 0; i < withoutLast.length; i++) {
    sum += Number(withoutLast[i]);
  }
  return sum % 9;
}

/**
 * Compute the mod-10 check digit.
 *
 * Rule: checkDigit makes (sum(allDigits)) divisible by 10
 * i.e.  checkDigit = (10 - sum(allOtherDigits) % 10) % 10
 *
 * @param digits   full account string (including the check digit as last char)
 * @returns        expected check digit
 */
export function computeMod10CheckDigit(digits: string): number {
  const withoutLast = digits.slice(0, -1);
  let sum = 0;
  for (let i = 0; i < withoutLast.length; i++) {
    sum += Number(withoutLast[i]);
  }
  return (10 - (sum % 10)) % 10;
}

/**
 * Determine which check-digit method(s), if any, a given account number passes.
 * Returns an array of matching methods; empty means none match.
 */
export function detectCheckMethod(accountNumber: string): AccountCheckMethod[] {
  const methods: AccountCheckMethod[] = [];
  if (accountNumber.length < 2) return methods;

  // mod-9
  const last = Number(accountNumber[accountNumber.length - 1]);
  if (last === computeMod9CheckDigit(accountNumber)) {
    methods.push('mod9');
  }
  // mod-10
  if (last === computeMod10CheckDigit(accountNumber)) {
    methods.push('mod10');
  }
  return methods;
}

/**
 * Validate an account number using the specified check-digit method.
 *
 * @param accountNumber       the numeric account string (digits only)
 * @param method              validation strategy
 * @param expectedCheckDigit  override for the expected check digit (optional)
 */
export function validateAccountNumber(
  accountNumber: string,
  method: AccountCheckMethod = 'none',
  expectedCheckDigit?: number,
): AccountValidationResult {
  const errors: string[] = [];

  if (typeof accountNumber !== 'string') {
    return { valid: false, errors: ['Account number must be a string'] };
  }

  const trimmed = accountNumber.trim();

  // Length
  if (trimmed.length < MIN_ACCOUNT_LENGTH) {
    errors.push(`Too short: minimum ${MIN_ACCOUNT_LENGTH} digits`);
  }
  if (trimmed.length > MAX_ACCOUNT_LENGTH) {
    errors.push(`Too long: maximum ${MAX_ACCOUNT_LENGTH} digits`);
  }

  // Numeric-only
  if (!ACCOUNT_NUMBER_REGEX.test(trimmed)) {
    errors.push('Must contain only digits (0-9)');
    return { valid: false, errors };
  }

  if (errors.length > 0) return { valid: false, errors };

  // Auto-detect check method if none specified and we have enough digits
  let detectedMethods: AccountCheckMethod[] | undefined;
  if (method === 'none' && trimmed.length >= 2) {
    detectedMethods = detectCheckMethod(trimmed);
  }

  // Check-digit methods
  if (method === 'none') {
    return { valid: true, errors: [], checkMethod: detectedMethods };
  }

  if (trimmed.length < 2) {
    errors.push('Need at least 2 digits for check-digit validation');
    return { valid: false, errors };
  }

  const lastDigit = Number(trimmed[trimmed.length - 1]);

  // Use explicit expected digit if supplied, otherwise compute
  const expected = expectedCheckDigit ?? (method === 'mod9'
    ? computeMod9CheckDigit(trimmed)
    : computeMod10CheckDigit(trimmed));

  if (lastDigit !== expected) {
    errors.push(
      `Invalid ${method} check digit: expected ${expected}, got ${lastDigit}`,
    );
  }

  return { valid: errors.length === 0, errors, checkMethod: detectedMethods };
}

/**
 * Convenience: boolean-only account validation.
 */
export function isAccountNumberValid(
  accountNumber: string,
  method: AccountCheckMethod = 'none',
  expectedCheckDigit?: number,
): boolean {
  return validateAccountNumber(accountNumber, method, expectedCheckDigit).valid;
}

// ---------------------------------------------------------------------------
// Combined routing + account validation
// ---------------------------------------------------------------------------

/**
 * Validate a routing number and account number together.
 * Returns a structured result covering both.
 */
export function validateAccountPair(
  routingNumber: string,
  sourceAccount: string,
  destinationAccount: string,
): PairValidationResult {
  const routing = validateRoutingNumber(routingNumber);
  const source = validateAccountNumber(sourceAccount);
  const destination = validateAccountNumber(destinationAccount);

  const errors: string[] = [];

  if (!routing.valid) {
    errors.push(...routing.errors);
  }
  if (!source.valid) {
    errors.push(`Source: ${source.errors.join('; ')}`);
  }
  if (!destination.valid) {
    errors.push(`Destination: ${destination.errors.join('; ')}`);
  }
  if (sourceAccount.trim() === destinationAccount.trim()) {
    errors.push('Source and destination account numbers must differ');
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Routing number parsing / info extraction
// ---------------------------------------------------------------------------

/**
 * DecodeFederal Reserve district from first two digits of routing number.
 */
function getFederalReserveDistrict(firstTwo: number): number {
  // Standard ABA ranges to FR districts
  if (firstTwo >= 0 && firstTwo <= 12) {
    // 00 is treated as 1 (Boston)
    return firstTwo === 0 ? 1 : firstTwo;
  }
  if (firstTwo >= 21 && firstTwo <= 29) return 2;   // New York
  if (firstTwo >= 30 && firstTwo <= 32) return 3;   // Philadelphia
  if (firstTwo >= 61 && firstTwo <= 69) return 12;  // San Francisco
  if (firstTwo >= 70 && firstTwo <= 72) return 10;  // Dallas
  if (firstTwo === 80) return 8;                     // US Treasury
  if (firstTwo >= 90 && firstTwo <= 92) return 12;   // Other
  return -1; // Unknown
}

/**
 * Decode a routing number's structural information.
 *
 * Position meaning (1-indexed for human documentation; 0-indexed in code):
 *   digits 1-4: ABA institution identifier
 *   digits 5-8: Federal Reserve routing symbol
 *   digit  9   : check digit
 *
 * The 8th digit (index 7) indicates the institution type.
 */
export function parseRoutingNumber(routingNumber: string): RoutingInfo | null {
  const result = validateRoutingNumber(routingNumber);
  if (!result.valid) return null;

  const trimmed = routingNumber.trim();

  // Federal Reserve District from first two digits
  const frDistrict = getFederalReserveDistrict(Number(trimmed.slice(0, 2)));

  // Institution type = 8th digit (0-indexed 7)
  const typeDigit = trimmed[7];
  const institutionType: Record<string, string> = {
    '0': 'Reserve Bank',
    '1': 'Thrift Institution',
    '6': 'Foreign Branch',
    '7': 'Regular Depository',
    '8': 'Credit Union / Non-Fed',
    '9': 'In-house Locator',
  };

  // Thrift indicator: '1' means thrift institution
  const thriftIndicator = typeDigit === '1' ? '1' : '0';

  return {
    thriftIndicator,
    federalReserveDistrict: frDistrict,
    institutionType: institutionType[typeDigit] ?? `Unknown (${typeDigit})`,
  };
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/**
 * Format a routing number with dashes for readability: XXXX-XXXXX
 */
export function formatRoutingNumber(digits: string): string {
  const clean = digits.replace(/\D/g, '');
  if (clean.length !== 9) return digits;
  return `${clean.slice(0, 4)}-${clean.slice(4, 9)}`;
}

/**
 * Strip all non-digit characters from a routing number.
 */
export function stripRoutingNumber(raw: string): string {
  return raw.replace(/\D/g, '');
}

/**
 * Format an account number with grouping dashes (groups of 4 from the right).
 * E.g., "1234567890" → "12-3456-7890"
 */
export function formatAccountNumber(digits: string): string {
  const clean = digits.replace(/\D/g, '');
  if (clean.length <= 8) return clean;

  const groups: string[] = [];
  // Split into groups of 4 from the RIGHT
  let remaining = clean;
  while (remaining.length > 4) {
    const prefix = remaining.slice(0, remaining.length - 4);
    const suffix = remaining.slice(remaining.length - 4);
    groups.unshift(suffix);
    remaining = prefix;
  }
  if (remaining.length > 0) {
    groups.unshift(remaining);
  }
  return groups.join('-');
}
