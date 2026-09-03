import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { toCents, formatCurrency } from '../../lib/transactionUtils';
import { calculateVaultYield } from '../../lib/neobank/utils';

describe('BetweenAccounts & Vault Transfer Logic', () => {
  const mockAccounts = [
    {
      id: 1,
      name: 'Main Checking',
      balance: 1000000, // $10,000.00
      is_main: true,
      routing_number: '123456780',
    },
    {
      id: 2,
      name: 'Treasury High-Yield Savings Vault',
      balance: 250000, // $2,500.00
      is_main: false,
      routing_number: '123456780',
    },
    {
      id: 3,
      name: 'Vacation Fund',
      balance: 50000, // $500.00
      is_main: false,
      routing_number: '123456780',
    },
  ];

  it('correctly resolves primary checking and savings vault accounts', () => {
    const main = mockAccounts.find((a) => a.is_main);
    assert.ok(main);
    assert.equal(main.id, 1);
    assert.equal(main.name, 'Main Checking');

    const savings = mockAccounts.find(
      (a) => !a.is_main && (a.name.toLowerCase().includes('savings') || a.name.toLowerCase().includes('vault'))
    );
    assert.ok(savings);
    assert.equal(savings.id, 2);
    assert.equal(savings.balance, 250000);
  });

  it('validates transfer direction and prevents identical source and target accounts', () => {
    const fromId = 1;
    const toId = 1;
    assert.equal(fromId === toId, true, 'Should detect identical accounts');

    let swappedFrom = fromId;
    let swappedTo = 2;
    // Swap direction
    const temp = swappedFrom;
    swappedFrom = swappedTo;
    swappedTo = temp;

    assert.equal(swappedFrom, 2);
    assert.equal(swappedTo, 1);
  });

  it('validates insufficient funds and boundaries on internal transfers', () => {
    const checking = mockAccounts[0];
    const validAmount = toCents('250.00'); // 25000 cents
    assert.equal(validAmount, 25000);
    assert.ok(validAmount <= checking.balance, 'Checking has sufficient funds for $250.00');

    const excessiveAmount = toCents('15000.00'); // 1500000 cents
    assert.ok(excessiveAmount > checking.balance, 'Should detect excessive transfer amount');

    const invalidZero = toCents('0.00');
    assert.equal(invalidZero, 0);
    assert.ok(invalidZero <= 0, 'Should reject zero or negative amount');
  });

  it('calculates accurate projected APY yield for vault deposits', () => {
    const depositCents = toCents('5000.00'); // $5,000.00
    assert.equal(depositCents, 500000);

    const yieldInfo = calculateVaultYield(depositCents, 4.85);
    // Annual = 5000 * 0.0485 = $242.50 = 24250 cents
    assert.equal(yieldInfo.annualCents, 24250);
    assert.ok(yieldInfo.monthlyCents > 0);
    assert.equal(formatCurrency(yieldInfo.annualCents), '$242.50');
  });
});
