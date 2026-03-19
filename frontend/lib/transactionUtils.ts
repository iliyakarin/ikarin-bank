// We cannot import types in this environment for some reason when using node --experimental-strip-types
// It seems it strips types but might have issues with type-only imports or maybe I am misinterpreting the error.
// "SyntaxError: The requested module './types.ts' does not provide an export named 'TransactionStatus'"
// This usually happens when the file is treated as a module but the export is a type and it gets stripped out but the import remains?
// Or maybe because it's a type-only file?

// Let's just use string for the input type in this utility file to avoid the import issue during testing.
// In the actual component we can use the type.

export const getTransactionStatus = (status: string) => {
    switch (status) {
        case 'pending':
        case 'sent_to_kafka':
            return 'pending';
        case 'cleared':
            return 'cleared';
        case 'failed':
            return 'failed';
        default:
            return 'unknown';
    }
};

export const getStatusLabel = (status: string) => {
    switch (status) {
        case 'pending':
            return 'Pending';
        case 'cleared':
            return 'Cleared';
        case 'failed':
            return 'Failed';
        default:
            return 'Unknown Status';
    }
};

/**
 * Safely converts a dollar amount (string or number) to integer cents.
 * Avoids floating point precision issues by using string manipulation.
 */
export const toCents = (amount: string | number): number => {
    if (amount === undefined || amount === null || amount === '') return 0;

    // Ensure we have a string, remove commas (if any) and whitespace
    const s = amount.toString().replace(/,/g, '').trim();

    if (!s || s === '.') return 0;

    const parts = s.split('.');
    let dollars = parts[0] || '0';
    let cents = parts[1] || '00';

    // Handle negative sign
    const isNegative = dollars.startsWith('-');
    if (isNegative) dollars = dollars.substring(1);

    // Normalize cents to exactly 2 digits
    cents = cents.padEnd(2, '0').slice(0, 2);

    const totalCents = parseInt(dollars, 10) * 100 + parseInt(cents, 10);
    return isNegative ? -totalCents : totalCents;
};

/**
 * Safely converts integer cents to a dollar string.
 * Avoids floating point precision issues by using integer arithmetic.
 * Returns a string with exactly 2 decimal places.
 */
export const fromCents = (cents: number): string => {
    if (cents === undefined || cents === null) return '0.00';

    const isNegative = cents < 0;
    const absCents = Math.abs(cents);

    const dollars = Math.floor(absCents / 100);
    const remainingCents = absCents % 100;

    const result = `${dollars}.${remainingCents.toString().padStart(2, '0')}`;
    return isNegative ? `-${result}` : result;
};

/**
 * Formats integer cents into a human-readable currency string.
 * Uses fromCents internally to ensure precision.
 */
export const formatCurrency = (cents: number | null | undefined, showSymbol: boolean = true): string => {
    if (cents === null || cents === undefined) return showSymbol ? '$0.00' : '0.00';
    const formatted = fromCents(cents);
    if (!showSymbol) return formatted;

    // Add symbol and handle negative sign placement
    if (formatted.startsWith('-')) {
        return `-$${formatted.substring(1)}`;
    }
    return `$${formatted}`;
};
