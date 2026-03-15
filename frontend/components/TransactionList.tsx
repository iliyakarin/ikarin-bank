"use client";
import React from 'react';
import { Transaction } from '@/lib/types';
import { getTransactionStatus, getStatusLabel, formatCurrency } from '@/lib/transactionUtils';
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON } from '@/lib/constants';
import { motion } from 'framer-motion';
import { Check, Clock, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';

function TransactionItem({ transaction, index }: { transaction: Transaction, index: number }) {
    const { settings } = useAuth();
    const status = getTransactionStatus(transaction.status);
    const statusLabel = getStatusLabel(status);
    const icon = CATEGORY_ICONS[transaction.category] || DEFAULT_CATEGORY_ICON;

    // Determine if this is a deduction (expense or transfer) or income
    const isIncome = transaction.amount > 0;
    const isTransfer = transaction.transaction_type === 'transfer' || transaction.category === 'Transfer';

    // Apply colors and prefixes
    const amountColor = isIncome ? 'text-emerald-400' : 'text-rose-400';



    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className="flex items-center justify-between p-5 hover:bg-white/5 transition-colors cursor-pointer group rounded-2xl"
        >
            <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <div>
                    <p className="font-bold text-white text-lg">{transaction.merchant}</p>
                    <div className="flex items-center gap-3">
                        <p className="text-xs text-white/40 font-medium">{transaction.category}</p>

                        {status === 'pending' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                                <Clock className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {status === 'cleared' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded-full border border-emerald-500/30">
                                <Check className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {status === 'unknown' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-white/60 bg-white/10 px-2 py-0.5 rounded-full border border-white/20">
                                <AlertCircle className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {status === 'failed' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-red-300 bg-red-500/20 px-2 py-0.5 rounded-full border border-red-500/30">
                                <AlertCircle className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {/* Transfer indicator */}
                        {isTransfer && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-blue-300 bg-blue-500/20 px-2 py-0.5 rounded-full border border-blue-500/30">
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h8m0 0l-8-8v8m0 0l8-8" />
                                </svg>
                                P2P
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <div className="text-right flex flex-col justify-end items-end gap-1">
                <p className={`font-bold text-lg ${amountColor}`}>
                    {formatCurrency(transaction.amount)}
                </p>
                <p className="text-xs text-white/40 font-medium">
                    {new Date(transaction.created_at + 'Z').toLocaleDateString(settings.useEUDates ? 'en-GB' : 'en-US', { month: 'short', day: 'numeric' })}
                </p>
                {status === 'failed' && (
                    <Link
                        href={`/client`}
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1 flex items-center gap-1 text-[10px] uppercase font-bold text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded shadow-sm transition-colors"
                    >
                        Top Up & Retry
                    </Link>
                )}
            </div>
        </motion.div>
    );
}

export default function TransactionList({ transactions, loading }: { transactions: Transaction[], loading: boolean }) {
    return (
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-[2.5rem] shadow-sm overflow-hidden p-2 mt-8">
            <div className="p-6 flex justify-between items-center">
                <h3 className="font-bold text-xl text-white">Recent Transactions</h3>
                <Link href="/client/transactions" className="text-white text-sm font-bold hover:underline underline-offset-4">View All</Link>
            </div>
            <div className="space-y-1">
                {loading ? (
                    <div className="p-8 text-center text-white/50 animate-pulse font-medium">Loading transactions...</div>
                ) : transactions.length > 0 ? (
                    transactions.map((tx, i) => <TransactionItem key={tx.id} transaction={tx} index={i} />)
                ) : (
                    <div className="p-12 text-center">
                        <p className="text-white/40 font-medium">No activity in this account</p>
                    </div>
                )}
            </div>
        </div>
    );
}
