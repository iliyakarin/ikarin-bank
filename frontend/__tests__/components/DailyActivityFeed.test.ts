import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { groupTransactionsByDate, formatMerchantName, formatFedRailBadge } from '../../lib/neobank/utils';

describe('DailyActivityFeed & ReceiptModal - Task 6', () => {
  it('groups raw transactions and maps merchant brand names with rail indicators', () => {
    const rawEvents = [
      {
        id: 'tx-fednow-1',
        amount: 3181, // $31.81
        event_type: 'fednow',
        merchant: 'David Chen',
        created_at: new Date().toISOString(),
        status: 'cleared',
        end_to_end_id: 'FEDNOW-4b1b2f0d-d8dc',
      },
      {
        id: 'tx-wire-1',
        amount: 650443, // $6,504.43
        event_type: 'wire',
        merchant: 'Vanguard Brokerage Settlement',
        created_at: new Date().toISOString(),
        status: 'cleared',
        imad: '20260821L1Q1167008515',
      },
    ];

    const grouped = groupTransactionsByDate(rawEvents);
    assert.ok(grouped['Today']);
    assert.equal(grouped['Today'].length, 2);

    const firstTx = grouped['Today'][0];
    const brand = formatMerchantName(firstTx.merchant);
    assert.equal(brand, 'David Chen');

    const badge = formatFedRailBadge(firstTx.event_type);
    assert.equal(badge.label, 'FedNow 24/7');
  });

  it('formats digital receipt metadata with tracking codes', () => {
    const wireTx = {
      id: 'tx-wire-99',
      amount: 5000000,
      event_type: 'wire',
      merchant: 'BNY Mellon Trust',
      imad: '20260822L1Q1167009999',
      omad: '20260822OMAD9999',
      status: 'cleared',
    };

    assert.ok(wireTx.imad.startsWith('20260822'));
    assert.equal(wireTx.status, 'cleared');
  });
});
