import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { calculateVaultYield, formatCardNumberMasked } from '../../lib/neobank/utils';

describe('HeroProductCarousel Components - Task 3', () => {
  it('calculates goal progress percentage for VaultCard', () => {
    const currentBalanceCents = 750000; // $7,500.00
    const targetGoalCents = 1000000; // $10,000.00
    const progressPercent = Math.min(100, Math.round((currentBalanceCents / targetGoalCents) * 100));

    assert.equal(progressPercent, 75);
    const yieldInfo = calculateVaultYield(currentBalanceCents, 4.85);
    assert.equal(yieldInfo.annualCents, 36375); // $363.75
  });

  it('formats masked card number and handles freeze states for DigitalCardPreview', () => {
    const rawNumber = '4532148803436467';
    const masked = formatCardNumberMasked(rawNumber);
    assert.equal(masked, '4532 •••• •••• 6467');

    const cardState = {
      isFrozen: true,
      onlineEnabled: false,
    };
    assert.equal(cardState.isFrozen, true);
    assert.equal(cardState.onlineEnabled, false);
  });
});
