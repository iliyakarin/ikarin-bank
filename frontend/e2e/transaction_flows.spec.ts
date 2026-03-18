import { test, expect } from '@playwright/test';

test.describe('Transaction Integrity Flows', () => {
    const password = "REDACTED!";
    const emailA = `userA_${Math.floor(Math.random() * 100000)}@test.com`;
    const emailB = `userB_${Math.floor(Math.random() * 100000)}@test.com`;

    async function registerAndLogin(page: any, email: string) {
        await page.goto('/auth/register');
        await page.fill('input[placeholder="John"]', 'Test');
        await page.fill('input[placeholder="Doe"]', 'User');
        await page.fill('input[type="email"]', email);
        await page.fill('input[placeholder="••••••••••••••••"]', password);
        await page.click('button:has-text("Register Now")');
        await expect(page).toHaveURL(/\/auth\/login/);

        await page.fill('input[type="email"]', email);
        await page.fill('input[type="password"]', password);
        await page.click('button:has-text("Sign In")');
        await expect(page).toHaveURL(/\/client/);
        
        // Initial Deposit to ensure funds
        await page.click('a[href="/client/deposit"]');
        await page.click('button:has-text("Popular")'); // More specific button select
        
        // Modal interaction - more flexible locator
        const depositModalBtn = page.locator('button:has-text("Deposit")').filter({ hasText: "Main Account" });
        await depositModalBtn.waitFor({ state: 'visible', timeout: 20000 });
        await depositModalBtn.click();
        
        await expect(page.locator('text=Deposit successful')).toBeVisible({ timeout: 20000 });
        console.log(`Deposited $100.00 for ${email} successfully.`);
    }

    test('Flow A1: Internal P2P Transfer from A to B', async ({ page, browser }) => {
        page.on('console', msg => console.log(`[BROWSER CONSOLE] ${msg.type().toUpperCase()}: ${msg.text()}`));
        // 1. Setup User B
        const contextB = await browser.newContext();
        const pageB = await contextB.newPage();
        await registerAndLogin(pageB, emailB);
        await contextB.close();

        // 2. Setup User A
        await registerAndLogin(page, emailA);

        // 3. Add User B as Contact
        await page.click('a[href="/client/contacts"]');
        await page.click('button:has-text("KARIN")');
        await page.fill('input[placeholder="e.g. Alice Smith"]', 'User B');
        await page.fill('input[placeholder="alice@example.com"]', emailB);
        await page.click('button:has-text("Save Contact")');
        await expect(page.locator('text=Contact added successfully')).toBeVisible();

        // 4. Perform Transfer
        await page.click('a[href="/client/send"]');
        await page.click('button:has-text("Instant")'); // Explicit tab select
        
        await page.fill('input[placeholder="user@example.com"]', emailB);
        
        // Wait for dropdown and select
        const contactOption = page.locator(`div:has-text("${emailB}")`).last();
        await contactOption.waitFor({ state: 'visible' });
        await contactOption.click({ force: true }); 
        
        await page.fill('input[placeholder="0.00"]', '50.00');
        await page.fill('textarea[placeholder="What is this for?"]', 'Lunch money');
        
        await page.waitForTimeout(2000); // Wait for form settlement
        const sendBtn = page.locator('button:has-text("Send Instantly")');
        await expect(sendBtn).toBeEnabled();
        await sendBtn.click();
        
        // Modal Confirm
        const modalTitle = page.locator('h3:has-text("Confirm Instant Transfer")');
        await expect(modalTitle).toBeVisible({ timeout: 15000 });
        await page.click('button:has-text("Send Now")');

        // Verify Success or Error using a more robust wait
        console.log("Waiting for transaction result toast...");
        
        // Wait for ANY toast to appear
        const anyToast = page.locator('div[class*="z-[200]"] > div');
        await anyToast.first().waitFor({ state: 'visible', timeout: 30000 });
        
        const successToast = page.locator('text=Transaction ID:');
        const errorToast = page.locator('h4:has-text("Error"), .text-red-200'); // Check for Error header or red text
        
        if (await successToast.isVisible()) {
            const txText = await successToast.textContent();
            console.log(`P2P Transaction successful: ${txText}`);
        } else if (await errorToast.isVisible()) {
            const errorText = await errorToast.textContent();
            console.error(`P2P Transaction failed with error visible: ${errorText}`);
            throw new Error(`Transaction failed: ${errorText}`);
        } else {
            const toastContent = await anyToast.first().textContent();
            console.warn(`Unexpected toast content: ${toastContent}`);
            throw new Error(`Unexpected result: ${toastContent}`);
        }

        // Verify History - Navigate to dedicated transactions page
        await page.goto('/client/transactions');
        const historyTable = page.locator('table');
        try {
            const transactionRow = page.locator('tr').filter({ hasText: emailB }).filter({ hasText: /-\$\s?50\.00/ });
            await expect(transactionRow).toBeVisible({ timeout: 15000 });
            console.log("P2P Transaction verified in history on dedicated page.");
        } catch (e) {
            const tableText = await historyTable.textContent();
            console.error(`History verification failed on transactions page. Table content: ${tableText}`);
            throw e;
        }
    });

    test('Flow A2: Merchant Payment (Simulated)', async ({ page }) => {
        await registerAndLogin(page, `merchant_test_${Math.floor(Math.random() * 10000)}@test.com`);

        // 1. Add Merchant Contact (Austin Energy)
        await page.click('a[href="/client/contacts"]');
        
        // Wait for metadata to load
        await page.waitForResponse(resp => resp.url().includes('/api/v1/vendors') && resp.status() === 200);
        
        await page.click('button:has-text("MERCHANT")');
        
        // Fix: Force click and wait for state to settle
        const merchantSelect = page.locator('select');
        await merchantSelect.waitFor();
        await merchantSelect.selectOption({ label: 'Austin Energy (Utilities)' });
        
        await page.fill('input[placeholder="e.g. 1002345"]', 'SUB-999');
        await page.fill('input[placeholder="e.g. My Electric Bill"]', 'Austin Energy');
        
        // Wait a beat for React state
        await page.waitForTimeout(1000);
        
        const saveMerchantBtn = page.locator('button:has-text("Save Merchant")');
        // Aggressively click even if Playwright thinks it's disabled, as a fallback
        await saveMerchantBtn.click({ force: true });
        await expect(page.locator('text=Contact added successfully')).toBeVisible({ timeout: 10000 });

        // 2. Perform Merchant Payment
        await page.click('a[href="/client/send"]');
        await page.fill('input[placeholder="user@example.com"]', 'Austin');
        // Target the contact result specifically (it has the "Merchant:" tag in the description)
        const merchantOption = page.locator('.group:has-text("Austin Energy")').first();
        await merchantOption.waitFor({ state: 'visible' });
        await merchantOption.click({ force: true });
        
        // Wait for subscriber ID to appear and be filled (handled by our new effect or the click handler)
        const subIdInput = page.locator('input[placeholder="Enter your subscriber ID"]');
        await subIdInput.waitFor({ state: 'visible' });
        await expect(subIdInput).toHaveValue('SUB-999', { timeout: 10000 });
        
        await page.fill('input[placeholder="0.00"]', '20.50');
        
        const merchantSendBtn = page.locator('button:has-text("Send Instantly")');
        // Wait for dropdown to close or force it (clicking the amount input should have closed it, but let's be safe)
        if (await page.locator('.group:has-text("Austin Energy")').first().isVisible()) {
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
        }
        
        await expect(merchantSendBtn).toBeEnabled();
        await merchantSendBtn.click({ force: true });
        
        // Confirm
        const merchantModalTitle = page.locator('h3:has-text("Confirm Instant Transfer")');
        await expect(merchantModalTitle).toBeVisible({ timeout: 10000 });
        await page.click('button:has-text("Send Now")');
        
        // Wait for the success toast.
        await expect(page.locator('[data-testid="success-toast"]')).toBeVisible({ timeout: 20000 });
        await expect(page.locator('text=/Transaction ID:/')).toBeVisible({ timeout: 5000 });
    });

    test('Flow A3: External Bank Account Addition', async ({ page }) => {
        await registerAndLogin(page, `bank_test_${Math.floor(Math.random() * 10000)}@test.com`);

        await page.click('a[href="/client/contacts"]');
        
        // Wait for metadata
        await page.waitForResponse(resp => resp.url().includes('/api/v1/banks') && resp.status() === 200);
        
        await page.click('button:has-text("BANK")');
        
        // Fix: Force click
        const bankSelect = page.locator('select');
        await bankSelect.waitFor();
        await bankSelect.selectOption({ label: 'Chase' });
        
        await page.fill('input[placeholder="Ending in..."]', '987654321');
        await page.fill('input[placeholder="e.g. Alice P. Smith"]', 'My Bank Account');
        
        await page.waitForTimeout(1000);
        
        const saveAccountBtn = page.locator('button:has-text("Save Account")');
        await saveAccountBtn.click({ force: true });
        await expect(page.locator('text=Contact added successfully')).toBeVisible({ timeout: 10000 });
        
        // Verify it appears in the list
        await expect(page.locator('text=RTN: 021000021')).toBeVisible();
        await expect(page.locator('text=****4321')).toBeVisible();
    });
});
