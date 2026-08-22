import { AbaValidationResult, FedRail, FedRailBadgeInfo, VaultYieldResult } from './types';

// Federal Reserve District Lookup Map
const FED_DISTRICT_MAP: Record<string, string> = {
  '01': 'Boston',
  '02': 'New York',
  '03': 'Philadelphia',
  '04': 'Cleveland',
  '05': 'Richmond',
  '06': 'Atlanta',
  '07': 'Chicago',
  '08': 'St. Louis',
  '09': 'Minneapolis',
  '10': 'Kansas City',
  '11': 'Dallas',
  '12': 'San Francisco',
  '21': 'Boston (Thrift)',
  '22': 'New York (Thrift)',
  '23': 'Philadelphia (Thrift)',
  '24': 'Cleveland (Thrift)',
  '25': 'Richmond (Thrift)',
  '26': 'Atlanta (Thrift)',
  '27': 'Chicago (Thrift)',
  '28': 'St. Louis (Thrift)',
  '29': 'Minneapolis (Thrift)',
  '30': 'Kansas City (Thrift)',
  '31': 'Dallas (Thrift)',
  '32': 'San Francisco (Thrift)',
};

/**
 * Validates a 9-digit US Federal Reserve ABA Routing Number using Mod-10 checksum:
 * Sum = 3*(d1 + d4 + d7) + 7*(d2 + d5 + d8) + 1*(d3 + d6 + d9) mod 10 == 0
 */
export function validateAbaRouting(routing: string): AbaValidationResult {
  const clean = routing.replace(/\D/g, '');
  if (clean.length !== 9) {
    return { valid: false, error: 'Routing number must be exactly 9 digits' };
  }

  const digits = clean.split('').map(Number);
  const checksum =
    3 * (digits[0] + digits[3] + digits[6]) +
    7 * (digits[1] + digits[4] + digits[7]) +
    1 * (digits[2] + digits[5] + digits[8]);

  if (checksum % 10 !== 0) {
    return { valid: false, error: 'Invalid ABA routing checksum' };
  }

  const prefix = clean.substring(0, 2);
  const district = FED_DISTRICT_MAP[prefix] || 'Federal Reserve System';

  return {
    valid: true,
    routing: clean,
    district,
  };
}

/**
 * Calculates compound yield for a High-Yield Savings Vault given balance in cents and APY percent.
 */
export function calculateVaultYield(balanceCents: number, apyPercent: number): VaultYieldResult {
  if (balanceCents <= 0 || apyPercent <= 0) {
    return {
      annualCents: 0,
      monthlyCents: 0,
      dailyCents: 0,
      formattedApy: `${apyPercent.toFixed(2)}% APY`,
    };
  }

  const annualCents = Math.round((balanceCents * apyPercent) / 100);
  const monthlyCents = Math.round(annualCents / 12);
  const dailyCents = Math.round(annualCents / 365);

  return {
    annualCents,
    monthlyCents,
    dailyCents,
    formattedApy: `${apyPercent.toFixed(2)}% APY`,
  };
}

/**
 * Formats metadata and badge presentation for Federal Reserve settlement rails.
 */
export function formatFedRailBadge(rail: string): FedRailBadgeInfo {
  switch (rail.toLowerCase()) {
    case 'fednow':
      return {
        rail: 'fednow',
        label: 'FedNow 24/7',
        speed: 'Instant (2.5s)',
        fee: '$0.00',
        color: 'emerald',
        icon: 'Zap',
        description: 'Federal Reserve instant real-time gross settlement',
      };
    case 'wire':
    case 'fedwire':
      return {
        rail: 'wire',
        label: 'Fedwire RTGS',
        speed: 'Real-time (Same day)',
        fee: '$15.00',
        color: 'indigo',
        icon: 'Landmark',
        description: 'High-value institutional real-time settlement with IMAD/OMAD',
      };
    case 'ach':
    case 'fedach':
      return {
        rail: 'ach',
        label: 'FedACH Direct',
        speed: '1-2 Business Days',
        fee: '$0.00',
        color: 'amber',
        icon: 'Clock',
        description: 'Batch automated clearing house direct debit/deposit',
      };
    default:
      return {
        rail: 'internal',
        label: 'Internal P2P',
        speed: 'Instant',
        fee: '$0.00',
        color: 'purple',
        icon: 'Send',
        description: 'Direct intra-bank ledger transfer',
      };
  }
}

/**
 * Masks 16-digit card numbers for PCI-DSS compliant consumer display (e.g. 5542 •••• •••• 4567).
 */
export function formatCardNumberMasked(cardNum: string): string {
  const clean = cardNum.replace(/\s+/g, '');
  if (clean.length !== 16) return cardNum;
  return `${clean.slice(0, 4)} •••• •••• ${clean.slice(12, 16)}`;
}

