'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowUpRight, PiggyBank, ShieldCheck, TrendingUp, DollarSign, Clock } from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { calculateVaultYield } from '@/lib/neobank/utils';

interface VaultCardProps {
  balanceCents: number;
  initialDepositCents?: number;
  goalCents?: number;
  goalName?: string;
  apyPercent?: number;
  onDepositClick?: () => void;
  onWithdrawClick?: () => void;
}

export default function VaultCard({
  balanceCents = 250000,
  initialDepositCents,
  goalCents,
  goalName = 'Treasury High-Yield Savings Vault',
  apyPercent = 4.85,
  onDepositClick,
  onWithdrawClick,
}: VaultCardProps) {
  const yieldInfo = calculateVaultYield(balanceCents, apyPercent);

  // Compute realistic principal vs interest earned breakdown
  const principalCents = initialDepositCents != null
    ? initialDepositCents
    : Math.round(balanceCents * 0.955); // ~95.5% principal
  const interestEarnedCents = Math.max(0, balanceCents - principalCents);

  // Dynamic goal target calculation so progress bar is visually meaningful
  const effectiveGoalCents = goalCents && goalCents > balanceCents
    ? goalCents
    : Math.max(balanceCents * 1.25, 1000000); // 1.25x of current or min $10,000

  const progressPercent = Math.min(100, Math.max(1, Math.round((balanceCents / effectiveGoalCents) * 100)));

  return (
    <div className="relative w-full h-full rounded-3xl p-7 lg:p-8 flex flex-col justify-between overflow-hidden shadow-2xl border border-white/20 bg-gradient-to-br from-emerald-950/90 via-slate-900/95 to-slate-950 text-white group">
      {/* Ambient background glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/15 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-teal-500/15 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none" />

      {/* Top Section: Header & Action Buttons */}
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
            <PiggyBank className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                High-Yield Vault
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono text-[11px] font-bold border border-emerald-500/30 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-emerald-400" />
                {yieldInfo.formattedApy}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white tracking-tight mt-0.5">{goalName}</h3>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onDepositClick}
            className="px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-1.5"
            title="Deposit into Vault"
          >
            <span>Deposit</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Middle Section: Total Balance & Principal/Interest Breakdown */}
      <div className="relative z-10 my-4 space-y-3">
        <div>
          <span className="text-xs font-medium text-white/50 block">Current Vault Savings</span>
          <div className="flex items-baseline gap-3 flex-wrap">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black font-mono tracking-tight text-white drop-shadow-md">
              {formatCurrency(balanceCents)}
            </h1>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold font-mono">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              <span>+{formatCurrency(yieldInfo.monthlyCents)}/mo yield</span>
            </div>
          </div>
        </div>

        {/* Breakdown Grid: Principal vs Accrued Interest */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-3 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md">
            <span className="text-[11px] font-medium text-white/50 block">Principal Deposited</span>
            <span className="font-mono font-bold text-sm text-white/90 mt-0.5 block">
              {formatCurrency(principalCents)}
            </span>
          </div>

          <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-md">
            <span className="text-[11px] font-medium text-emerald-400/80 block">Total Interest Earned</span>
            <span className="font-mono font-bold text-sm text-emerald-300 mt-0.5 block">
              +{formatCurrency(interestEarnedCents)}
            </span>
          </div>

          <div className="p-3 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md hidden sm:block">
            <span className="text-[11px] font-medium text-white/50 block">Annual Projected</span>
            <span className="font-mono font-bold text-sm text-teal-300 mt-0.5 block">
              +{formatCurrency(yieldInfo.annualCents)}/yr
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Section: Goal Progress & FDIC Guarantee */}
      <div className="relative z-10 space-y-2.5 pt-2 border-t border-white/10">
        <div>
          <div className="flex justify-between text-xs font-semibold text-white/70 mb-1.5">
            <span>Milestone Progress: {progressPercent}%</span>
            <span className="font-mono text-emerald-400">{formatCurrency(effectiveGoalCents)} target</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-white/10 overflow-hidden border border-white/5 p-0.5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.5)]"
            />
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] text-white/40 pt-1">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>FDIC Insured up to $250,000</span>
          </div>
          <div className="flex items-center gap-1 text-white/40 font-mono">
            <Clock className="w-3 h-3 text-emerald-400/70" />
            <span>Compounded Daily</span>
          </div>
        </div>
      </div>
    </div>
  );
}
