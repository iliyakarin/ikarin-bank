'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowUpRight, PiggyBank, ShieldCheck } from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { calculateVaultYield } from '@/lib/neobank/utils';

interface VaultCardProps {
  balanceCents: number;
  goalCents?: number;
  goalName?: string;
  apyPercent?: number;
  onDepositClick?: () => void;
}

export default function VaultCard({
  balanceCents = 250000, // $2,500.00 default
  goalCents = 1000000, // $10,000.00 default
  goalName = 'Emergency & Travel Fund',
  apyPercent = 4.85,
  onDepositClick,
}: VaultCardProps) {
  const yieldInfo = calculateVaultYield(balanceCents, apyPercent);
  const progressPercent = Math.min(100, Math.round((balanceCents / goalCents) * 100));

  return (
    <div className="relative w-full h-full rounded-3xl p-7 flex flex-col justify-between overflow-hidden shadow-2xl border border-white/15 bg-gradient-to-br from-emerald-950/80 via-slate-900/90 to-slate-950 text-white group">
      {/* Ambient background glow */}
      <div className="absolute top-0 right-0 w-52 h-52 bg-emerald-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-52 h-52 bg-teal-500/10 rounded-full blur-3xl -ml-16 -mb-16 pointer-events-none" />

      {/* Top section: Vault Header */}
      <div className="relative z-10 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
            <PiggyBank className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">High-Yield Vault</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono text-[10px] font-bold border border-emerald-500/30">
                {yieldInfo.formattedApy}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white tracking-tight">{goalName}</h3>
          </div>
        </div>

        <button
          onClick={onDepositClick}
          className="p-2.5 rounded-xl bg-white/10 hover:bg-emerald-500/20 hover:text-emerald-300 border border-white/10 hover:border-emerald-500/30 transition-all flex items-center gap-1.5 text-xs font-semibold text-white/80"
          title="Add to Vault"
        >
          <span>Deposit</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Middle section: Balance & Projected Yield */}
      <div className="relative z-10 my-4 space-y-1">
        <span className="text-xs font-medium text-white/50 block">Current Vault Savings</span>
        <div className="flex items-baseline gap-3">
          <span className="text-4xl lg:text-5xl font-black font-mono tracking-tight text-white">
            {formatCurrency(balanceCents / 100)}
          </span>
          <div className="flex items-center gap-1 text-emerald-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>+${(yieldInfo.monthlyCents / 100).toFixed(2)}/mo yield</span>
          </div>
        </div>
      </div>

      {/* Bottom section: Goal Progress & FDIC guarantee */}
      <div className="relative z-10 space-y-3">
        <div>
          <div className="flex justify-between text-xs font-semibold text-white/70 mb-1.5">
            <span>Goal Progress: {progressPercent}%</span>
            <span className="font-mono">{formatCurrency(goalCents / 100)} target</span>
          </div>
          <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_12px_rgba(16,185,129,0.5)]"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-1 text-[11px] text-white/40">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/70" />
            <span>FDIC Insured up to $250,000</span>
          </div>
          <span className="text-white/30 font-mono">Compounded Daily</span>
        </div>
      </div>
    </div>
  );
}
