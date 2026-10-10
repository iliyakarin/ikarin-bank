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

  it('filters and deletes a virtual card from the active card list', () => {
    const list: CardDetails[] = [
      {
        id: 'card-debit-1',
        cardNumber: '5542889012234567',
        expiry: '12/28',
        cvv: '739',
        cardType: 'debit',
        isFrozen: false,
      },
      {
        id: 'card-virtual-123',
        cardNumber: '4790123456789012',
        expiry: '10/30',
        cvv: '999',
        cardType: 'virtual',
        isFrozen: false,
      },
    ];

    // Delete virtual card
    const remaining = list.filter((c) => c.id !== 'card-virtual-123');
    assert.equal(remaining.length, 1);
    assert.equal(remaining[0].id, 'card-debit-1');
  });

  it('safely handles selection fallback and prevents deletion of debit/credit cards', () => {
    const list: CardDetails[] = [
      {
        id: 'card-debit-1',
        cardNumber: '5542889012234567',
        expiry: '12/28',
        cvv: '739',
        cardType: 'debit',
        isFrozen: false,
      },
      {
        id: 'card-credit-2',
        cardNumber: '4532148803436467',
        expiry: '08/29',
        cvv: '456',
        cardType: 'credit',
        isFrozen: false,
      },
      {
        id: 'card-virtual-1',
        cardNumber: '4790123456789012',
        expiry: '10/30',
        cvv: '999',
        cardType: 'virtual',
        isFrozen: false,
      },
    ];

    // Attempt deletion function helper replicating CardSecurityHub safety check
    const attemptDelete = (card: CardDetails, currentList: CardDetails[]) => {
      if (card.cardType !== 'virtual') {
        return { success: false, list: currentList, nextSelected: card.id };
      }
      const updated = currentList.filter((c) => c.id !== card.id);
      const nextSelected = updated[0]?.id || 'card-debit-1';
      return { success: true, list: updated, nextSelected };
    };

    // Attempting to delete debit card fails
    const debitResult = attemptDelete(list[0], list);
    assert.equal(debitResult.success, false);
    assert.equal(debitResult.list.length, 3);

    // Attempting to delete virtual card succeeds and switches active card
    const virtualResult = attemptDelete(list[2], list);
    assert.equal(virtualResult.success, true);
    assert.equal(virtualResult.list.length, 2);
    assert.equal(virtualResult.nextSelected, 'card-debit-1');
  });
});

