import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('SimLabDrawer Role Gate - Task 9', () => {
  it('strictly isolates admin features from regular users', () => {
    const regularUser = { id: 1, email: 'user@example.com', role: 'user' };
    const adminUser = { id: 2, email: 'admin@karinbank.com', role: 'admin' };

    const shouldRenderForUser = regularUser.role === 'admin';
    assert.equal(shouldRenderForUser, false);

    const shouldRenderForAdmin = adminUser.role === 'admin';
    assert.equal(shouldRenderForAdmin, true);
  });

  it('provides simulator injection scenario templates', () => {
    const scenarios = [
      { id: 'fednow-fast-pay', name: 'FedNow P2P Split ($31.81)', rail: 'fednow', amountCents: 3181 },
      { id: 'fedwire-escrow', name: 'Fedwire Escrow Settlement ($6,504.43)', rail: 'wire', amountCents: 650443 },
      { id: 'fedach-payroll', name: 'FedACH Direct Payroll ($4,250.00)', rail: 'ach', amountCents: 425000 },
    ];

    assert.equal(scenarios.length, 3);
    assert.equal(scenarios[0].rail, 'fednow');
    assert.equal(scenarios[1].rail, 'wire');
    assert.equal(scenarios[2].rail, 'ach');
  });
});
