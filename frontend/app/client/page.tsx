"use client";
import { useState, useEffect } from 'react';
import { motion } from "framer-motion";
import { useAuth } from '@/lib/AuthContext';
import { TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardPage() {
    const { user, token } = useAuth();
    const [balance, setBalance] = useState<number>(0);
    const [recentTx, setRecentTx] = useState<any[]>([]);
    const [balanceHistory, setBalanceHistory] = useState<any[]>([]);
    const [dayFilter, setDayFilter] = useState(30);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;

        const fetchData = async () => {
            try {
                setLoading(true);
                // Fetch account balance
                const userRes = await fetch('http://localhost:8000/auth/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (userRes.ok) {
                    const userData = await userRes.json();
                    // Fetch account balance
                    const accountRes = await fetch(`http://localhost:8000/accounts/${userData.id}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (accountRes.ok) {
                        const accountData = await accountRes.json();
                        setBalance(accountData.balance);
                    }
                }

                // Fetch recent transactions
                const txRes = await fetch(`http://localhost:8000/dashboard/recent-transactions?hours=24`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (txRes.ok) {
                    const txData = await txRes.json();
                    setRecentTx(txData.transactions || []);
                }

                // Fetch balance history
                const histRes = await fetch(`http://localhost:8000/dashboard/balance-history?days=${dayFilter}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (histRes.ok) {
                    const histData = await histRes.json();
                    setBalanceHistory(histData.balance_history || []);
                }
            } catch (err) {
                console.error('Failed to fetch dashboard data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [token, dayFilter]);

    if (loading) {
        return (
            <div className="space-y-8">
                <div className="animate-pulse space-y-4">
                    <div className="h-32 bg-white/10 rounded-2xl"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-12 pb-12">
            {/* Hero Balance Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-purple-500/40 via-indigo-500/30 to-purple-600/40 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl"
            >
                <div className="space-y-4">
                    <p className="text-white/60 text-sm font-medium">Your Current Balance</p>
                    <h1 className="text-5xl md:text-6xl font-black text-white">
                        ${balance.toFixed(2)}
                    </h1>
                    <div className="flex items-center gap-2 text-emerald-400">
                        <TrendingUp size={20} />
                        <span className="font-semibold">+2.5% from last month</span>
                    </div>
                </div>
            </motion.div>

            {/* Trend Chart */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8"
            >
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-bold text-white">Balance Trend</h2>
                        <div className="flex gap-2">
                            {[7, 30, 60, 90].map((days) => (
                                <button
                                    key={days}
                                    onClick={() => setDayFilter(days)}
                                    className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                                        dayFilter === days
                                            ? 'bg-purple-500 text-white'
                                            : 'bg-white/10 text-white/60 hover:bg-white/20'
                                    }`}
                                >
                                    {days}d
                                </button>
                            ))}
                        </div>
                    </div>

                    {balanceHistory.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={balanceHistory}>
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

            {/* Recent Activity */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8"
            >
                <h2 className="text-2xl font-bold text-white mb-6">Recent Activity (Last 24h)</h2>
                <div className="space-y-4">
                    {recentTx.length > 0 ? (
                        recentTx.map((tx, i) => {
                            const isIncome = tx.transaction_type === 'income';
                            const amountColor = isIncome ? 'text-emerald-400' : 'text-red-400';
                            const amountPrefix = isIncome ? '+' : '-';
                            return (
                                <div
                                    key={i}
                                    className="flex items-center justify-between p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-all"
                                >
                                    <div>
                                        <p className="text-white font-semibold">{tx.merchant}</p>
                                        <p className="text-white/60 text-sm">{tx.category}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className={`font-bold ${amountColor}`}>
                                            {amountPrefix}${Math.abs(tx.amount).toFixed(2)}
                                        </p>
                                        <p className="text-white/60 text-xs">{new Date(tx.created_at).toLocaleDateString()}</p>
                                    </div>
                                </div>
                            );
                        })
                    ) : (
                        <div className="text-center py-8 text-white/60">
                            No transactions in the last 24 hours
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
}