/**
 * Formats raw merchant names / transaction descriptions into recognizable brand titles.
 */
export function formatMerchantName(rawName: string): string {
  if (!rawName) return 'Transaction';
  const upper = rawName.toUpperCase();

  if (upper.includes('NETFLIX')) return 'Netflix';
  if (upper.includes('UBER')) return 'Uber';
  if (upper.includes('STARBUCKS')) return 'Starbucks';
  if (upper.includes('PG&E') || upper.includes('ELECTRIC')) return 'PG&E Electric Utility';
  if (upper.includes('VANGUARD')) return 'Vanguard Settlement';
  if (upper.includes('APPLE')) return 'Apple';
  if (upper.includes('AMAZON')) return 'Amazon';
  if (upper.includes('SPOTIFY')) return 'Spotify';

  // Capitalize words nicely if not recognized
  return rawName
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Groups an array of transaction events chronologically into Today, Yesterday, or formatted Date headers.
 */
export function groupTransactionsByDate<T extends { created_at?: string; event_time?: string }>(
  events: T[]
): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  const today = new Date();
  const todayDateStr = today.toDateString();

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayDateStr = yesterday.toDateString();

  for (const event of events) {
    const rawDate = event.created_at || event.event_time;
    if (!rawDate) {
      groups['Earlier'] = groups['Earlier'] || [];
      groups['Earlier'].push(event);
      continue;
    }

    const txDate = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
    const txDateStr = txDate.toDateString();

    let header = txDateStr;
    if (txDateStr === todayDateStr) {
      header = 'Today';
    } else if (txDateStr === yesterdayDateStr) {
      header = 'Yesterday';
    } else {
      header = txDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: txDate.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
      });
    }

    if (!groups[header]) {
      groups[header] = [];
    }
    groups[header].push(event);
  }

  return groups;
}

/**
 * Determines whether a transaction is an income (inflow) or expense (outflow).
 * Handles ClickHouse records, Postgres models, and simulator activities.
 */
export function isTransactionIncome(tx: any, userEmail?: string): boolean {
  if (!tx) return false;

  // 1. Explicit transaction_side from ClickHouse / backend
  if (tx.transaction_side === 'CREDIT') return true;
  if (tx.transaction_side === 'DEBIT') return false;

  // 2. Explicit transaction_type
  const txType = (tx.transaction_type || '').toLowerCase();
  if (
    txType === 'income' ||
    txType === 'salary' ||
    txType === 'deposit' ||
    txType === 'interest' ||
    txType === 'cashback'
  ) {
    return true;
  }
  if (
    txType === 'expense' ||
    txType === 'payment' ||
    txType === 'purchase' ||
    txType === 'withdrawal' ||
    txType === 'fee'
  ) {
    return false;
  }

  // 3. Counterparty / merchant text markers
  const merchant = (tx.merchant || tx.counterparty || '').toLowerCase();
  if (merchant.startsWith('from ')) return true;
  if (merchant.startsWith('to ')) return false;

  // 4. Email check for P2P
  if (userEmail) {
    const cleanUser = userEmail.toLowerCase();
    if (
      tx.recipient_email &&
      tx.recipient_email.toLowerCase() === cleanUser &&
      tx.sender_email &&
      tx.sender_email.toLowerCase() !== cleanUser
    ) {
      return true;
    }
    if (tx.sender_email && tx.sender_email.toLowerCase() === cleanUser) {
      return false;
    }
  }

  // 5. Merchant presence check: If a merchant is present (Shell, AMC, Chipotle, etc.), it is an expense!
  if (
    tx.merchant &&
    !merchant.includes('deposit') &&
    !merchant.includes('salary') &&
    !merchant.includes('payroll')
  ) {
    return false;
  }

  // 6. Category heuristics
  const cat = (tx.category || '').toLowerCase();
  if (cat.includes('income') || cat.includes('salary') || cat.includes('deposit')) {
    return true;
  }
  if (
    cat.includes('dining') ||
    cat.includes('transport') ||
    cat.includes('entertainment') ||
    cat.includes('groceries') ||
    cat.includes('utilities') ||
    cat.includes('shopping') ||
    cat.includes('rent') ||
    cat.includes('insurance')
  ) {
    return false;
  }

  // 7. Fallback to amount sign if explicitly negative
  if (typeof tx.amount === 'number' && tx.amount < 0) {
    return false;
  }

  return false;
}

export function isTransactionExpense(tx: any, userEmail?: string): boolean {
  return !isTransactionIncome(tx, userEmail);
}

export type TimeRange = '24h' | '7d' | '30d' | '90d' | '1y';

