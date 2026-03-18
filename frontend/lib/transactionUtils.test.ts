import { describe, it } from 'node:test';
import { strict as assert } from 'node:assert';
import { getTransactionStatus, getStatusLabel, toCents, fromCents, formatCurrency } from './transactionUtils';

describe('Transaction Status Logic', () => {
    it('should identify pending transactions', () => {
        assert.equal(getTransactionStatus('pending'), 'pending');
        assert.equal(getTransactionStatus('sent_to_kafka'), 'pending');
    });

    it('should identify cleared transactions', () => {
        assert.equal(getTransactionStatus('cleared'), 'cleared');
    });

    it('should identify unknown status', () => {
        assert.equal(getTransactionStatus('random_status'), 'unknown');
    });

    it('should return correct labels', () => {
        assert.equal(getStatusLabel('pending'), 'Pending');
        assert.equal(getStatusLabel('cleared'), 'Cleared');
        assert.equal(getStatusLabel('unknown'), 'Unknown Status');
    });
});

describe('toCents Precision Utility', () => {
    it('should convert simple dollar strings to cents', () => {
        assert.equal(toCents("10.50"), 1050);
        assert.equal(toCents("10"), 1000);
        assert.equal(toCents("0.01"), 1);
    });

    it('should handle commas in amount strings', () => {
        assert.equal(toCents("1,000.50"), 100050);
    });

    it('should handle numeric inputs safely (though strings are preferred)', () => {
        assert.equal(toCents(10.5), 1050);
        assert.equal(toCents(10.05), 1005);
    });

    it('should handle edge cases like empty strings or whitespace', () => {
        assert.equal(toCents(""), 0);
        assert.equal(toCents("  "), 0);
        assert.equal(toCents("."), 0);
    });

    it('should handle negative amounts', () => {
        assert.equal(toCents("-10.50"), -1050);
        assert.equal(toCents("-0.01"), -1);
    });

    it('should ignore extra decimal places (standard banking practice is to truncate or validate)', () => {
        // Our toCents slices to 2 digits
        assert.equal(toCents("10.559"), 1055);
    });
});

describe('fromCents & formatCurrency Utilities', () => {
    it('should convert cents to dollar strings', () => {
        assert.equal(fromCents(1050), "10.50");
        assert.equal(fromCents(1000), "10.00");
        assert.equal(fromCents(1), "0.01");
        assert.equal(fromCents(0), "0.00");
    });

    it('should handle negative cents in fromCents', () => {
        assert.equal(fromCents(-1050), "-10.50");
        assert.equal(fromCents(-1), "-0.01");
    });

    it('should format currency with symbols', () => {
        assert.equal(formatCurrency(1050), "$10.50");
        assert.equal(formatCurrency(-1050), "-$10.50");
    });

    it('should support disabling the currency symbol', () => {
        assert.equal(formatCurrency(1050, false), "10.50");
        assert.equal(formatCurrency(-1050, false), "-10.50");
    });

    it('should handle null/undefined gracefully', () => {
        assert.equal(formatCurrency(null), "$0.00");
        assert.equal(formatCurrency(undefined), "$0.00");
    });
});
