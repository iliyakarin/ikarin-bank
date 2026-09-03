'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowDownRight, ArrowUpRight, Sparkles, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';
import { Account, createSubAccount } from '@/lib/api/accounts';
import { createInternalTransfer } from '@/lib/api/transfers';
import { toCents, formatCurrency } from '@/lib/transactionUtils';
import { calculateVaultYield } from '@/lib/neobank/utils';
import { ApiError } from '@/lib/api/client';

interface VaultTransferModalProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: Account[];
  initialMode?: 'deposit' | 'withdraw';
  onSuccess?: (message: string) => void;
  refreshBalance: () => Promise<void>;
}

export default function VaultTransferModal({
  isOpen,
  onClose,
  accounts,
  initialMode = 'deposit',
  onSuccess,
  refreshBalance,
}: VaultTransferModalProps) {
  const [mode, setMode] = useState<'deposit' | 'withdraw'>(initialMode);
  const [amountStr, setAmountStr] = useState('500.00');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync mode whenever initialMode changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setError(null);
    }
  }, [isOpen, initialMode]);

  const mainAccount = accounts.find((a) => a.is_main) || accounts[0];
  const savingsAccount = accounts.find(
    (a) => !a.is_main && (a.name.toLowerCase().includes('savings') || a.name.toLowerCase().includes('vault'))
  ) || accounts.find((a) => !a.is_main);

  const checkingBalanceCents = mainAccount?.balance || 0;
  const vaultBalanceCents = savingsAccount?.balance || 0;

  const currentSourceBalance = mode === 'deposit' ? checkingBalanceCents : vaultBalanceCents;
  const currentTargetBalance = mode === 'deposit' ? vaultBalanceCents : checkingBalanceCents;

  const depositCents = toCents(amountStr);
  const yieldEstimate = calculateVaultYield(depositCents > 0 ? depositCents : 0, 4.85);

  const handleQuickChip = (val: string) => {
    setError(null);
    if (val === '25%') {
      const amt = Math.floor(currentSourceBalance * 0.25);
      setAmountStr((amt / 100).toFixed(2));
    } else if (val === '50%') {
      const amt = Math.floor(currentSourceBalance * 0.5);
      setAmountStr((amt / 100).toFixed(2));
    } else if (val === 'max') {
      setAmountStr((currentSourceBalance / 100).toFixed(2));
    } else {
      setAmountStr(val);
    }
  };

  const handleExecuteTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cents = toCents(amountStr);
    if (cents <= 0) {
      setError('Please enter a transfer amount greater than $0.00.');
      return;
    }

    if (cents > currentSourceBalance) {
      const sourceName = mode === 'deposit' ? 'Main Checking' : 'High-Yield Savings Vault';
      setError(`Insufficient funds in ${sourceName}. Available: ${formatCurrency(currentSourceBalance)}`);
      return;
    }

    setLoading(true);
    try {
      let targetSavingsId = savingsAccount?.id;

      // Auto-provision High Yield Savings sub-account if none exists yet
      if (!targetSavingsId) {
        await createSubAccount('High Yield Savings');
        await refreshBalance();
        // Fallback reload accounts if state not updated synchronously
        targetSavingsId = mainAccount?.id ? mainAccount.id + 1 : 2;
      }

      const fromId = mode === 'deposit' ? mainAccount.id : targetSavingsId;
      const toId = mode === 'deposit' ? targetSavingsId : mainAccount.id;

      const commentary =
        mode === 'deposit'
          ? 'Deposit to Treasury High-Yield Savings Vault'
          : 'Withdrawal from Treasury High-Yield Savings Vault to Checking';

      await createInternalTransfer({
        from_account_id: fromId,
        to_account_id: toId,
        amount: cents,
        commentary,
        idempotency_key: `vault-tx-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      });

      await refreshBalance();
      const successMsg =
        mode === 'deposit'
          ? `Successfully deposited ${formatCurrency(cents)} into High-Yield Savings Vault!`
          : `Successfully withdrew ${formatCurrency(cents)} from Savings Vault to Main Checking!`;

      if (onSuccess) onSuccess(successMsg);
      onClose();
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.detail?.detail || 'Vault transfer failed');
      } else {
        setError(err.message || 'Connection error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-lg rounded-3xl p-6 sm:p-8 bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-950 border border-white/15 shadow-2xl backdrop-blur-2xl text-white overflow-hidden"
        >
          {/* Ambient Glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/15 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-teal-500/15 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none" />

          {/* Header Row */}
          <div className="relative z-10 flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight">
                  High-Yield Savings Vault
                </h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono text-[10px] font-bold border border-emerald-500/30">
                    4.85% APY
                  </span>
                  <span className="text-xs text-white/50">Internal Transfer</span>
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="relative z-10 grid grid-cols-2 gap-2 p-1.5 bg-white/[0.04] rounded-2xl border border-white/10 my-6">
            <button
              type="button"
              onClick={() => {
                setMode('deposit');
                setError(null);
              }}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'deposit'
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <ArrowDownRight className="w-4 h-4" />
              <span>Deposit to Vault</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setMode('withdraw');
                setError(null);
              }}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'withdraw'
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <ArrowUpRight className="w-4 h-4" />
              <span>Withdraw to Checking</span>
            </button>
          </div>

          {/* Account Route Cards */}
          <div className="relative z-10 grid grid-cols-1 sm:grid-cols-[1fr,auto,1fr] items-center gap-2.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10">
            <div>
              <span className="text-[10px] uppercase font-bold text-white/40 block">From</span>
              <span className="text-xs font-bold text-white block">
                {mode === 'deposit' ? 'Main Checking' : 'High-Yield Vault'}
              </span>
              <span className="font-mono text-xs text-white/60 block mt-0.5">
                {formatCurrency(currentSourceBalance)}
              </span>
            </div>

            <div className="hidden sm:flex justify-center text-white/30">
              <ArrowRight className="w-4 h-4" />
            </div>

            <div className="text-left sm:text-right">
              <span className="text-[10px] uppercase font-bold text-white/40 block">To</span>
              <span className="text-xs font-bold text-emerald-400 block">
                {mode === 'deposit' ? 'High-Yield Vault' : 'Main Checking'}
              </span>
              <span className="font-mono text-xs text-white/60 block mt-0.5">
                {formatCurrency(currentTargetBalance)}
              </span>
            </div>
          </div>

          <form onSubmit={handleExecuteTransfer} className="relative z-10 space-y-5 mt-6">
            {/* Amount Input */}
            <div className="space-y-2 text-center">
              <span className="text-xs font-bold uppercase tracking-wider text-white/50 block">
                Transfer Amount
              </span>

              <div className="relative inline-block mx-auto">
                <span className="text-3xl text-white/40 font-mono absolute -left-7 top-1">$</span>
                <input
                  type="text"
                  value={amountStr}
                  onChange={(e) => {
                    setAmountStr(e.target.value);
                    setError(null);
                  }}
                  className="text-4xl sm:text-5xl font-black font-mono tracking-tight bg-transparent text-center text-white outline-none border-b-2 border-emerald-500/50 focus:border-emerald-400 pb-1 w-52"
                />
              </div>

              {/* Quick Chips */}
              <div className="flex items-center justify-center gap-2 flex-wrap pt-2">
                {['100.00', '500.00', '1000.00', '5000.00', '25%', '50%', 'max'].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => handleQuickChip(chip)}
                    className={`px-3 py-1 rounded-xl text-xs font-mono font-bold transition-all ${
                      amountStr === chip
                        ? 'bg-emerald-500 text-slate-950 font-black shadow-md'
                        : 'bg-white/[0.05] hover:bg-white/10 text-white/70 border border-white/10'
                    }`}
                  >
                    {chip === 'max' ? 'Max' : chip.includes('%') ? chip : `$${chip}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Live Yield Calculation Preview for Deposits */}
            {mode === 'deposit' && depositCents > 0 && (
              <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span>Projected Yield Return:</span>
                </div>
                <span className="font-mono font-bold text-emerald-300">
                  +{formatCurrency(yieldEstimate.annualCents)}/yr (+{formatCurrency(yieldEstimate.monthlyCents)}/mo)
                </span>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="p-3.5 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-4 rounded-2xl bg-white/10 hover:bg-white/15 text-white/80 font-bold text-sm transition-all"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={loading || !amountStr || parseFloat(amountStr) <= 0}
                className={`flex-1 py-4 rounded-2xl font-bold text-sm text-slate-950 active:scale-98 transition-all disabled:opacity-40 flex items-center justify-center gap-2 shadow-xl ${
                  mode === 'deposit'
                    ? 'bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-emerald-500/20'
                    : 'bg-gradient-to-r from-purple-400 to-indigo-400 hover:from-purple-300 hover:to-indigo-300 shadow-purple-500/20 text-white'
                }`}
              >
                {loading ? (
                  <span className="animate-pulse">Authorizing Internal Transfer...</span>
                ) : (
                  <>
                    <span>
                      {mode === 'deposit' ? 'Confirm Deposit to Vault' : 'Confirm Withdrawal to Checking'}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
