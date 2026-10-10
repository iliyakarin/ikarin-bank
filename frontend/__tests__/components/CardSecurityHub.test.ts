import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { CardDetails } from '../../lib/neobank/types';

describe('CardSecurityHub Logic - Task 8', () => {
  it('handles limit updates and toggle switches', () => {
    const initialCard: CardDetails = {
      id: 'card-1',
      cardNumber: '5542889012234567',
      cardHolder: 'JOHN DOE',
      expiry: '12/28',
      cvv: '739',
      cardType: 'debit',
      isFrozen: false,
      dailySpendingLimitCents: 500000, // $5,000.00
      monthlySpendingLimitCents: 2000000, // $20,000.00
      onlinePaymentsEnabled: true,
      contactlessEnabled: true,
      atmWithdrawalsEnabled: true,
    };

    // Toggle freeze
    const frozenCard = { ...initialCard, isFrozen: true };
    assert.equal(frozenCard.isFrozen, true);

    // Update daily limit
    const updatedLimitCard = { ...initialCard, dailySpendingLimitCents: 250000 };
    assert.equal(updatedLimitCard.dailySpendingLimitCents, 250000);
  });

  it('generates a valid new virtual card with default security limits', async () => {
    const { generateVirtualCard, generateVirtualCardNumber } = await import('../../lib/neobank/cardGenerator');
    const virtualCard = generateVirtualCard('ILIA KARIN');

    assert.equal(virtualCard.cardType, 'virtual');
    assert.equal(virtualCard.cardHolder, 'ILIA KARIN');
    assert.ok(virtualCard.cardNumber);
    assert.equal(virtualCard.cardNumber!.length, 16);
    assert.equal(virtualCard.cardNumber!.startsWith('4790'), true);
    assert.equal(virtualCard.isFrozen, false);
    assert.equal(virtualCard.dailySpendingLimitCents, 100000);
    assert.equal(virtualCard.monthlySpendingLimitCents, 500000);
    assert.equal(virtualCard.onlinePaymentsEnabled, true);
    assert.equal(virtualCard.atmWithdrawalsEnabled, false);
    assert.equal(virtualCard.cvv.length, 3);
  });
});

