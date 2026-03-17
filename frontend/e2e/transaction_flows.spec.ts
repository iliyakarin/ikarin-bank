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
        
        // Use part of the label and wait for it
        await page.locator('select:has-text("Select a company")').selectOption({ label: 'Austin Energy (Utilities)' });
        await page.fill('input[placeholder="e.g. 1002345"]', 'SUB-999');
        await page.click('button:has-text("Save Merchant")');
        await expect(page.locator('text=Contact added successfully')).toBeVisible();

        // 2. Perform Merchant Payment
        await page.click('a[href="/client/send"]');
        await page.fill('input[placeholder="user@example.com"]', 'AE'); // search by name fragment
        const merchantOption = page.locator('text=Austin Energy').last();
        await merchantOption.waitFor({ state: 'visible' });
        await merchantOption.click({ force: true });
        
        await expect(page.locator('input[placeholder="Enter your subscriber ID"]')).toHaveValue('SUB-999');
        
        await page.fill('input[placeholder="0.00"]', '120.50');
        
        const merchantSendBtn = page.locator('button:has-text("Send Instantly")');
        await expect(merchantSendBtn).toBeEnabled();
        await merchantSendBtn.click();
        
        // Confirm
        const merchantModalTitle = page.locator('h3:has-text("Confirm Instant Transfer")');
        await expect(merchantModalTitle).toBeVisible({ timeout: 10000 });
        await page.click('button:has-text("Send Now")');
        await expect(page.locator('text=Transaction ID:')).toBeVisible({ timeout: 15000 });
    });

    test('Flow A3: External Bank Account Addition', async ({ page }) => {
        await registerAndLogin(page, `bank_test_${Math.floor(Math.random() * 10000)}@test.com`);

        await page.click('a[href="/client/contacts"]');
        
        // Wait for metadata
        await page.waitForResponse(resp => resp.url().includes('/api/v1/banks') && resp.status() === 200);
        
        await page.click('button:has-text("BANK")');
        
        await page.locator('select:has-text("Select a bank")').selectOption({ label: 'Chase' });
        await page.fill('input[placeholder="Ending in..."]', '987654321');
        await page.fill('input[placeholder="e.g. Alice P. Smith"]', 'My External Account');
        
        await page.click('button:has-text("Save Account")');
        await expect(page.locator('text=Contact added successfully')).toBeVisible();
        
        // Verify it appears in the list
        await expect(page.locator('text=RTN: 021000021')).toBeVisible();
        await expect(page.locator('text=****4321')).toBeVisible();
    });
});
