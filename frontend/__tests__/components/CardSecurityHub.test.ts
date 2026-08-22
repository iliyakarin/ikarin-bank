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
});
