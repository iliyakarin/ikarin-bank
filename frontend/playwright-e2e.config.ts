import { defineConfig, devices } from '@playwright/test';
import baseConfig from './playwright.config';

export default defineConfig({
    ...baseConfig,
    outputDir: 'test-results-e2e',
    reporter: 'list',
    // Disable the last-run reporter which is causing permission issues
    metadata: {
        lastRun: false
    }
});
