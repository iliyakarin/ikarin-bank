import { CardDetails } from './types';

/**
 * Generates a realistic 16-digit card number with a valid Luhn checksum.
 * Uses BIN 4790 (Visa Virtual).
 */
export function generateVirtualCardNumber(): string {
  const prefix = '4790';
  let digits = prefix;
  for (let i = 0; i < 11; i++) {
    digits += Math.floor(Math.random() * 10).toString();
  }
  // Calculate Luhn check digit
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let d = parseInt(digits[digits.length - 1 - i], 10);
    if (i % 2 === 0) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
  }
  const checkDigit = (10 - (sum % 10)) % 10;
  return digits + checkDigit.toString();
}

/**
 * Creates a new virtual card instance.
 */
export function generateVirtualCard(cardHolder: string = 'VALUED CLIENT'): CardDetails {
  const id = `card-virtual-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const now = new Date();
  const expMonth = String(now.getMonth() + 1).padStart(2, '0');
  const expYear = String((now.getFullYear() + 4) % 100).padStart(2, '0');
  const cvv = String(Math.floor(100 + Math.random() * 900));

  return {
    id,
    cardNumber: generateVirtualCardNumber(),
    cardHolder: cardHolder.toUpperCase().trim() || 'VALUED CLIENT',
    expiry: `${expMonth}/${expYear}`,
    cvv,
    cardType: 'virtual',
    type: 'virtual',
    isFrozen: false,
    dailySpendingLimitCents: 100000, // $1,000.00
    monthlySpendingLimitCents: 500000, // $5,000.00
    onlinePaymentsEnabled: true,
    contactlessEnabled: true,
    atmWithdrawalsEnabled: false,
  };
}
