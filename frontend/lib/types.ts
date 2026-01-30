export type TransactionStatus = 'pending' | 'sent_to_kafka' | 'cleared';
export type TransactionType = 'income' | 'expense' | 'transfer';

export interface Transaction {
    id: string;
    account_id: number;
    amount: number;
    category: string;
    merchant: string;
    sender_email?: string;
    recipient_email?: string;
    status: TransactionStatus;
    transaction_type: TransactionType;
    created_at: string; // ISO string
}

export interface AccountSummary {
    total_balance: number;
    monthly_trend: { date: string; value: number }[];
}

export interface NavLink {
    name: string;
    href: string;
    icon: string; // Emoji or Icon name
}
