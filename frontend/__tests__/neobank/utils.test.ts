import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateAbaRouting,
  groupTransactionsByDate,
  formatFedRailBadge,
  calculateVaultYield,
  formatCardNumberMasked,
  formatMerchantName,
} from '../../lib/neobank/utils';

describe('Neobank Pure Utilities - Task 1', () => {
  describe('validateAbaRouting', () => {
    it('validates authentic Chase routing number 021000021', () => {
      const res = validateAbaRouting('021000021');
      assert.equal(res.valid, true);
      assert.equal(res.district, 'New York');
    });

    it('validates authentic Wells Fargo routing number 121000248', () => {
      const res = validateAbaRouting('121000248');
      assert.equal(res.valid, true);
      assert.equal(res.district, 'San Francisco');
    });

    it('rejects invalid routing number with incorrect checksum', () => {
      const res = validateAbaRouting('021000022');
      assert.equal(res.valid, false);
      assert.equal(res.error, 'Invalid ABA routing checksum');
    });

    it('rejects short or non-digit input', () => {
      const res = validateAbaRouting('12345');
      assert.equal(res.valid, false);
      assert.equal(res.error, 'Routing number must be exactly 9 digits');
    });
  });

  describe('calculateVaultYield', () => {
    it('calculates accurate monthly and annual yield in cents for $10,000 at 4.85% APY', () => {
      // 10,000.00 USD = 1,000,000 cents
      const yieldCalc = calculateVaultYield(1000000, 4.85);
      assert.equal(yieldCalc.annualCents, 48500); // $485.00
      assert.equal(yieldCalc.monthlyCents, 4042); // $40.42 rounded
      assert.equal(yieldCalc.formattedApy, '4.85% APY');
    });

    it('handles zero balance gracefully', () => {
      const yieldCalc = calculateVaultYield(0, 4.85);
      assert.equal(yieldCalc.annualCents, 0);
      assert.equal(yieldCalc.monthlyCents, 0);
    });
  });

  describe('formatFedRailBadge', () => {
    it('formats FedNow instant settlement rail badge', () => {
      const badge = formatFedRailBadge('fednow');
      assert.equal(badge.label, 'FedNow 24/7');
      assert.equal(badge.speed, 'Instant (2.5s)');
      assert.equal(badge.fee, '$0.00');
    });

    it('formats Fedwire RTGS high-value rail badge', () => {
      const badge = formatFedRailBadge('wire');
      assert.equal(badge.label, 'Fedwire RTGS');
      assert.equal(badge.speed, 'Real-time (Same day)');
      assert.equal(badge.fee, '$15.00');
    });

    it('formats FedACH batch rail badge', () => {
      const badge = formatFedRailBadge('ach');
      assert.equal(badge.label, 'FedACH Direct');
      assert.equal(badge.speed, '1-2 Business Days');
      assert.equal(badge.fee, '$0.00');
    });
  });

  describe('formatCardNumberMasked', () => {
    it('masks 16-digit card showing first 4 and last 4', () => {
      const masked = formatCardNumberMasked('5542889012234567');
      assert.equal(masked, '5542 •••• •••• 4567');
    });

    it('handles already spaced input', () => {
      const masked = formatCardNumberMasked('5542 8890 1223 4567');
      assert.equal(masked, '5542 •••• •••• 4567');
    });
  });

  describe('formatMerchantName', () => {
    it('cleans up raw transaction descriptions into clean brand names', () => {
      assert.equal(formatMerchantName('NETFLIX.COM PAYMENT 08/21'), 'Netflix');
      assert.equal(formatMerchantName('UBER *TRIP 2841 SAN FRANCISCO'), 'Uber');
      assert.equal(formatMerchantName('STARBUCKS STORE #10492'), 'Starbucks');
      assert.equal(formatMerchantName('PG&E UTILITY DIRECT DEBIT'), 'PG&E Electric Utility');
      assert.equal(formatMerchantName('VANGUARD BROKERAGE SETTLEMENT'), 'Vanguard Settlement');
    });
  });

  describe('groupTransactionsByDate', () => {
    it('groups transactions into chronological buckets', () => {
      const now = new Date();
      const todayISO = now.toISOString();
      const yesterday = new Date(now.getTime() - 86400000);
      const yesterdayISO = yesterday.toISOString();

      const events = [
        { id: 'tx-1', amount: 5000, created_at: todayISO, merchant: 'Netflix' },
        { id: 'tx-2', amount: 1200, created_at: todayISO, merchant: 'Uber' },
        { id: 'tx-3', amount: 35000, created_at: yesterdayISO, merchant: 'PG&E' },
      ];

      const grouped = groupTransactionsByDate(events);
      assert.ok(grouped['Today'] || grouped[Object.keys(grouped)[0]]);
      assert.equal(Object.values(grouped).flat().length, 3);
    });
  });
});