export function getTimeRangeHours(range: TimeRange): number {
  switch (range) {
    case '24h':
      return 24;
    case '7d':
      return 168;
    case '30d':
      return 720;
    case '90d':
      return 2160;
    case '1y':
      return 8760;
    default:
      return 720;
  }
}

/**
 * Filters transaction records by timestamp window relative to current time.
 */
export function filterTransactionsByTimeRange<T extends { created_at?: string; event_time?: string }>(
  transactions: T[],
  range: TimeRange,
  refDate: Date = new Date()
): T[] {
  const hours = getTimeRangeHours(range);
  const cutoffMs = refDate.getTime() - hours * 3600 * 1000;

  return transactions.filter((tx) => {
    const rawDate = tx.created_at || tx.event_time;
    if (!rawDate) return true;
    const txTime = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z').getTime();
    return isNaN(txTime) || txTime >= cutoffMs;
  });
}

export interface ChartDataPoint {
  date: string;
  amount: number;
  count: number;
}

/**
 * Aggregates transactions into discrete time intervals (hours, days, weeks, months)
 * matching the selected timeframe so the curve dynamically transforms.
 */
export function generateChartBuckets<T extends { amount?: number; created_at?: string; event_time?: string }>(
  transactions: T[],
  range: TimeRange,
  refDate: Date = new Date()
): ChartDataPoint[] {
  const points: ChartDataPoint[] = [];

  if (range === '24h') {
    for (let i = 23; i >= 0; i--) {
      const bucketTime = new Date(refDate.getTime() - i * 3600 * 1000);
      const label = bucketTime.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
      const bucketStart = bucketTime.getTime() - 1800 * 1000;
      const bucketEnd = bucketTime.getTime() + 1800 * 1000;

      const matching = transactions.filter((tx) => {
        const rawDate = tx.created_at || tx.event_time;
        if (!rawDate) return false;
        const t = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z').getTime();
        return t >= bucketStart && t < bucketEnd;
      });

      const totalCents = matching.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
      points.push({ date: label, amount: Math.round(totalCents / 100), count: matching.length });
    }
  } else if (range === '7d') {
    for (let i = 6; i >= 0; i--) {
      const d = new Date(refDate);
      d.setDate(d.getDate() - i);
      const label = d.toLocaleDateString('en-US', { weekday: 'short' });
      const dateStr = d.toDateString();

      const matching = transactions.filter((tx) => {
        const rawDate = tx.created_at || tx.event_time;
        if (!rawDate) return false;
        const t = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
        return t.toDateString() === dateStr;
      });

      const totalCents = matching.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
      points.push({ date: label, amount: Math.round(totalCents / 100), count: matching.length });
    }
  } else if (range === '30d') {
    for (let i = 14; i >= 0; i--) {
      const d = new Date(refDate);
      d.setDate(d.getDate() - i * 2);
      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const startMs = d.getTime() - 24 * 3600 * 1000;
      const endMs = d.getTime() + 24 * 3600 * 1000;

      const matching = transactions.filter((tx) => {
        const rawDate = tx.created_at || tx.event_time;
        if (!rawDate) return false;
        const t = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z').getTime();
        return t >= startMs && t < endMs;
      });

      const totalCents = matching.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
      points.push({ date: label, amount: Math.round(totalCents / 100), count: matching.length });
    }
  } else if (range === '90d') {
    for (let i = 11; i >= 0; i--) {
      const d = new Date(refDate);
      d.setDate(d.getDate() - i * 7);
      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const startMs = d.getTime() - 3.5 * 24 * 3600 * 1000;
      const endMs = d.getTime() + 3.5 * 24 * 3600 * 1000;

      const matching = transactions.filter((tx) => {
        const rawDate = tx.created_at || tx.event_time;
        if (!rawDate) return false;
        const t = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z').getTime();
        return t >= startMs && t < endMs;
      });

      const totalCents = matching.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
      points.push({ date: label, amount: Math.round(totalCents / 100), count: matching.length });
    }
  } else {
    for (let i = 11; i >= 0; i--) {
      const d = new Date(refDate.getFullYear(), refDate.getMonth() - i, 1);
      const label = d.toLocaleDateString('en-US', { month: 'short' });
      const targetMonth = d.getMonth();
      const targetYear = d.getFullYear();

      const matching = transactions.filter((tx) => {
        const rawDate = tx.created_at || tx.event_time;
        if (!rawDate) return false;
        const t = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
        return t.getMonth() === targetMonth && t.getFullYear() === targetYear;
      });

      const totalCents = matching.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
      points.push({ date: label, amount: Math.round(totalCents / 100), count: matching.length });
    }
  }

  return points;
}

