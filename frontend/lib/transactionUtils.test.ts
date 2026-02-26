import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getTransactionStatus, getStatusLabel } from './transactionUtils';

describe('Transaction Status Logic', () => {
    it('should identify pending transactions', () => {
        assert.strictEqual(getTransactionStatus('pending'), 'pending');
        assert.strictEqual(getTransactionStatus('sent_to_kafka'), 'pending');
    });

    it('should identify cleared transactions', () => {
        assert.strictEqual(getTransactionStatus('cleared'), 'cleared');
    });

    it('should identify unknown status', () => {
        assert.strictEqual(getTransactionStatus('random_status'), 'unknown');
    });

    it('should return correct labels', () => {
        assert.strictEqual(getStatusLabel('pending'), 'Pending');
        assert.strictEqual(getStatusLabel('cleared'), 'Cleared');
        assert.strictEqual(getStatusLabel('unknown'), 'Unknown Status');
    });
});
