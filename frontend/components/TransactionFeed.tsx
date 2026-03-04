"use client";
import { Transaction } from '@/lib/types';
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON } from '@/lib/constants';

interface TransactionItemProps {
    transaction: Transaction;
}

function TransactionItem({ transaction }: TransactionItemProps) {
    const isPending = transaction.status === 'pending';
    const isProcessing = transaction.status === 'sent_to_kafka';
    const icon = CATEGORY_ICONS[transaction.category] || DEFAULT_CATEGORY_ICON;

    // Determine if this is a deduction (expense or transfer) or income
    const isIncome = transaction.transaction_type === 'income';
    const isDeduction = transaction.transaction_type === 'expense' || transaction.transaction_type === 'transfer';
    const amountColor = isIncome ? 'text-gray-900' : 'text-red-500';
    const amountPrefix = isIncome ? '+' : '-';

    return (
        <div className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors cursor-pointer group">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <div>
                    <p className="font-bold text-gray-900">{transaction.merchant}</p>
                    <div className="flex items-center gap-2">
                        <p className="text-xs text-gray-500">{transaction.category}</p>
                        {isPending && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-orange-500 uppercase tracking-tighter animate-pulse">
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
                                Pending
                            </span>
                        )}
                        {isProcessing && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-blue-500 uppercase tracking-tighter animate-pulse-subtle">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                Processing
                            </span>
                        )}
                        {!isPending && !isProcessing && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-green-500 uppercase tracking-tighter">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                Cleared
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <div className="text-right">
                <p className={`font-bold ${amountColor}`}>
                    {amountPrefix}${Math.abs(transaction.amount).toFixed(2)}
                </p>
                <p className="text-[10px] text-gray-400">
                    {new Date(transaction.created_at + 'Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </p>
            </div>
        </div>
    );
}

export function TransactionSkeleton() {
    return (
        <div className="animate-pulse flex items-center justify-between p-4 bg-white">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gray-200"></div>
                <div className="space-y-2">
                    <div className="h-4 w-32 bg-gray-200 rounded"></div>
                    <div className="h-3 w-16 bg-gray-100 rounded"></div>
                </div>
            </div>
            <div className="space-y-2 flex flex-col items-end">
                <div className="h-4 w-16 bg-gray-200 rounded"></div>
                <div className="h-3 w-12 bg-gray-100 rounded"></div>
            </div>
        </div>
    );
}

export default function TransactionFeed({ transactions, loading }: { transactions: Transaction[], loading: boolean }) {
    if (loading) {
        return (
            <div className="divide-y divide-gray-100">
                {[...Array(5)].map((_, i) => <TransactionSkeleton key={i} />)}
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-50 flex justify-between items-center">
                <h3 className="font-bold text-gray-900">Recent Activity</h3>
                <button className="text-primary-600 text-xs font-semibold hover:underline">View All</button>
            </div>
            <div className="divide-y divide-gray-100">
                {transactions.length > 0 ? (
                    transactions.map((tx) => <TransactionItem key={tx.id} transaction={tx} />)
                ) : (
                    <div className="p-10 text-center">
                        <p className="text-gray-400 text-sm">No transactions yet</p>
                    </div>
                )}
            </div>
        </div>
    );
}
