import { describe, it } from 'node:test';
import { strict as assert } from 'node:assert';
import {
    ROUTING_NUMBER_REGEX,
    ACCOUNT_NUMBER_REGEX,
    computeRoutingCheckDigit,
    validateRoutingNumber,
    isRoutingNumberValid,
    computeMod9CheckDigit,
    computeMod10CheckDigit,
    detectCheckMethod,
    validateAccountNumber,
    isAccountNumberValid,
    validateAccountPair,
    parseRoutingNumber,
    formatRoutingNumber,
    stripRoutingNumber,
    formatAccountNumber,
} from './routingUtils';

// ═══════════════════════════════════════════
// Regex patterns
// ═══════════════════════════════════════════
describe('ROUTING_NUMBER_REGEX', () => {
    it('matches exactly 9 digits', () => {
        assert.equal(ROUTING_NUMBER_REGEX.test('121042882'), true);
    });
    it('rejects too few digits', () => {
        assert.equal(ROUTING_NUMBER_REGEX.test('12104288'), false);
    });
    it('rejects too many digits', () => {
        assert.equal(ROUTING_NUMBER_REGEX.test('1210428821'), false);
    });
    it('rejects non-digits', () => {
        assert.equal(ROUTING_NUMBER_REGEX.test('12104288X'), false);
    });
});

describe('ACCOUNT_NUMBER_REGEX', () => {
    it('matches numeric strings', () => {
        assert.equal(ACCOUNT_NUMBER_REGEX.test('123456789'), true);
    });
    it('rejects letters', () => {
        assert.equal(ACCOUNT_NUMBER_REGEX.test('123abc'), false);
    });
    it('rejects empty', () => {
        assert.equal(ACCOUNT_NUMBER_REGEX.test(''), false);
    });
});

// ═══════════════════════════════════════════
// Routing number check digit (mod 11)
// ═══════════════════════════════════════════
describe('computeRoutingCheckDigit', () => {
    it('021000021 (Chase)', () => {
        assert.equal(computeRoutingCheckDigit('021000021'), 1);
    });
    it('071000013 (US Bank)', () => {
        assert.equal(computeRoutingCheckDigit('071000013'), 3);
    });
    it('121042882 (Wells Fargo)', () => {
        assert.equal(computeRoutingCheckDigit('121042882'), 2);
    });
});

// ═══════════════════════════════════════════
// validateRoutingNumber
// ═══════════════════════════════════════════
describe('validateRoutingNumber', () => {
    it('accepts valid routing number', () => {
        const result = validateRoutingNumber('021000021');
        assert.equal(result.valid, true);
        assert.equal(result.checkDigit, 1);
    });
    it('rejects wrong check digit', () => {
        const result = validateRoutingNumber('021000022');
        assert.equal(result.valid, false);
        assert.equal(result.expectedCheckDigit, 1);
    });
    it('rejects wrong length', () => {
        const result = validateRoutingNumber('02100002');
        assert.equal(result.valid, false);
    });
    it('Federal Reserve district decoding', () => {
        const r12a = validateRoutingNumber('121042882'); // Wells Fargo - San Francisco (district 12)
        assert.equal(r12a.federalReserveDistrict, 12);
        const r12b = validateRoutingNumber('122105155'); // San Francisco (district 12)
        assert.equal(r12b.federalReserveDistrict, 12);
    });
});

// ═══════════════════════════════════════════
// isRoutingNumberValid (shorthand)
// ═══════════════════════════════════════════
describe('isRoutingNumberValid', () => {
    it('returns true for valid', () => {
        assert.equal(isRoutingNumberValid('021000021'), true);
    });
    it('returns false for invalid', () => {
        assert.equal(isRoutingNumberValid('000000000'), false);
    });
    it('returns false for wrong length', () => {
        assert.equal(isRoutingNumberValid('12345'), false);
    });
});

// ═══════════════════════════════════════════
// Mod-9 check digit
// ═══════════════════════════════════════════
describe('computeMod9CheckDigit', () => {
    it('basic example: "12345678"', () => {
        // sum of 1+2+3+4+5+6+7+8 = 36; 36 % 9 = 0
        assert.equal(computeMod9CheckDigit('123456789'), 0);
    });
    it('single digit prefix', () => {
        assert.equal(computeMod9CheckDigit('50'), 5);
    });
});

// ═══════════════════════════════════════════
// Mod-10 check digit
// ═══════════════════════════════════════════
describe('computeMod10CheckDigit', () => {
    it('basic: "12345678"', () => {
        // sum = 36; (10 - 36%10) % 10 = (10-6)%10 = 4
        assert.equal(computeMod10CheckDigit('123456789'), 4);
    });
    it('sum already divisible by 10', () => {
        // "19" -> sum=10, (10-10%10)%10 = 0
        assert.equal(computeMod10CheckDigit('190'), 0);
    });
});

