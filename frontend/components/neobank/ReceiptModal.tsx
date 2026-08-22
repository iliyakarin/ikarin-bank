'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  CheckCircle2,
  Copy,
  Check,
  Download,
  RotateCcw,
  ShieldCheck,
  Landmark,
  Zap,
  Clock,
  Send,
  CreditCard,
  Printer,
} from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { formatFedRailBadge, formatMerchantName, isTransactionIncome } from '@/lib/neobank/utils';

interface ReceiptModalProps {
  transaction: any | null;
  isOpen: boolean;
  onClose: () => void;
  onRepeatPayment?: (tx: any) => void;
}

export default function ReceiptModal({
  transaction,
  isOpen,
  onClose,
  onRepeatPayment,
}: ReceiptModalProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!isOpen || !transaction) return null;

  const handleCopy = (val: string, key: string) => {
    navigator.clipboard.writeText(val);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handlePrint = () => {
    window.print();
  };

  const rawAmount = typeof transaction.amount === 'number' ? transaction.amount : 0;
  const isIncome = isTransactionIncome(transaction);
  const formattedAmount = formatCurrency(Math.abs(rawAmount));
  const rawDate = transaction.created_at || transaction.event_time || new Date().toISOString();
  const dateObj = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');

  const rail = transaction.transaction_type || transaction.event_type || 'internal';
  const badgeInfo = formatFedRailBadge(rail);
  const merchantClean = formatMerchantName(transaction.merchant || transaction.counterparty || 'External Transfer');

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xl">
        <div className="absolute inset-0" onClick={onClose} />

        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative z-10 w-full max-w-md rounded-3xl p-6 sm:p-8 bg-gradient-to-b from-slate-900 via-slate-900/95 to-slate-950 border border-white/20 shadow-2xl text-white overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Ambient Lighting & Bank Watermark */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl -ml-16 -mb-16 pointer-events-none" />

          {/* Top Row: Official Receipt Header & Close */}
          <div className="flex items-center justify-between pb-5 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white shadow-md">
                <Landmark className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-black uppercase tracking-widest text-white block">
                  KarinBank Core
                </span>
                <span className="text-[10px] text-white/40 block font-mono">
                  Official Clearing Receipt
                </span>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white flex items-center justify-center transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Center: Success Badge & Amount */}
          <div className="my-6 text-center space-y-2">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-xl shadow-emerald-500/10">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <span className="text-xs font-bold uppercase tracking-widest text-emerald-400 block">
              Payment Cleared & Settled
            </span>

            <h1
              className={`text-4xl font-black font-mono tracking-tight ${
                isIncome ? 'text-emerald-400' : 'text-white'
              }`}
            >
              {isIncome ? `+${formattedAmount}` : `-${formattedAmount}`}
            </h1>

            <p className="text-sm font-semibold text-white/80">{merchantClean}</p>
          </div>

          {/* Receipt Details Sheet */}
          <div className="p-4 rounded-2xl bg-black/40 border border-white/10 space-y-2.5 text-xs font-mono">
            <div className="flex justify-between items-center text-white/60">
              <span>Settlement Rail:</span>
              <span className="px-2 py-0.5 rounded-md bg-white/10 text-white font-bold">
                {badgeInfo.label}
              </span>
            </div>

            <div className="flex justify-between items-center text-white/60">
              <span>Timestamp:</span>
              <span className="text-white/90">
                {dateObj.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </span>
            </div>

            <div className="flex justify-between items-center text-white/60">
              <span>Status:</span>
              <span className="text-emerald-400 font-bold">CLEARED (ISO 20022)</span>
            </div>

            {/* IMAD / OMAD (Fedwire) */}
            {transaction.imad && (
              <div className="flex justify-between items-center text-white/60 pt-1 border-t border-white/5">
                <span>Fedwire IMAD:</span>
                <div className="flex items-center gap-1.5 text-white/90">
                  <span>{transaction.imad}</span>
                  <button
                    onClick={() => handleCopy(transaction.imad, 'imad')}
                    className="text-purple-400 hover:text-purple-300"
                  >
                    {copiedKey === 'imad' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            )}

            {/* End to End ID (FedNow) */}
            {transaction.end_to_end_id && (
              <div className="flex justify-between items-center text-white/60 pt-1 border-t border-white/5">
                <span>End-to-End ID:</span>
                <div className="flex items-center gap-1.5 text-white/90">
                  <span className="truncate max-w-[140px]">{transaction.end_to_end_id}</span>
                  <button
                    onClick={() => handleCopy(transaction.end_to_end_id, 'e2e')}
                    className="text-purple-400 hover:text-purple-300"
                  >
                    {copiedKey === 'e2e' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            )}

            {/* Trace Number (ACH) */}
            {transaction.trace_number && (
              <div className="flex justify-between items-center text-white/60 pt-1 border-t border-white/5">
                <span>ACH Trace Number:</span>
                <div className="flex items-center gap-1.5 text-white/90">
                  <span>{transaction.trace_number}</span>
                  <button
                    onClick={() => handleCopy(transaction.trace_number, 'trace')}
                    className="text-purple-400 hover:text-purple-300"
                  >
                    {copiedKey === 'trace' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            )}

            {/* Transaction Reference / Hash */}
            <div className="flex justify-between items-center text-white/60 pt-1 border-t border-white/5">
              <span>Ref ID:</span>
              <div className="flex items-center gap-1.5 text-white/90">
                <span className="truncate max-w-[140px]">{transaction.id || transaction.transaction_id || 'TX-948291'}</span>
                <button
                  onClick={() => handleCopy(transaction.id || transaction.transaction_id || 'TX-948291', 'txid')}
                  className="text-purple-400 hover:text-purple-300"
                >
                  {copiedKey === 'txid' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex items-center gap-3">
            {onRepeatPayment && (
              <button
                onClick={() => {
                  onRepeatPayment(transaction);
                  onClose();
                }}
                className="flex-1 py-3.5 rounded-2xl bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold text-xs hover:from-purple-400 hover:to-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Repeat Payment</span>
              </button>
            )}

            <button
              onClick={handlePrint}
              className="p-3.5 rounded-2xl bg-white/10 hover:bg-white/15 text-white/80 hover:text-white transition-all flex items-center justify-center gap-1.5 text-xs font-semibold"
              title="Print Receipt"
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline">Print</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
