import { test, expect } from '@playwright/test';

// Use same basic auth setup as other tests
test.describe('Stripe E2E Flow', () => {
  // Wait to setup before proceeding
  test.beforeEach(async ({ page }) => {
    // Navigate to local app
    await page.goto('/auth/login');
    // Login as the seed user created in start.sh
    await page.fill('input[type="email"]', process.env.ADMIN_EMAIL!);
    await page.fill('input[type="password"]', process.env.ADMIN_PASSWORD!);
    const signInButton = page.locator('button:has-text("Sign In")');
    await expect(signInButton).toBeEnabled({ timeout: 10000 });
    await signInButton.click();
    // Ensure we reached the dashboard
    await expect(page).toHaveURL(/.*\/client/);

    // Navigate to Stripe
    await page.click('text="Pay with Stripe"');
    await expect(page).toHaveURL(/.*\/stripe/);
    await expect(page.locator('h1')).toContainText('Pay with Stripe');
  });

  test('Validates Top-Up Flow', async ({ page }) => {
    await page.waitForTimeout(1000); // stable wait

    // Listen for intent creation
    const intentPromise = page.waitForResponse(response =>
      response.url().includes('/stripe/payment_intents')
    );

    await page.click('text="Add $10.00"');
    const intentResponse = await intentPromise;
    console.log(`intent response status: ${intentResponse.status()}`);
    expect(intentResponse.status()).toBe(200);

    // Verify Modal Appears
    await expect(page.locator('text="Complete Payment (10 USD)"')).toBeVisible();

    // Fill form
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe');
    await page.fill('input[placeholder="4242 4242 4242 4242"]', '4242424242424242');
    await page.fill('input[placeholder="MM"]', '12');
    await page.fill('input[placeholder="YYYY"]', '2030');
    await page.fill('input[placeholder="123"]', '123');

    // Wait for the final confirmation requests
    const pmPromise = page.waitForResponse(response =>
      response.url().includes('/stripe/payment_methods')
    );

    const confirmPromise = page.waitForResponse(response =>
      response.url().includes('/confirm')
    );

    // Provide handler for alert
    page.on('dialog', dialog => dialog.accept());

    await page.click('button:has-text("Pay $10")');

    const pmResponse = await pmPromise;
    console.log(`pm response status: ${pmResponse.status()}`);
    expect(pmResponse.status()).toBe(200);

    const confirmResponse = await confirmPromise;
    console.log(`confirm response status: ${confirmResponse.status()}`);
    expect(confirmResponse.status()).toBe(200);

    // Ensure we are redirected away from the stripe page (usually back to dashboard)
    await expect(page).not.toHaveURL(/.*\/stripe/);
  });
});

