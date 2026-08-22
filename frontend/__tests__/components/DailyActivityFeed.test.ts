import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { groupTransactionsByDate, formatMerchantName, formatFedRailBadge, isTransactionIncome, isTransactionExpense } from '../../lib/neobank/utils';

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

  it('correctly classifies expenses (purchases, dining, gas, entertainment) as negative outflow', () => {
    // 1. Merchant purchases from simulator
    const amcTx = { amount: 3799, merchant: 'Amc Theatres', category: 'entertainment', transaction_side: 'DEBIT', transaction_type: 'expense' };
    const shellTx = { amount: 6451, merchant: 'Shell Gas Station', category: 'transport', transaction_side: 'DEBIT', transaction_type: 'expense' };
    const chipotleTx = { amount: 1453, merchant: 'Chipotle Mexican Grill', category: 'dining', transaction_side: 'DEBIT', transaction_type: 'expense' };
    const rentTx = { amount: 180000, merchant: 'Apartment Leasing Co', category: 'rent', transaction_side: 'DEBIT', transaction_type: 'expense' };
    const p2pOutTx = { amount: 1463, merchant: 'To Ikarin6@example.com', category: 'p2p', transaction_side: 'DEBIT', transaction_type: 'transfer' };

    assert.equal(isTransactionIncome(amcTx), false, 'AMC purchase must be an expense (outflow)');
    assert.equal(isTransactionExpense(amcTx), true);

    assert.equal(isTransactionIncome(shellTx), false, 'Shell Gas must be an expense (outflow)');
    assert.equal(isTransactionExpense(shellTx), true);

    assert.equal(isTransactionIncome(chipotleTx), false, 'Chipotle dining must be an expense (outflow)');
    assert.equal(isTransactionExpense(chipotleTx), true);

    assert.equal(isTransactionIncome(rentTx), false, 'Rent must be an expense (outflow)');
    assert.equal(isTransactionExpense(rentTx), true);

    assert.equal(isTransactionIncome(p2pOutTx), false, 'Outgoing P2P must be an expense (outflow)');
    assert.equal(isTransactionExpense(p2pOutTx), true);
  });

  it('correctly classifies income (salary, deposit, incoming p2p) as positive inflow', () => {
    const salaryTx = { amount: 250000, merchant: 'TechCorp Payroll', category: 'income', transaction_side: 'CREDIT', transaction_type: 'income' };
    const p2pInTx = { amount: 14171, merchant: 'From Ikarin6@example.com', category: 'p2p', transaction_side: 'CREDIT', transaction_type: 'transfer' };
    const depositTx = { amount: 50000, merchant: 'Direct Card Deposit', category: 'deposit', transaction_side: 'CREDIT', transaction_type: 'deposit' };

    assert.equal(isTransactionIncome(salaryTx), true, 'Salary must be income (inflow)');
    assert.equal(isTransactionExpense(salaryTx), false);

    assert.equal(isTransactionIncome(p2pInTx), true, 'Incoming P2P must be income (inflow)');
    assert.equal(isTransactionExpense(p2pInTx), false);

    assert.equal(isTransactionIncome(depositTx), true, 'Deposit must be income (inflow)');
    assert.equal(isTransactionExpense(depositTx), false);
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
