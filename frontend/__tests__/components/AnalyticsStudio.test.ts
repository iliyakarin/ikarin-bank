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

  it('ranks top merchants by volume descending', () => {
    const transactions = [
      { merchant: 'Uber', amount: 4500 },
      { merchant: 'Starbucks', amount: 1200 },
      { merchant: 'Uber', amount: 3500 },
      { merchant: 'Netflix', amount: 2200 },
    ];

    const merchantMap: Record<string, number> = {};
    for (const tx of transactions) {
      merchantMap[tx.merchant] = (merchantMap[tx.merchant] || 0) + tx.amount;
    }

    const leaderboard = Object.entries(merchantMap)
      .map(([name, amount]) => ({ name, amount }))
      .sort((a, b) => b.amount - a.amount);

    assert.equal(leaderboard[0].name, 'Uber');
    assert.equal(leaderboard[0].amount, 8000);
    assert.equal(leaderboard[1].name, 'Netflix');
  });
});
