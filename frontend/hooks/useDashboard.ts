"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { Transaction } from '@/lib/types';
import { useAuth } from '@/lib/AuthContext';

interface UseTransactionsResult {
    transactions: Transaction[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    refetching: boolean;
}

export function useTransactions(hours: number = 24, autoRefresh: boolean = true): UseTransactionsResult {
    const { token } = useAuth();
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [refetching, setRefetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchTransactions = useCallback(async (isRefresh: boolean = false) => {
        if (!mountedRef.current) return;

        if (isRefresh) {
            setRefetching(true);
        } else {
            setLoading(true);
        }

        setError(null);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            const authToken = token || localStorage.getItem('bank_token');
            if (!authToken) {
                throw new Error('No authentication token found');
            }

            const response = await fetch(
                `http://localhost:8000/dashboard/recent-transactions?hours=${hours}`,
                {
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                    },
                    signal: controller.signal,
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (mountedRef.current) {
                setTransactions(data.transactions || []);
            }
        } catch (err: any) {
            if (err.name === 'AbortError') {
                return;
            }

            if (mountedRef.current) {
                console.error('Failed to fetch transactions:', err);
                setError(err.message || 'Failed to load transactions');
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
                setRefetching(false);
            }
        }
    }, [hours, token]);

    useEffect(() => {
        fetchTransactions(false);

        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchTransactions(true);
            }, 30000); // Refresh every 30 seconds

            return () => clearInterval(interval);
        }
    }, [fetchTransactions, autoRefresh]);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    return { transactions, loading, error, refresh: () => fetchTransactions(true), refetching };
}

export interface AccountData {
    id: number;
    name: string;
    balance: number;
    reserved_balance: number;
    is_main: boolean;
    routing_number?: string;
    masked_account_number?: string;
}

interface UseBalanceResult {
    balance: number | null;
    reservedBalance: number | null;
    accounts: AccountData[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    userId: number | null;
    refetching: boolean;
}

export function useBalance(autoRefresh: boolean = true): UseBalanceResult {
    const { token, user } = useAuth();
    const [balance, setBalance] = useState<number | null>(null);
    const [reservedBalance, setReservedBalance] = useState<number | null>(null);
    const [accounts, setAccounts] = useState<AccountData[]>([]);
    const [loading, setLoading] = useState(true);
    const [refetching, setRefetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchBalance = useCallback(async (isRefresh: boolean = false) => {
        if (!mountedRef.current) return;

        if (isRefresh) {
            setRefetching(true);
        } else {
            setLoading(true);
        }
        setError(null);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            const authToken = token || localStorage.getItem('bank_token');
            if (!authToken) {
                throw new Error('No authentication token found');
            }

            if (mountedRef.current && user) {
                const balanceResponse = await fetch(
                    `http://localhost:8000/accounts/${user.id}`,
                    {
                        headers: { 'Authorization': `Bearer ${authToken}` },
                        signal: controller.signal,
                    }
                );

                if (!balanceResponse.ok) {
                    throw new Error('Failed to fetch balance');
                }

                const balanceData = await balanceResponse.json();
                setBalance(balanceData.balance);
                setReservedBalance(balanceData.reserved_balance);
                setAccounts(balanceData.accounts || []);
            }
        } catch (err: any) {
            if (err.name === 'AbortError') {
                return;
            }

            if (mountedRef.current) {
                console.error('Failed to fetch balance:', err);
                setError(err.message || 'Failed to load balance');
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
                setRefetching(false);
            }
        }
    }, [token, user]);

    useEffect(() => {
        fetchBalance(false);

        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchBalance(true);
            }, 60000); // Refresh every minute

            return () => clearInterval(interval);
        }
    }, [fetchBalance, autoRefresh]);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    return { balance, reservedBalance, accounts, loading, error, refresh: () => fetchBalance(true), userId: user ? user.id : null, refetching };
}

interface UseBalanceHistoryResult {
    history: { date: string; balance: number; daily_change: number }[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export function useBalanceHistory(days: number = 30, autoRefresh: boolean = true): UseBalanceHistoryResult {
    const { token } = useAuth();
    const [history, setHistory] = useState<{ date: string; balance: number; daily_change: number }[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchHistory = useCallback(async () => {
        if (!mountedRef.current) return;

        setLoading(true);
        setError(null);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            const authToken = token || localStorage.getItem('bank_token');
            if (!authToken) {
                throw new Error('No authentication token found');
            }

            const response = await fetch(
                `http://localhost:8000/dashboard/balance-history?days=${days}`,
                {
                    headers: { 'Authorization': `Bearer ${authToken}` },
                    signal: controller.signal,
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (mountedRef.current) {
                setHistory(data.balance_history || []);
            }
        } catch (err: any) {
            if (err.name === 'AbortError') {
                return;
            }

            if (mountedRef.current) {
                console.error('Failed to fetch balance history:', err);
                setError(err.message || 'Failed to load balance history');
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
            }
        }
    }, [days, token]);

    useEffect(() => {
        fetchHistory();

        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchHistory();
            }, 300000); // Refresh every 5 minutes

            return () => clearInterval(interval);
        }
    }, [fetchHistory, autoRefresh]);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    return { history, loading, error, refresh: fetchHistory };
}
