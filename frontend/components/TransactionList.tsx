"use client";
import React from 'react';
import { Transaction } from '@/lib/types';
import { getTransactionStatus, getStatusLabel } from '@/lib/transactionUtils';
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON } from '@/lib/constants';
import { motion } from 'framer-motion';
import { Check, Clock, AlertCircle } from 'lucide-react';

function TransactionItem({ transaction, index }: { transaction: Transaction, index: number }) {
    const status = getTransactionStatus(transaction.status);
    const statusLabel = getStatusLabel(status);
    const icon = CATEGORY_ICONS[transaction.category] || DEFAULT_CATEGORY_ICON;

    // Determine if this is a deduction (expense or transfer) or income
    const isIncome = transaction.amount > 0;
    const isTransfer = transaction.transaction_type === 'transfer' || transaction.category === 'Transfer';

    // Apply colors and prefixes
    const amountColor = isIncome ? 'text-emerald-600' : 'text-red-500';
    const amountPrefix = isIncome ? '+' : '-';



    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className="flex items-center justify-between p-5 hover:bg-gray-50 transition-colors cursor-pointer group rounded-2xl"
        >
            <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <div>
                    <p className="font-bold text-gray-900 text-lg">{transaction.merchant}</p>
                    <div className="flex items-center gap-3">
                        <p className="text-xs text-gray-400 font-medium">{transaction.category}</p>

                        {status === 'pending' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">
                                <Clock className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {status === 'cleared' && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                                <Check className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {status === 'unknown' && (
                             <span className="flex items-center gap-1 text-[11px] font-bold text-gray-600 bg-gray-50 px-2 py-0.5 rounded-full border border-gray-100">
                                <AlertCircle className="w-3 h-3" />
                                {statusLabel}
                            </span>
                        )}

                        {/* Transfer indicator */}
                        {isTransfer && (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h8m0 0l-8-8v8m0 0l8-8" />
                                </svg>
                                P2P
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <div className="text-right">
                <p className={`font-bold text-lg ${amountColor}`}>
                    {amountPrefix}${Math.abs(transaction.amount).toFixed(2)}
                </p>
                <p className="text-xs text-gray-400 font-medium">
                    {new Date(transaction.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </p>
            </div>
        </motion.div>
    );
}

export default function TransactionList({ transactions, loading }: { transactions: Transaction[], loading: boolean }) {
    return (
        <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-sm overflow-hidden p-2">
            <div className="p-6 flex justify-between items-center">
                <h3 className="font-bold text-xl text-gray-900">Recent Transactions</h3>
                <button className="text-black text-sm font-bold hover:underline underline-offset-4">View All</button>
            </div>
            <div className="space-y-1">
                {loading ? (
                    <div className="p-8 text-center text-gray-400 animate-pulse">Loading transactions...</div>
                ) : transactions.length > 0 ? (
                    transactions.map((tx, i) => <TransactionItem key={tx.id} transaction={tx} index={i} />)
                ) : (
                    <div className="p-12 text-center">
                        <p className="text-gray-400 font-medium">No activity in this account</p>
                    </div>
                )}
            </div>
        </div>
    );
}