// ═══════════════════════════════════════════
// detectCheckMethod
// ═══════════════════════════════════════════
describe('detectCheckMethod', () => {
    it('detects mod9', () => {
        // Account "123456789" with mod9: sum(1..8)=36, 36%9=0, last=9≠0
        // Account "123456780": last=0, sum(1..8)=36, 36%9=0 → mod9
        const methods = detectCheckMethod('123456780');
        assert.ok(methods.includes('mod9'));
    });
    it('detects mod10', () => {
        // "10": sum(1)=1, (10-1%10)%10=9, last=0 ≠ 9
        // "123456789": sum=36, (10-6)%10=4, last=9≠4
        // "123456784": sum=36, (10-6)%10=4, last=4 → mod10
        const methods = detectCheckMethod('123456784');
        assert.ok(methods.includes('mod10'));
    });
    it('returns empty array when no method matches', () => {
        const methods = detectCheckMethod('1');
        assert.equal(methods.length, 0);
    });
    it('single digit returns none', () => {
        const methods = detectCheckMethod('5');
        assert.equal(methods.length, 0);
    });
});

// ═══════════════════════════════════════════
// validateAccountNumber
// ═══════════════════════════════════════════
describe('validateAccountNumber', () => {
    it('rejects non-numeric', () => {
        const result = validateAccountNumber('abc123');
        assert.equal(result.valid, false);
    });
    it('rejects too short (less than 4 digits)', () => {
        const result = validateAccountNumber('12');
        assert.equal(result.valid, false);
    });
    it('rejects too long (more than 17 digits)', () => {
        const result = validateAccountNumber('123456789012345678');
        assert.equal(result.valid, false);
    });
    it('accepts 4-digit minimum', () => {
        const result = validateAccountNumber('1234');
        assert.equal(result.valid, true);
    });
    it('accepts 17-digit maximum', () => {
        const result = validateAccountNumber('12345678901234567');
        assert.equal(result.valid, true);
    });
    it('detects check method for valid account', () => {
        const result = validateAccountNumber('123456784');
        assert.equal(result.valid, true);
        assert.ok(result.checkMethod?.includes('mod10'));
    });
});

// ═══════════════════════════════════════════
// isAccountNumberValid (shorthand)
// ═══════════════════════════════════════════
describe('isAccountNumberValid', () => {
    it('returns true for valid', () => {
        assert.equal(isAccountNumberValid('1234567890'), true);
    });
    it('returns false for non-numeric', () => {
        assert.equal(isAccountNumberValid('abc'), false);
    });
});

// ═══════════════════════════════════════════
// validateAccountPair
// ═══════════════════════════════════════════
describe('validateAccountPair', () => {
    it('rejects identical source and destination', () => {
        const result = validateAccountPair('021000021', '1234567890', '1234567890');
        assert.equal(result.valid, false);
    });
    it('accepts different accounts with same routing', () => {
        const result = validateAccountPair('021000021', '1234567890', '1234567891');
        assert.equal(result.valid, true);
    });
    it('rejects invalid routing number', () => {
        const result = validateAccountPair('000000000', '1234567890', '1234567891');
        assert.equal(result.valid, false);
    });
    it('rejects invalid source account', () => {
        const result = validateAccountPair('021000021', 'ab', '1234567891');
        assert.equal(result.valid, false);
    });
});

// ═══════════════════════════════════════════
// parseRoutingNumber
// ═══════════════════════════════════════════
describe('parseRoutingNumber', () => {
    it('parses Chase 021000021', () => {
        const info = parseRoutingNumber('021000021');
        assert.ok(info !== null);
        assert.equal(info?.federalReserveDistrict, 2); // New York Fed
        assert.equal(info?.institutionType, 'Unknown (2)'); // digit 7 of 021000021 is '2'
    });
    it('parses San Francisco district (1xx)', () => {
        const info = parseRoutingNumber('121042882');
        assert.ok(info !== null);
        assert.equal(info?.federalReserveDistrict, 12);
    });
    it('returns null for invalid routing number', () => {
        assert.equal(parseRoutingNumber('000000000'), null);
    });
    it('returns null for non-9-digit string', () => {
        assert.equal(parseRoutingNumber('12345'), null);
    });
    it('parses thrift indicator', () => {
        // digit at index 6 in range 5-7 => thrift
        const info = parseRoutingNumber('071000013');
        assert.equal(info?.institutionType, 'Thrift Institution');
    });
});

// ═══════════════════════════════════════════
// format / strip / format helpers
// ═══════════════════════════════════════════
describe('formatRoutingNumber', () => {
    it('formats 9 digits with dashes', () => {
        assert.equal(formatRoutingNumber('021000021'), '0210-00021');
    });
    it('truncates if longer than 9', () => {
        const result = formatRoutingNumber('0210000213');
        assert.ok(result.length <= 11);
    });
});

describe('stripRoutingNumber', () => {
    it('removes non-digit characters', () => {
        assert.equal(stripRoutingNumber('0210-00021'), '021000021');
    });
    it('handles dashes', () => {
        assert.equal(stripRoutingNumber('021-000-021'), '021000021');
    });
    it('handles spaces', () => {
        assert.equal(stripRoutingNumber('021 000 021'), '021000021');
    });
});

describe('formatAccountNumber', () => {
    it('groups digits in fours from the right', () => {
        assert.equal(formatAccountNumber('1234567890'), '12-3456-7890');
    });
    it('handles short account', () => {
        assert.equal(formatAccountNumber('1234'), '1234');
    });
    it('handles long account (17 digits)', () => {
        const result = formatAccountNumber('12345678901234567');
        assert.ok(result.includes('-'));
    });
});
