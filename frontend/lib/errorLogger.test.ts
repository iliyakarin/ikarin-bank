import { test } from 'node:test';
import assert from 'node:assert';
import { determineErrorSeverity } from './errorLogger.ts';

test('determineErrorSeverity - critical patterns', () => {
  // Network errors
  assert.strictEqual(determineErrorSeverity(new Error('Network error occurred')), 'critical');
  assert.strictEqual(determineErrorSeverity(new Error('A network timeout error')), 'critical');

  // Auth and permissions
  assert.strictEqual(determineErrorSeverity(new Error('Authentication failed')), 'critical');
  assert.strictEqual(determineErrorSeverity(new Error('Permission denied')), 'critical');

  // System limits
  assert.strictEqual(determineErrorSeverity(new Error('Quota exceeded')), 'critical');

  // Security
  assert.strictEqual(determineErrorSeverity(new Error('Security violation detected')), 'critical');
});

test('determineErrorSeverity - high patterns', () => {
  // Database errors
  assert.strictEqual(determineErrorSeverity(new Error('Database connection failed')), 'high');

  // API errors
  assert.strictEqual(determineErrorSeverity(new Error('API error: 500 Internal Server Error')), 'high');

  // Validation
  assert.strictEqual(determineErrorSeverity(new Error('Validation failed for field email')), 'high');

  // Unauthorized (distinct from Authentication failed)
  assert.strictEqual(determineErrorSeverity(new Error('User is unauthorized')), 'high');
});

test('determineErrorSeverity - medium patterns', () => {
  assert.strictEqual(determineErrorSeverity(new Error('Failed to fetch data')), 'medium');
  assert.strictEqual(determineErrorSeverity(new Error('Connection timeout')), 'medium');
  assert.strictEqual(determineErrorSeverity(new Error('Connection reset by peer')), 'medium');
  assert.strictEqual(determineErrorSeverity(new Error('Bad request')), 'medium');
});

test('determineErrorSeverity - low (default)', () => {
  assert.strictEqual(determineErrorSeverity(new Error('Some random UI error')), 'low');
  assert.strictEqual(determineErrorSeverity(new Error('Unknown problem occurred')), 'low');
  assert.strictEqual(determineErrorSeverity(new Error('')), 'low');
});

test('determineErrorSeverity - case insensitivity', () => {
  assert.strictEqual(determineErrorSeverity(new Error('NETWORK ERROR')), 'critical');
  assert.strictEqual(determineErrorSeverity(new Error('database error')), 'high');
  assert.strictEqual(determineErrorSeverity(new Error('TIMEOUT')), 'medium');
});

test('determineErrorSeverity - precedence (critical over others)', () => {
  // Contains both 'network error' (critical) and 'database' (high)
  // Should return 'critical' because it's checked first
  assert.strictEqual(determineErrorSeverity(new Error('network error in database connection')), 'critical');
});

test('determineErrorSeverity - precedence (high over medium)', () => {
  // Contains both 'database' (high) and 'timeout' (medium)
  assert.strictEqual(determineErrorSeverity(new Error('database timeout')), 'high');
});
