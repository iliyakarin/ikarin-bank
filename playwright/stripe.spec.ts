import { test, expect } from '@playwright/test';

// Use same basic auth setup as other tests
test.describe('Stripe E2E Flow', () => {
  // Wait to setup before proceeding
  test.beforeEach(async ({ page }) => {
    // Navigate to local app
    await page.goto('http://localhost:3000/auth/login');
    // Login as the seed user created in start.sh
    await page.fill('input[name="email"]', 'ikarin@admin.com');
    await page.fill('input[name="password"]', 'admin123'); // assuming standard dev dummy creds
    await page.click('button[type="submit"]');
    // Ensure we reached the dashboard
    await expect(page).toHaveURL(/.*\/client/);
    
    // Navigate to Stripe
    await page.click('text="Pay with Stripe"');
    await expect(page).toHaveURL(/.*\/stripe/);
    await expect(page).locator('h1').toContainText('Pay with Stripe');
  });

  test('Validates Top-Up Flow', async ({ page }) => {
    await page.waitForTimeout(1000); // stable wait
    
    // Since we are not running Stripe mock via URL change, we'll listen to the network to ensure the payload is correct.
    const checkoutPromise = page.waitForResponse(response => 
      response.url().includes('/stripe/create-checkout-session') && response.status() === 200
    );

    // Initial click might redirect if the mock doesn't handle the redirect correctly in test environment, but we check if request fired.
    await page.click('text="Add $10.00"');
    
    const response = await checkoutPromise;
    const body = await response.json();

    expect(body.url).toBeDefined();
    // In our mock, the URL will be `http://stripe-mock` or `http://localhost`.
  });
});
