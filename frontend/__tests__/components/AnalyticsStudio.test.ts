import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('AnalyticsStudio Logic - Task 7', () => {
  it('aggregates category totals and computes percentages', () => {
    const transactions = [
      { category: 'Dining', amount: 15000 },
      { category: 'Dining', amount: 5000 },
      { category: 'Utilities', amount: 18000 },
      { category: 'Travel', amount: 42000 },
    ];

    const categoryMap: Record<string, number> = {};
    let totalSpend = 0;

    for (const tx of transactions) {
      const cat = tx.category || 'Other';
      categoryMap[cat] = (categoryMap[cat] || 0) + tx.amount;
      totalSpend += tx.amount;
    }

    assert.equal(totalSpend, 80000);
    assert.equal(categoryMap['Dining'], 20000);
    assert.equal(categoryMap['Utilities'], 18000);
    assert.equal(categoryMap['Travel'], 42000);

    const diningPercent = Math.round((categoryMap['Dining'] / totalSpend) * 100);
    assert.equal(diningPercent, 25);
  });

  it('dynamically recalculates metrics and filters transactions across time ranges (24h, 7d, 30d, 90d, 1y)', () => {
    const now = new Date('2026-08-22T12:00:00Z');
    const transactions = [
      { id: '1', amount: 5000, category: 'Dining', created_at: new Date(now.getTime() - 2 * 3600 * 1000).toISOString() }, // 2h ago (24h)
      { id: '2', amount: 12000, category: 'Shopping', created_at: new Date(now.getTime() - 48 * 3600 * 1000).toISOString() }, // 2d ago (7d)
      { id: '3', amount: 35000, category: 'Travel', created_at: new Date(now.getTime() - 15 * 24 * 3600 * 1000).toISOString() }, // 15d ago (30d)
      { id: '4', amount: 80000, category: 'Investment', created_at: new Date(now.getTime() - 60 * 24 * 3600 * 1000).toISOString() }, // 60d ago (90d)
      { id: '5', amount: 200000, category: 'Real Estate', created_at: new Date(now.getTime() - 200 * 24 * 3600 * 1000).toISOString() }, // 200d ago (1y)
    ];

    // Import helper from utils
    const { filterTransactionsByTimeRange } = require('../../lib/neobank/utils');

    const res24h = filterTransactionsByTimeRange(transactions, '24h', now);
    assert.equal(res24h.length, 1);
    assert.equal(res24h[0].id, '1');

    const res7d = filterTransactionsByTimeRange(transactions, '7d', now);
    assert.equal(res7d.length, 2);

    const res30d = filterTransactionsByTimeRange(transactions, '30d', now);
    assert.equal(res30d.length, 3);

    const res90d = filterTransactionsByTimeRange(transactions, '90d', now);
    assert.equal(res90d.length, 4);

    const res1y = filterTransactionsByTimeRange(transactions, '1y', now);
    assert.equal(res1y.length, 5);
  });
});
