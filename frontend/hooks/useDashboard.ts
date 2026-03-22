"use client";
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/lib/AuthContext';
import { getRecentTransactions, getAccountSummary, Transaction, Account } from '@/lib/api/accounts';
export type { Transaction, Account };

interface UseTransactionsResult {
    transactions: Transaction[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    refetching: boolean;
}

export function useTransactions(hours: number = 24, autoRefresh: boolean = true): UseTransactionsResult {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [refetching, setRefetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);

    const fetchTransactions = useCallback(async (isRefresh: boolean = false) => {
        if (!mountedRef.current) return;
        if (isRefresh) setRefetching(true); else setLoading(true);
        setError(null);

        try {
            const data = await getRecentTransactions(hours);
            if (mountedRef.current) setTransactions(data);
        } catch (err: any) {
            if (mountedRef.current) {
                setError(err.message || 'Failed to load transactions');
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
                setRefetching(false);
            }
        }
    }, [hours]);

    useEffect(() => {
        fetchTransactions(false);
        if (autoRefresh) {
            const interval = setInterval(() => fetchTransactions(true), 30000);
            return () => clearInterval(interval);
        }
    }, [fetchTransactions, autoRefresh]);

    useEffect(() => {
        mountedRef.current = true;
        return () => { mountedRef.current = false; };
    }, []);

    return { transactions, loading, error, refresh: () => fetchTransactions(true), refetching };
}

interface UseBalanceResult {
    balance: number | null;
    reservedBalance: number | null;
    accounts: Account[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    userId: number | null;
    refetching: boolean;
}

export function useBalance(autoRefresh: boolean = true): UseBalanceResult {
    const { user } = useAuth();
    const [balance, setBalance] = useState<number | null>(null);
    const [reservedBalance, setReservedBalance] = useState<number | null>(null);
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [loading, setLoading] = useState(true);
    const [refetching, setRefetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);

    const fetchBalance = useCallback(async (isRefresh: boolean = false) => {
        if (!mountedRef.current || !user) return;
        if (isRefresh) setRefetching(true); else setLoading(true);
        setError(null);

        try {
            const data = await getAccountSummary(user.id);
            if (mountedRef.current) {
                setBalance(data.balance);
                setReservedBalance(data.reserved_balance);
                setAccounts(data.accounts);
            }
        } catch (err: any) {
            if (mountedRef.current) {
                setError(err.message || 'Failed to load account summary');
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
                setRefetching(false);
            }
        }
    }, [user]);

    useEffect(() => {
        fetchBalance(false);
        if (autoRefresh) {
            const interval = setInterval(() => fetchBalance(true), 60000);
            return () => clearInterval(interval);
        }
    }, [fetchBalance, autoRefresh]);

    useEffect(() => {
        mountedRef.current = true;
        return () => { mountedRef.current = false; };
    }, []);

    return { balance, reservedBalance, accounts, loading, error, refresh: () => fetchBalance(true), userId: user ? user.id : null, refetching };
}
