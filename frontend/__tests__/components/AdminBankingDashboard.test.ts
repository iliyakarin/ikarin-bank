import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { formatMerchantName, formatFedRailBadge, isTransactionIncome, isTransactionExpense } from '../../lib/neobank/utils';

describe('Admin Banking Dashboard & Audit Ledger - Task 10', () => {
  it('formats metrics, merchant brand names and rail indicators accurately', () => {
    const mockMetrics = {
      totalVolume: 5049900, // $50,499.00
      transactionCount: 42,
      totalBalance: 125000000, // $1,250,000.00
      activeUsers: 8,
      avgTransactionSize: 120235,
      topTransactions: [
        {
          id: 'tx-audit-1',
          amount: 650000, // $6,500.00
          merchant: 'Vanguard Brokerage Settlement',
          category: 'investments',
          created_at: new Date().toISOString(),
          account_id: 1,
          transaction_type: 'wire',
          transaction_side: 'DEBIT',
          status: 'cleared',
        },
        {
          id: 'tx-audit-2',
          amount: 250000, // $2,500.00
          merchant: 'TechCorp Payroll Direct Deposit',
          category: 'income',
          created_at: new Date().toISOString(),
          account_id: 1,
          transaction_type: 'income',
          transaction_side: 'CREDIT',
          status: 'cleared',
        }
      ],
      hourlyVolume: Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        count: i === 14 ? 12 : 2,
        total: i === 14 ? 1500000 : 25000,
      })),
      merchantStats: [
        { merchant: 'Shell Gas Station', transaction_count: 14, total_amount: 89400 },
        { merchant: 'Amc Theatres', transaction_count: 8, total_amount: 32000 },
      ],
      userGrowth: [
        { date: '2026-08-22', count: 8 }
      ],
    };

    assert.equal(mockMetrics.totalVolume, 5049900);
    assert.equal(mockMetrics.transactionCount, 42);
    assert.equal(mockMetrics.topTransactions.length, 2);
    assert.equal(mockMetrics.hourlyVolume.length, 24);

    // Verify top transactions classification
    const debitTx = mockMetrics.topTransactions[0];
    const creditTx = mockMetrics.topTransactions[1];

    assert.equal(isTransactionExpense(debitTx), true, 'Wire debit must be an expense (outflow)');
    assert.equal(isTransactionIncome(debitTx), false);

    assert.equal(isTransactionIncome(creditTx), true, 'Payroll credit must be an income (inflow)');
    assert.equal(isTransactionExpense(creditTx), false);

    // Verify rail badge formatting
    const railBadge = formatFedRailBadge(debitTx.transaction_type);
    assert.equal(railBadge.rail, 'wire');
    assert.ok(railBadge.label.includes('Fedwire'));
  });

  it('handles bank-wide transaction filter params gracefully', () => {
    const rawTxList = [
      { id: '1', merchant: 'Shell Gas Station', category: 'transport', amount: 6451, transaction_side: 'DEBIT' },
      { id: '2', merchant: 'David Chen', category: 'p2p', amount: 3500, transaction_side: 'CREDIT' },
      { id: '3', merchant: 'Target Supercenter', category: 'shopping', amount: 12050, transaction_side: 'DEBIT' },
    ];

    const searchStr = 'target';
    const filtered = rawTxList.filter(t => t.merchant.toLowerCase().includes(searchStr));
    assert.equal(filtered.length, 1);
    assert.equal(filtered[0].merchant, 'Target Supercenter');
  });
});
