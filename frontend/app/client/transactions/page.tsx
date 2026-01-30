'use client';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { Filter } from 'lucide-react';

interface Transaction {
    id: string;
    sender_email?: string;
    recipient_email?: string;
    amount: number;
    category: string;
    merchant?: string;
    timestamp: string;
    status?: string;
    transaction_type?: 'income' | 'expense' | 'transfer';
}

export default function TransactionsPage() {
    const { token } = useAuth();
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [dayRange, setDayRange] = useState(1); // default to last 24 hours
    const [customDays, setCustomDays] = useState('');
    const [txType, setTxType] = useState<'all' | 'incoming' | 'outgoing'>('all');
    const [minAmount, setMinAmount] = useState('');
    const [maxAmount, setMaxAmount] = useState('');
    const [sortAsc, setSortAsc] = useState(false); // default DESC

    useEffect(() => {
        const fetchTransactions = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                params.set('days', dayRange.toString());
                if (txType !== 'all') params.set('tx_type', txType);
                if (minAmount) params.set('min_amount', minAmount);
                if (maxAmount) params.set('max_amount', maxAmount);
                params.set('sort', sortAsc ? 'asc' : 'desc');

                const res = await fetch(`http://localhost:8000/transactions?${params.toString()}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    setTransactions(data.transactions || []);
                } else {
                    console.error('Failed to load transactions', await res.text());
                }
            } catch (error) {
                console.error('Error fetching transactions:', error);
            } finally {
                setLoading(false);
            }
        };

        if (token) fetchTransactions();
    }, [token, dayRange, txType, minAmount, maxAmount, sortAsc]);

    // Preset buttons handler
    const applyPreset = (days: number) => {
        setCustomDays('');
        setDayRange(days);
    };

    const applyCustomDays = () => {
        const parsed = parseInt(customDays || '0', 10);
        if (!isNaN(parsed) && parsed > 0) {
            setDayRange(parsed);
        }
    };

    const stats = {
        total: transactions.length,
        sent: transactions.filter(t => t.transaction_type === 'expense' || t.transaction_type === 'transfer').reduce((sum, t) => sum + t.amount, 0),
        received: transactions.filter(t => t.transaction_type === 'income').reduce((sum, t) => sum + t.amount, 0),
    };

    return (
        <div className="space-y-8 pb-12">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
            >
                <h1 className="text-4xl font-black text-white flex items-center gap-3">
                    <Filter className="text-purple-400" size={32} />
                    All Transactions
                </h1>
                <p className="text-white/60">View and filter your complete transaction history</p>
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6"
            >
                <h2 className="text-xl font-bold text-white mb-4">Filters</h2>

                <div className="flex flex-wrap items-center gap-3 mb-4">
                    <button onClick={() => applyPreset(1)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">24h</button>
                    <button onClick={() => applyPreset(7)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">7d</button>
                    <button onClick={() => applyPreset(30)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">30d</button>
                    <button onClick={() => applyPreset(60)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">60d</button>
                    <button onClick={() => applyPreset(90)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">90d</button>

                    <div className="ml-4 flex items-center gap-2">
                        <input
                            type="number"
                            placeholder="Custom days"
                            value={customDays}
                            onChange={(e) => setCustomDays(e.target.value)}
                            className="w-28 bg-white/10 border border-white/20 rounded-lg px-2 py-1 text-white placeholder-white/40"
                        />
                        <button onClick={applyCustomDays} className="px-3 py-1 rounded-lg bg-white/5 text-white/80 hover:bg-purple-600/20">Apply</button>
                    </div>

                    <div className="ml-auto flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <label className="text-white/70 text-sm">Type</label>
                            <select value={txType} onChange={(e) => setTxType(e.target.value as any)} className="bg-white/10 border border-white/20 rounded-lg px-2 py-1 text-white">
                                <option value="all">All</option>
                                <option value="incoming">Incoming</option>
                                <option value="outgoing">Outgoing</option>
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <label className="text-white/70 text-sm">Sort</label>
                            <button onClick={() => setSortAsc(!sortAsc)} className="px-3 py-1 rounded-lg bg-white/5 text-white/80">
                                {sortAsc ? 'Asc' : 'Desc'}
                            </button>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-white/70 text-sm font-semibold">Min Amount</label>
                        <input
                            type="number"
                            placeholder="$0"
                            value={minAmount}
                            onChange={(e) => setMinAmount(e.target.value)}
                            className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white placeholder-white/40 focus:outline-none focus:border-purple-400 transition-all"
                        />
                    </div>

                    <div>
                        <label className="block text-white/70 text-sm font-semibold">Max Amount</label>
                        <input
                            type="number"
                            placeholder="$∞"
                            value={maxAmount}
                            onChange={(e) => setMaxAmount(e.target.value)}
                            className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white placeholder-white/40 focus:outline-none focus:border-purple-400 transition-all"
                        />
                    </div>

                    <div className="flex items-end">
                        <button onClick={() => { setMinAmount(''); setMaxAmount(''); setTxType('all'); setDayRange(1); setSortAsc(false); }} className="px-4 py-2 rounded-lg bg-red-600/10 text-red-300">Reset</button>
                    </div>
                </div>
            </motion.div>

            {/* Transactions Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl overflow-hidden"
            >
                {loading ? (
                    <div className="p-12 text-center text-white/60">Loading transactions...</div>
                ) : transactions.length === 0 ? (
                    <div className="p-12 text-center text-white/60">No transactions found</div>
                ) : (
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="border-b border-white/10 bg-white/5">
                                    <tr>
                                        <th className="px-6 py-4 text-left text-white/70 font-semibold text-sm">Merchant</th>
                                        <th className="px-6 py-4 text-left text-white/70 font-semibold text-sm">Category</th>
                                        <th className="px-6 py-4 text-left text-white/70 font-semibold text-sm">From</th>
                                        <th className="px-6 py-4 text-left text-white/70 font-semibold text-sm">To</th>
                                        <th className="px-6 py-4 text-right text-white/70 font-semibold text-sm">Amount</th>
                                        <th className="px-6 py-4 text-right text-white/70 font-semibold text-sm">Date</th>
                                        <th className="px-6 py-4 text-right text-white/70 font-semibold text-sm">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {transactions.map((tx) => (
                                        <tr key={tx.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                            <td className="px-6 py-4 text-white font-medium">{tx.merchant || '—'}</td>
                                            <td className="px-6 py-4 text-white/70 text-sm">{tx.category}</td>
                                            <td className="px-6 py-4 text-white/70 text-sm">{tx.sender_email || '—'}</td>
                                            <td className="px-6 py-4 text-white/70 text-sm">{tx.recipient_email || '—'}</td>
                                            <td className={`px-6 py-4 text-right font-mono font-semibold ${
                                                tx.transaction_type === 'income' ? 'text-emerald-400' : 'text-white'
                                            }`}>
                                                {tx.transaction_type === 'income' ? '+' : '-'} ${Math.abs(tx.amount).toFixed(2)}
                                            </td>
                                            <td className="px-6 py-4 text-white/60 text-sm text-right">{new Date(tx.timestamp).toLocaleString()}</td>
                                            <td className="px-6 py-4 text-right text-white/70">{tx.status || 'Cleared'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Stats Footer */}
                        <div className="border-t border-white/10 bg-white/5 px-6 py-6 grid grid-cols-3 gap-8">
                            <div>
                                <p className="text-white/60 text-sm mb-2">Total Transactions</p>
                                <p className="text-white text-2xl font-bold">{stats.total}</p>
                            </div>
                            <div>
                                <p className="text-white/60 text-sm mb-2">Total Sent</p>
                                <p className="text-white text-2xl font-bold">${stats.sent.toFixed(2)}</p>
                            </div>
                            <div>
                                <p className="text-white/60 text-sm mb-2">Total Received</p>
                                <p className="text-emerald-400 text-2xl font-bold">${stats.received.toFixed(2)}</p>
                            </div>
                        </div>
                    </>
                )}
            </motion.div>
        </div>
    );
}
