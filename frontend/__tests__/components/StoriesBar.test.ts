import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_STORIES } from '../../components/neobank/StoriesBar';

describe('StoriesBar Component - Task 2', () => {
  it('contains at least 5 default financial stories with rich content', () => {
    assert.ok(DEFAULT_STORIES.length >= 5);

    const vaultStory = DEFAULT_STORIES.find((s) => s.id === 'story-vaults');
    assert.ok(vaultStory);
    assert.equal(vaultStory.actionType, 'savings');
    assert.ok(vaultStory.content.headline.includes('4.85% APY'));

    const fedNowStory = DEFAULT_STORIES.find((s) => s.id === 'story-fednow');
    assert.ok(fedNowStory);
    assert.equal(fedNowStory.actionType, 'transfer');
    assert.ok(fedNowStory.content.bullets.length > 0);

    const cashbackStory = DEFAULT_STORIES.find((s) => s.id === 'story-cashback');
    assert.ok(cashbackStory);
    assert.equal(cashbackStory.actionType, 'cashback');

    const fdicStory = DEFAULT_STORIES.find((s) => s.id === 'story-fdic');
    assert.ok(fdicStory);
    assert.equal(fdicStory.actionType, 'security');
  });

  it('all stories have valid action callback types and gradients', () => {
    for (const story of DEFAULT_STORIES) {
      assert.ok(story.id);
      assert.ok(story.title);
      assert.ok(story.gradient);
      assert.ok(story.actionText);
      assert.ok(['savings', 'transfer', 'cashback', 'security', 'analytics'].includes(story.actionType));
    }
  });
});
