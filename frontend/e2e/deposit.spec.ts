import { test, expect } from '@playwright/test';

// Use same basic auth setup as other tests
test.describe('Deposit E2E Flow', () => {
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

    // Navigate to Deposit
    await page.click('text="Deposit Funds"');
    await expect(page).toHaveURL(/.*\/deposit/);
    await expect(page.locator('h1')).toContainText('Deposit Funds');
  });

  test('Validates Top-Up Flow', async ({ page }) => {
    // Log console errors
    page.on('console', msg => {
      console.log(`BROWSER ${msg.type().toUpperCase()}: ${msg.text()}`);
    });

    await page.waitForTimeout(1000); // stable wait

    // Listen for intent creation
    const intentPromise = page.waitForResponse(response =>
      response.url().includes('/deposits/payment_intents')
    );

    // Click the "Starter" button ($10.00)
    await page.click('button:has-text("Starter")');
    const intentResponse = await intentPromise;
    console.log(`intent response status: ${intentResponse.status()}`);
    expect(intentResponse.status()).toBe(200);

    // Verify Modal Appears
    await expect(page.locator('text="Deposit $10 to Main Account"')).toBeVisible();

    // Fill form
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe');
    await page.fill('input[placeholder="4242 4242 4242 4242"]', '4242424242424242');
    await page.fill('input[placeholder="MM"]', '12');
    await page.fill('input[placeholder="YYYY"]', '2030');
    await page.fill('input[placeholder="123"]', '123');

    // Wait for the final confirmation requests
    const fulfillPromise = page.waitForResponse(response =>
      response.url().includes('/deposits/fulfill-payment')
    );

    // In mock mode, we don't expect a real confirm request as the mock form handles it
    // Provide handler for alert
    page.on('dialog', dialog => dialog.accept());
    await page.click('button:has-text("Deposit $10 to Main Account")');

    const fulfillResponse = await fulfillPromise;
    console.log(`fulfill response status: ${fulfillResponse.status()}`);
    expect(fulfillResponse.status()).toBe(200);
    // expect(confirmResponse.status()).toBe(200); 

    // In mock mode we just close the modal, so check it's gone
    await expect(page.locator('text="Deposit $10 to Main Account"')).not.toBeVisible();
  });
});

