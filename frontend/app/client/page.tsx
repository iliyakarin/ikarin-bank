"use client";

import { useState, useEffect } from 'react';
import { motion } from "framer-motion";
import { useAuth } from '@/lib/AuthContext';
import { useTransactions, useBalance } from '@/hooks/useDashboard';
import SpendingStats, { SpendingByCategory } from '@/components/SpendingStats';
import TransactionList from '@/components/TransactionList';
import BalanceHistoryChart from '@/components/BalanceHistoryChart';
import { TrendingUp, RefreshCw, ShieldCheck } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardPage() {
    const { user, token } = useAuth();
    const [userName, setUserName] = useState<string>('User');
    const [dayFilter, setDayFilter] = useState(30);

    const { transactions, loading: transactionsLoading, error: transactionsError, refresh: refreshTransactions, refetching } = useTransactions(24, true);
    const { balance, loading: balanceLoading, refresh: refreshBalance, refetching: balanceRefetching } = useBalance(true);

    useEffect(() => {
        if (user) {
            setUserName(user.first_name);
        }
    }, [user]);

    const handleRefresh = async () => {
        await Promise.all([refreshTransactions(), refreshBalance()]);
    };

    const isRefreshing = transactionsLoading || balanceLoading || refetching;

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    };

    const stats = {
        totalIncome: transactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0),
        totalExpenses: transactions.filter(t => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0),
        transactionCount: transactions.length,
    };

    const balanceHistoryData = transactions
        .map(t => ({
            date: new Date(t.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            balance: t.amount,
        }))
        .reverse();

    const growthPercent = 2.5;

    return (
        <div className="space-y-12 pb-12">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">
                        Good morning, <span className="text-white/40">{userName}</span>
                    </h1>
                    <p className="text-white/40 font-medium">Your financial health is at its peak this month.</p>
                </motion.div>

                <div className="flex items-center gap-3">
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleRefresh}
                        className="p-3 bg-white/5 rounded-2xl border border-white/10 text-white hover:bg-white/10 transition-all disabled:opacity-50"
                        title="Refresh data"
                        aria-label="Refresh data"
                        disabled={isRefreshing}
                    >
                        <motion.div
                            animate={isRefreshing ? { rotate: 360 } : { rotate: 0 }}
                            transition={isRefreshing ? { repeat: Infinity, duration: 1, ease: "linear" } : { duration: 0.5 }}
                        >
                            <RefreshCw size={20} />
                        </motion.div>
                    </motion.button>
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-3 p-2 bg-white/5 rounded-2xl border border-white/10"
                    >
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                            <ShieldCheck size={20} />
                        </div>
                        <div className="pr-4">
                            <p className="text-[10px] uppercase font-black text-white/30 tracking-widest">Security Status</p>
                            <p className="text-sm font-bold text-white">Advanced Protection</p>
                        </div>
                    </motion.div>
                </div>
            </div>

            {/* Error Display */}
            {transactionsError && (
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-rose-500/20 border border-rose-500/30 text-rose-300 p-4 rounded-2xl"
                >
                    <p className="font-bold mb-1">Error loading data</p>
                    <p className="text-sm">{transactionsError}</p>
                </motion.div>
            )}

            {/* Hero Balance Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-purple-500/40 via-indigo-500/30 to-purple-600/40 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl"
            >
                <div className="flex justify-between items-start">
                    <div className="space-y-4">
                        <p className="text-white/60 text-sm font-medium">Your Current Balance</p>
                        <h1 className="text-5xl md:text-6xl font-black text-white">
                            {balanceLoading ? (
                                <div className="h-20 w-64 bg-white/10 rounded-2xl animate-pulse" />
                            ) : (
                                formatCurrency(balance || 0)
                            )}
                        </h1>
                        {!balanceLoading && (
                            <div className="flex items-center gap-2 text-emerald-400">
                                <TrendingUp size={20} />
                                <span className="font-semibold">+{growthPercent}% from last month</span>
                            </div>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Spending Statistics */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            >
                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 space-y-4 hover:scale-105 transition-transform duration-300">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                        <div className="text-2xl">↓</div>
                    </div>
                    <div>
                        <p className="text-white/40 text-sm font-medium mb-1">Total Income</p>
                        <p className="text-2xl lg:text-3xl font-bold text-emerald-400">
                            {formatCurrency(stats.totalIncome)}
                        </p>
                        <p className="text-white/30 text-xs mt-1">Last 24 Hours</p>
                    </div>
                </div>

                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 space-y-4 hover:scale-105 transition-transform duration-300">
                    <div className="w-12 h-12 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center">
                        <div className="text-2xl">↑</div>
                    </div>
                    <div>
                        <p className="text-white/40 text-sm font-medium mb-1">Total Expenses</p>
                        <p className="text-2xl lg:text-3xl font-bold text-rose-400">
                            {formatCurrency(stats.totalExpenses)}
                        </p>
                        <p className="text-white/30 text-xs mt-1">Last 24 Hours</p>
                    </div>
                </div>

                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 space-y-4 hover:scale-105 transition-transform duration-300">
                    <div className="w-12 h-12 rounded-2xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                        <div className="text-2xl">⚖️</div>
                    </div>
                    <div>
                        <p className="text-white/40 text-sm font-medium mb-1">Net Flow</p>
                        <p className={`text-2xl lg:text-3xl font-bold ${stats.totalIncome >= stats.totalExpenses ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {formatCurrency(stats.totalIncome - stats.totalExpenses)}
                        </p>
                        <p className="text-white/30 text-xs mt-1">Last 24 Hours</p>
                    </div>
                </div>

                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 space-y-4 hover:scale-105 transition-transform duration-300">
                    <div className="w-12 h-12 rounded-2xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
                        <div className="text-2xl">📊</div>
                    </div>
                    <div>
                        <p className="text-white/40 text-sm font-medium mb-1">Transactions</p>
                        <p className="text-2xl lg:text-3xl font-bold text-white">
                            {stats.transactionCount}
                        </p>
                        <p className="text-white/30 text-xs mt-1">Last 24 Hours</p>
                    </div>
                </div>
            </motion.div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {/* Balance Trend Chart */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="xl:col-span-2 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8"
                >
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-2xl font-bold text-white">Balance Trend</h2>
                            <div className="flex gap-2">
                                {[7, 30, 60, 90].map((days) => (
                                    <button
                                        key={days}
                                        onClick={() => setDayFilter(days)}
                                        className={`px-4 py-2 rounded-lg font-semibold transition-all ${dayFilter === days
                                            ? 'bg-purple-500 text-white'
                                            : 'bg-white/10 text-white/60 hover:bg-white/20'
                                            }`}
                                    >
                                        {days}d
                                    </button>
                                ))}
                            </div>
                        </div>

                        {balanceHistoryData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={balanceHistoryData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="date" stroke="rgba(255,255,255,0.6)" />
                                    <YAxis stroke="rgba(255,255,255,0.6)" />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: 'rgba(0,0,0,0.8)',
                                            border: '1px solid rgba(255,255,255,0.2)',
                                            borderRadius: '8px',
                                            color: '#fff'
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="balance"
                                        stroke="#a855f7"
                                        strokeWidth={2}
                                        dot={{ fill: '#a855f7', r: 4 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-64 flex items-center justify-center text-white/40">
                                No balance history available
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* Spending by Category */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <SpendingByCategory transactions={transactions} limit={5} />
                </motion.div>
            </div>

            {/* Transactions List */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
            >
                <TransactionList transactions={transactions} loading={transactionsLoading} />
            </motion.div>
        </div>
    );
}
