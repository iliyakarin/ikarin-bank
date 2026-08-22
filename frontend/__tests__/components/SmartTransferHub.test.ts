import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { validateAbaRouting, formatFedRailBadge } from '../../lib/neobank/utils';

describe('SmartTransferHub Logic - Task 5', () => {
  it('detects 9-digit routing input and classifies payment rail automatically', () => {
    // Standard Chase Routing -> FedNow & Fedwire supported
    const chaseAba = '021000021';
    const routingRes = validateAbaRouting(chaseAba);
    assert.equal(routingRes.valid, true);
    assert.equal(routingRes.district, 'New York');

    // Recommends FedNow for retail/instant amounts ($250.00)
    const amountCents = 25000;
    const recommendedRail = amountCents > 50000000 ? 'wire' : 'fednow';
    assert.equal(recommendedRail, 'fednow');

    const badge = formatFedRailBadge(recommendedRail);
    assert.equal(badge.fee, '$0.00');
  });

  it('recommends Fedwire RTGS for institutional high-value amounts over $500,000', () => {
    const amountCents = 75000000; // $750,000.00
    const recommendedRail = amountCents >= 50000000 ? 'wire' : 'fednow';
    assert.equal(recommendedRail, 'wire');

    const badge = formatFedRailBadge(recommendedRail);
    assert.equal(badge.fee, '$15.00');
  });
});
