'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowDownLeft,
  ArrowUpRight,
  Zap,
  Landmark,
  Clock,
  Send,
  CreditCard,
  Building2,
  Tv,
  Car,
  Coffee,
  ShoppingBag,
  Receipt,
  FileText,
} from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { groupTransactionsByDate, formatFedRailBadge, formatMerchantName } from '@/lib/neobank/utils';
import ReceiptModal from './ReceiptModal';

interface DailyActivityFeedProps {
  transactions: any[];
  loading?: boolean;
  onRepeatPayment?: (tx: any) => void;
  limit?: number;
}

export default function DailyActivityFeed({
  transactions = [],
  loading = false,
  onRepeatPayment,
  limit,
}: DailyActivityFeedProps) {
  const [selectedTx, setSelectedTx] = useState<any | null>(null);

  const displayedTxs = limit ? transactions.slice(0, limit) : transactions;
  const grouped = groupTransactionsByDate(displayedTxs);

  const getMerchantIcon = (merchantName: string, category?: string) => {
    const upper = (merchantName || '').toUpperCase();
    if (upper.includes('NETFLIX') || upper.includes('SPOTIFY')) {
      return <Tv className="w-5 h-5 text-rose-400" />;
    }
    if (upper.includes('UBER') || upper.includes('LYFT')) {
      return <Car className="w-5 h-5 text-blue-400" />;
    }
    if (upper.includes('STARBUCKS') || upper.includes('COFFEE')) {
      return <Coffee className="w-5 h-5 text-amber-400" />;
    }
    if (upper.includes('PG&E') || upper.includes('UTILITY') || upper.includes('ELECTRIC')) {
      return <FileText className="w-5 h-5 text-emerald-400" />;
    }
    if (upper.includes('VANGUARD') || upper.includes('FEDWIRE') || upper.includes('SETTLEMENT')) {
      return <Landmark className="w-5 h-5 text-indigo-400" />;
    }
    if (upper.includes('AMAZON') || upper.includes('SHOP') || upper.includes('APPLE')) {
      return <ShoppingBag className="w-5 h-5 text-purple-400" />;
    }
    return <CreditCard className="w-5 h-5 text-white/60" />;
  };

  const getRailIcon = (rail: string) => {
    switch (rail) {
      case 'fednow':
        return <Zap className="w-2.5 h-2.5 text-emerald-300" />;
      case 'wire':
        return <Landmark className="w-2.5 h-2.5 text-indigo-300" />;
      case 'ach':
        return <Clock className="w-2.5 h-2.5 text-amber-300" />;
      default:
        return <Send className="w-2.5 h-2.5 text-purple-300" />;
    }
  };

  if (loading) {
    return (
      <div className="w-full space-y-3">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="h-16 rounded-2xl bg-white/[0.04] animate-pulse border border-white/5" />
        ))}
      </div>
    );
  }

  if (displayedTxs.length === 0) {
    return (
      <div className="w-full p-12 text-center rounded-3xl bg-white/[0.02] border border-white/5 space-y-2">
        <Receipt className="w-10 h-10 text-white/20 mx-auto" />
        <h4 className="text-sm font-bold text-white/70">No Recent Transactions</h4>
        <p className="text-xs text-white/40">Your daily financial transactions will appear here.</p>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {Object.entries(grouped).map(([dateGroup, items]) => (
        <div key={dateGroup} className="space-y-2.5">
          {/* Date Header Badge */}
          <div className="sticky top-0 z-10 py-1 bg-[#050510]/80 backdrop-blur-md">
            <span className="text-xs font-bold uppercase tracking-wider text-white/40 px-1">
              {dateGroup}
            </span>
          </div>

          {/* Transaction Items */}
          <div className="space-y-2">
            {items.map((tx: any, idx: number) => {
              const rawAmount = typeof tx.amount === 'number' ? tx.amount : 0;
              const isIncome = rawAmount > 0;
              const formattedAmt = formatCurrency(Math.abs(rawAmount));
              const rail = tx.transaction_type || tx.event_type || 'internal';
              const badgeInfo = formatFedRailBadge(rail);
              const brandName = formatMerchantName(
                tx.merchant || tx.counterparty || tx.recipient_email || 'Transaction'
              );

              return (
                <motion.div
                  key={tx.id || tx.transaction_id || `tx-${idx}`}
                  whileHover={{ scale: 1.01, x: 2 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => setSelectedTx(tx)}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.06] hover:border-purple-500/30 backdrop-blur-xl transition-all cursor-pointer flex items-center justify-between gap-4 group"
                >
                  {/* Left: Brand Icon & Titles */}
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-2xl bg-white/[0.05] border border-white/10 flex items-center justify-center shadow-md group-hover:border-purple-400/40 transition-colors">
                        {getMerchantIcon(brandName, tx.category)}
                      </div>

                      {/* Little Rail Indicator */}
                      <div
                        className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-slate-950 border border-white/20 flex items-center justify-center"
                        title={badgeInfo.label}
                      >
                        {getRailIcon(rail)}
                      </div>
                    </div>

                    <div className="min-w-0">
                      <span className="text-sm font-bold text-white group-hover:text-purple-200 transition-colors truncate block">
                        {brandName}
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-white/40 truncate">
                          {tx.category || badgeInfo.label}
                        </span>
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-white/5 text-white/40 border border-white/5">
                          {badgeInfo.label}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Amount & Status */}
                  <div className="text-right flex-shrink-0">
                    <span
                      className={`text-sm lg:text-base font-black font-mono tracking-tight block ${
                        isIncome ? 'text-emerald-400' : 'text-white'
                      }`}
                    >
                      {isIncome ? `+${formattedAmt}` : `-${formattedAmt}`}
                    </span>
                    <span className="text-[10px] text-white/30 font-medium block capitalize">
                      {tx.status || 'cleared'}
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Interactive Digital Receipt Modal */}
      <ReceiptModal
        transaction={selectedTx}
        isOpen={!!selectedTx}
        onClose={() => setSelectedTx(null)}
        onRepeatPayment={onRepeatPayment}
      />
    </div>
  );
}
