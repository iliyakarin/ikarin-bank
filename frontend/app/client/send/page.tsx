"use client";
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { Send, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';

export default function SendMoneyPage() {
    const { token } = useAuth();
    const [recipient, setRecipient] = useState('');
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [txId, setTxId] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccess(false);

        if (!recipient.trim() || !amount) {
            setError('Please fill in all fields');
            setLoading(false);
            return;
        }

        if (parseFloat(amount) <= 0) {
            setError('Amount must be greater than 0');
            setLoading(false);
            return;
        }

        try {
            const res = await fetch('http://localhost:8000/p2p-transfer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    recipient_email: recipient,
                    amount: parseFloat(amount)
                })
            });

            if (res.ok) {
                const data = await res.json();
                setSuccess(true);
                setTxId(data.transaction_id);
                setRecipient('');
                setAmount('');
                setTimeout(() => setSuccess(false), 5000);
            } else {
                const data = await res.json();
                setError(data.detail || 'Transfer failed');
            }
        } catch (err) {
            setError('Connection error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-8 pb-12 max-w-2xl">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
            >
                <h1 className="text-4xl font-black text-white flex items-center gap-3">
                    <Send className="text-purple-400" size={32} />
                    Send Money
                </h1>
                <p className="text-white/60">Transfer funds to any user instantly</p>
            </motion.div>

            {/* Success Message */}
            {success && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-emerald-500/20 border border-emerald-500/50 rounded-xl p-4 flex items-center gap-3"
                >
                    <CheckCircle className="text-emerald-400" size={20} />
                    <div>
                        <p className="text-emerald-200 font-semibold">Transfer successful!</p>
                        <p className="text-emerald-200/70 text-sm">Transaction ID: {txId}</p>
                    </div>
                </motion.div>
            )}

            {/* Error Message */}
            {error && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 flex items-center gap-3"
                >
                    <AlertCircle className="text-red-400" size={20} />
                    <p className="text-red-200 font-semibold">{error}</p>
                </motion.div>
            )}

            {/* Form Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8"
            >
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Recipient Email */}
                    <div className="space-y-3">
                        <label className="block text-white font-semibold">Recipient Email</label>
                        <input
                            type="email"
                            value={recipient}
                            onChange={(e) => setRecipient(e.target.value)}
                            placeholder="user@example.com"
                            className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400 transition-all"
                            required
                        />
                        <p className="text-white/50 text-sm">The email address of the recipient account</p>
                    </div>

                    {/* Amount */}
                    <div className="space-y-3">
                        <label className="block text-white font-semibold">Amount (USD)</label>
                        <div className="relative">
                            <span className="absolute left-4 top-3 text-white font-semibold text-lg">$</span>
                            <input
                                type="number"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="0.00"
                                step="0.01"
                                className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400 transition-all"
                                required
                            />
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                Processing...
                            </>
                        ) : (
                            <>
                                <Send size={20} />
                                Send Money
                                <ArrowRight size={20} />
                            </>
                        )}
                    </button>
                </form>

                {/* Info Box */}
                <div className="mt-8 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl space-y-2">
                    <p className="text-purple-200 text-sm font-semibold">💡 Pro Tip</p>
                    <p className="text-purple-200/70 text-sm">
                        Transfers are processed instantly. The recipient will see the funds immediately in their account.
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
