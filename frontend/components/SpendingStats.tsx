"use client";

import { Transaction } from '@/lib/types';
import { useMemo } from 'react';
import { CATEGORY_COLORS, DEFAULT_CATEGORY_COLOR } from '@/lib/constants';
import { ArrowUpRight, ArrowDownLeft, TrendingUp, TrendingDown, Wallet } from 'lucide-react';

interface SpendingStatsProps {
    transactions: Transaction[];
    period: string;
}

export default function SpendingStats({ transactions, period }: SpendingStatsProps) {
    const stats = useMemo(() => {
        const totalIncome = transactions
            .filter(t => t.transaction_type === 'income' && t.category !== 'Internal Transfer')
            .reduce((sum, t) => sum + t.amount, 0);

        const totalExpenses = transactions
            .filter(t => (t.transaction_type === 'expense' || t.transaction_type === 'transfer') && t.category !== 'Internal Transfer' && t.amount < 0)
            .reduce((sum, t) => sum + Math.abs(t.amount), 0);

        const netFlow = totalIncome - totalExpenses;

        const spendingByCategory = transactions
            .filter(t => (t.transaction_type === 'expense' || t.transaction_type === 'transfer') && t.category !== 'Internal Transfer' && t.amount < 0)
            .reduce((acc, t) => {
                const category = t.transaction_type === 'transfer' ? 'Transfers' : t.category;
                const amount = Math.abs(t.amount);
                acc[category] = (acc[category] || 0) + amount;
                return acc;
            }, {} as Record<string, number>);

        const topCategories = Object.entries(spendingByCategory)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3);

        const pendingCount = transactions.filter(t => t.status === 'pending').length;
        const clearedCount = transactions.filter(t => t.status === 'cleared').length;

        return {
            totalIncome,
            totalExpenses,
            netFlow,
            spendingByCategory,
            topCategories,
            pendingCount,
            clearedCount,
            averageTransaction: transactions.length > 0 ? totalExpenses / transactions.length : 0,
        };
    }, [transactions]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Income */}
            <div className="glass-panel p-6 rounded-[2rem] space-y-4 hover:scale-105 transition-transform duration-300">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <ArrowDownLeft size={24} />
                </div>
                <div>
                    <p className="text-white/40 text-sm font-medium mb-1">Total Income</p>
                    <p className="text-2xl lg:text-3xl font-bold text-emerald-400">
                        {formatCurrency(stats.totalIncome)}
                    </p>
                    <p className="text-white/30 text-xs mt-1">{period}</p>
                </div>
            </div>

            {/* Total Expenses */}
            <div className="glass-panel p-6 rounded-[2rem] space-y-4 hover:scale-105 transition-transform duration-300">
                <div className="w-12 h-12 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center">
                    <ArrowUpRight size={24} />
                </div>
                <div>
                    <p className="text-white/40 text-sm font-medium mb-1">Total Expenses</p>
                    <p className="text-2xl lg:text-3xl font-bold text-rose-400">
                        {formatCurrency(stats.totalExpenses)}
                    </p>
                    <p className="text-white/30 text-xs mt-1">{period}</p>
                </div>
            </div>

            {/* Net Flow */}
            <div className="glass-panel p-6 rounded-[2rem] space-y-4 hover:scale-105 transition-transform duration-300">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${stats.netFlow >= 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                    {stats.netFlow >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
                </div>
                <div>
                    <p className="text-white/40 text-sm font-medium mb-1">Net Flow</p>
                    <p className={`text-2xl lg:text-3xl font-bold ${stats.netFlow >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                        {stats.netFlow >= 0 ? '+' : ''}{formatCurrency(stats.netFlow)}
                    </p>
                    <p className="text-white/30 text-xs mt-1">{period}</p>
                </div>
            </div>

            {/* Transaction Summary */}
            <div className="glass-panel p-6 rounded-[2rem] space-y-4 hover:scale-105 transition-transform duration-300">
                <div className="w-12 h-12 rounded-2xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
                    <Wallet size={24} />
                </div>
                <div>
                    <p className="text-white/40 text-sm font-medium mb-1">Transactions</p>
                    <p className="text-2xl lg:text-3xl font-bold text-white">
                        {transactions.length}
                    </p>
                    <p className="text-white/30 text-xs mt-1">
                        {stats.pendingCount} pending • {stats.clearedCount} cleared
                    </p>
                </div>
            </div>
        </div>
    );
}

interface SpendingByCategoryProps {
    transactions: Transaction[];
    limit?: number;
}

export function SpendingByCategory({ transactions, limit = 5 }: SpendingByCategoryProps) {
    const spendingData = useMemo(() => {
        const spendingByCategory = transactions
            .filter(t => (t.transaction_type === 'expense' || t.transaction_type === 'transfer') && t.category !== 'Internal Transfer' && t.amount < 0)
            .reduce((acc, t) => {
                const category = t.transaction_type === 'transfer' ? 'Transfers' : t.category;
                const amount = Math.abs(t.amount);
                acc[category] = (acc[category] || 0) + amount;
                return acc;
            }, {} as Record<string, number>);

        const totalSpending = Object.values(spendingByCategory).reduce((a, b) => a + b, 0);

        return Object.entries(spendingByCategory)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([category, amount]) => ({
                category,
                amount,
                percentage: totalSpending > 0 ? (amount / totalSpending) * 100 : 0,
            }));
    }, [transactions, limit]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    if (spendingData.length === 0) {
        return (
            <div className="glass-panel p-8 rounded-[2rem] text-center">
                <p className="text-white/40">No spending data available</p>
            </div>
        );
    }

    return (
        <div className="glass-panel p-8 rounded-[2rem] space-y-6">
            <h3 className="text-xl font-bold text-white">Spending by Category</h3>
            <div className="space-y-4">
                {spendingData.map((item) => {
                    const colorClass = CATEGORY_COLORS[item.category] || DEFAULT_CATEGORY_COLOR;
                    return (
                        <div key={item.category} className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-white font-medium">{item.category}</span>
                                <span className="text-white/60">{formatCurrency(item.amount)}</span>
                            </div>
                            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${colorClass} rounded-full transition-all duration-500`}
                                    style={{ width: `${item.percentage}%` }}
                                />
                            </div>
                            <div className="flex justify-between text-xs text-white/30">
                                <span>{item.percentage.toFixed(1)}% of spending</span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

interface QuickSummaryProps {
    balance: number | null;
    transactions: Transaction[];
    loading: boolean;
}

export function QuickSummary({ balance, transactions, loading }: QuickSummaryProps) {
    const recentSpending = useMemo(() => {
        const recent = transactions
            .filter(t => (t.transaction_type === 'expense' || t.transaction_type === 'transfer') && t.category !== 'Internal Transfer' && t.amount < 0)
            .slice(0, 5)
            .reduce((sum, t) => sum + Math.abs(t.amount), 0);
        return recent;
    }, [transactions]);

    const formatCurrency = (amount: number | null) => {
        if (amount === null) return '--';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    };

    return (
        <div className="glass-panel p-8 rounded-[2rem] space-y-6">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold text-white">Quick Summary</h3>
                {loading && (
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                )}
            </div>

            <div className="space-y-4">
                <div className="flex justify-between items-center py-3 border-b border-white/10">
                    <span className="text-white/40">Current Balance</span>
                    <span className="text-2xl font-bold text-white">{formatCurrency(balance)}</span>
                </div>

                <div className="flex justify-between items-center py-3 border-b border-white/10">
                    <span className="text-white/40">Recent Transactions</span>
                    <span className="text-white font-medium">{transactions.length}</span>
                </div>

                <div className="flex justify-between items-center py-3">
                    <span className="text-white/40">Recent Spending</span>
                    <span className="text-rose-400 font-medium">{formatCurrency(recentSpending)}</span>
                </div>
            </div>
        </div>
    );
}
