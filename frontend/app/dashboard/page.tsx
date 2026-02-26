"use client";

import { useState, useEffect } from 'react';
import { motion } from "framer-motion";
import BalanceCard from "@/components/BalanceCard";
import TransactionList from "@/components/TransactionList";
import SpendingStats, { SpendingByCategory, QuickSummary } from "@/components/SpendingStats";
import BalanceHistoryChart from "@/components/BalanceHistoryChart";
import DashboardSkeleton from "@/components/DashboardSkeleton";
import { useTransactions, useBalance } from '@/hooks/useDashboard';
import { useAuth } from '@/lib/AuthContext';
import { RefreshCw, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
    const { token } = useAuth();
    const [userName, setUserName] = useState<string>('User');

    const { transactions, loading: transactionsLoading, error: transactionsError, refresh: refreshTransactions, refetching } = useTransactions(24, true);
    const { balance, loading: balanceLoading, refresh: refreshBalance, refetching: balanceRefetching } = useBalance(true);

    useEffect(() => {
        const fetchUser = async () => {
            if (typeof window === 'undefined') return;

            const authToken = token || localStorage.getItem('bank_token');
            if (!authToken) return;

            try {
                const userRes = await fetch('http://localhost:8000/auth/me', {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                if (userRes.ok) {
                    const user = await userRes.json();
                    setUserName(user.first_name);
                }
            } catch (err) {
                console.error('Failed to fetch user:', err);
            }
        };
        fetchUser();
    }, [token]);

    const handleRefresh = async () => {
        await Promise.all([refreshTransactions(), refreshBalance()]);
    };

    const isRefreshing = transactionsLoading || balanceLoading || refetching;

    if (transactionsLoading && balanceLoading) {
        return <DashboardSkeleton />;
    }

    return (
        <div className="space-y-12 pb-12">
            {/* Header section */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-white mb-2">
                        Good morning, <span className="text-white/40">{user?.first_name || 'User'}</span>
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
            </header>

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

            {/* Spending Statistics */}
            <SpendingStats transactions={transactions} period="Last 24 Hours" />

            {/* Main Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
                {/* Left Column: Balance & Quick Actions */}
                <div className="xl:col-span-5 space-y-6">
                    {balance !== null ? (
                        <BalanceCard
                            balance={balance}
                            growth={2.5}
                            accountNumber="5542 8890 1223 4567"
                        />
                    ) : (
                        <div className="glass-panel p-8 rounded-[2.5rem] animate-pulse">
                            <div className="h-32 bg-white/5 rounded-2xl" />
                        </div>
                    )}

                    <QuickSummary balance={balance} transactions={transactions} loading={balanceLoading} />
                </div>

                {/* Right Column: Analytics */}
                <div className="xl:col-span-7 grid grid-cols-1 gap-6">
                    <BalanceHistoryChart
                        history={[]}
                        loading={false}
                        error={null}
                    />

                    <SpendingByCategory transactions={transactions} limit={5} />
                </div>
            </div>

            {/* Transactions List */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
            >
                <TransactionList transactions={transactions} loading={transactionsLoading} />
            </motion.div>
        </div>
    );
}
