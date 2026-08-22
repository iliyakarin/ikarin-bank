export type FedRail = 'fednow' | 'wire' | 'ach' | 'internal' | 'card';

export interface FedRailBadgeInfo {
  rail: FedRail;
  label: string;
  speed: string;
  fee: string;
  color: string;
  icon: string;
  description: string;
}

export interface AbaValidationResult {
  valid: boolean;
  district?: string;
  routing?: string;
  error?: string;
}

export interface VaultYieldResult {
  annualCents: number;
  monthlyCents: number;
  dailyCents: number;
  formattedApy: string;
}

export interface StoryItem {
  id: string;
  tag: string;
  title: string;
  subtitle: string;
  gradient: string;
  icon: string;
  actionText: string;
  actionType: 'savings' | 'transfer' | 'cashback' | 'security' | 'analytics';
  content: {
    headline: string;
    details: string;
    highlightMetric: string;
    metricLabel: string;
    bullets: string[];
  };
}

export interface FastPayPayee {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  routingNumber?: string;
  accountNumber?: string;
  avatarColor: string;
  initials: string;
  preferredRail: FedRail;
  bankName?: string;
}

export interface CardDetails {
  id: string;
  type?: 'debit' | 'credit' | 'virtual';
  cardType?: 'debit' | 'credit' | 'virtual';
  name?: string;
  cardHolder?: string;
  number?: string;
  cardNumber?: string;
  expiry: string;
  cvv: string;
  isFrozen: boolean;
  onlineEnabled?: boolean;
  onlinePaymentsEnabled?: boolean;
  contactlessEnabled?: boolean;
  internationalEnabled?: boolean;
  atmEnabled?: boolean;
  atmWithdrawalsEnabled?: boolean;
  dailyLimitCents?: number;
  dailySpendingLimitCents?: number;
  monthlyLimitCents?: number;
  monthlySpendingLimitCents?: number;
  currentDailySpendCents?: number;
}
