import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { FastPayPayee } from '../../lib/neobank/types';
import { DEFAULT_FAVORITE_PAYEES } from '../../components/neobank/FastPayCarousel';

describe('QuickActionHub & FastPayCarousel - Task 4', () => {
  it('contains pre-configured favorite payees with US Fed rails and initials', () => {
    assert.ok(DEFAULT_FAVORITE_PAYEES.length >= 4);

    const david = DEFAULT_FAVORITE_PAYEES.find((p: FastPayPayee) => p.name.includes('David Chen'));
    assert.ok(david);
    assert.equal(david.preferredRail, 'fednow');
    assert.equal(david.initials, 'DC');

    const vanguard = DEFAULT_FAVORITE_PAYEES.find((p: FastPayPayee) => p.name.includes('Vanguard'));
    assert.ok(vanguard);
    assert.equal(vanguard.preferredRail, 'wire');
    assert.equal(vanguard.initials, 'VG');

    const pge = DEFAULT_FAVORITE_PAYEES.find((p: FastPayPayee) => p.name.includes('PG&E'));
    assert.ok(pge);
    assert.equal(pge.preferredRail, 'ach');
    assert.equal(pge.initials, 'PE');
  });

  it('all payees have valid avatar colors and non-empty initials', () => {
    for (const payee of DEFAULT_FAVORITE_PAYEES) {
      assert.ok(payee.id);
      assert.ok(payee.name);
      assert.ok(payee.initials);
      assert.ok(payee.avatarColor);
      assert.ok(['fednow', 'wire', 'ach', 'internal'].includes(payee.preferredRail));
    }
  });
});
