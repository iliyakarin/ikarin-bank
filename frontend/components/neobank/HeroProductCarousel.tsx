'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, Check, Eye, EyeOff, ShieldCheck, TrendingUp, Landmark, PiggyBank, CreditCard, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { Account } from '@/lib/api/accounts';
import VaultCard from './VaultCard';
import DigitalCardPreview from './DigitalCardPreview';

interface HeroProductCarouselProps {
  balance: number; // In cents
  reservedBalance?: number | null;
  routingNumber?: string;
  accountNumber?: string;
  userName?: string;
  growthPercent?: number;
  loading?: boolean;
  accounts?: Account[];
  activeTab?: 'checking' | 'vault' | 'card';
  onTabChange?: (tab: 'checking' | 'vault' | 'card') => void;
  onDepositClick?: () => void;
  onWithdrawClick?: () => void;
  onSendClick?: () => void;
}

export default function HeroProductCarousel({
  balance = 0,
  reservedBalance = null,
  routingNumber = '123456780',
  accountNumber = '100000001',
  userName = 'JOHN DOE',
  growthPercent = 2.5,
  loading = false,
  accounts = [],
  activeTab: controlledActiveTab,
  onTabChange,
  onDepositClick,
  onWithdrawClick,
  onSendClick,
}: HeroProductCarouselProps) {
  const [internalActiveTab, setInternalActiveTab] = useState<'checking' | 'vault' | 'card'>('checking');
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;

  const setActiveTab = (tab: 'checking' | 'vault' | 'card') => {
    setInternalActiveTab(tab);
    if (onTabChange) onTabChange(tab);
  };

  const savingsAccount = accounts.find(
    (a) => !a.is_main && (a.name.toLowerCase().includes('savings') || a.name.toLowerCase().includes('vault'))
  ) || accounts.find((a) => !a.is_main);

  const effectiveVaultBalanceCents = savingsAccount != null
    ? savingsAccount.balance
    : Math.round(balance * 0.35);

  const [hideBalance, setHideBalance] = useState(false);
  const [copiedField, setCopiedField] = useState<'routing' | 'account' | null>(null);

  const handleCopy = (text: string, field: 'routing' | 'account') => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2500);
  };

  return (
    <div className="w-full space-y-4">
      {/* Product Selection Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 p-1 bg-white/[0.04] backdrop-blur-xl rounded-2xl border border-white/10">
          <button
            onClick={() => setActiveTab('checking')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'checking'
                ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Landmark className="w-3.5 h-3.5" />
            <span>Main Checking</span>
          </button>

          <button
            onClick={() => setActiveTab('vault')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'vault'
                ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <PiggyBank className="w-3.5 h-3.5" />
            <span>Savings Vault (4.85% APY)</span>
          </button>

          <button
            onClick={() => setActiveTab('card')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'card'
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/20'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Black Card</span>
          </button>
        </div>

        {/* Balance Visibility Toggle */}
        <button
          onClick={() => setHideBalance((prev) => !prev)}
          className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-white/50 hover:text-white border border-white/10 transition-all flex items-center gap-1.5 text-xs font-medium"
          title={hideBalance ? 'Show Balances' : 'Hide Balances'}
        >
          {hideBalance ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          <span className="hidden sm:inline">{hideBalance ? 'Show' : 'Hide'}</span>
        </button>
      </div>

      {/* Main Carousel Display Card */}
      <div className="relative w-full min-h-[290px]">
        <AnimatePresence mode="wait">
          {activeTab === 'checking' && (
            <motion.div
              key="checking"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 15 }}
              transition={{ duration: 0.25 }}
              className="w-full h-full rounded-3xl p-7 lg:p-8 flex flex-col justify-between overflow-hidden shadow-2xl border border-white/20 bg-gradient-to-br from-purple-950/70 via-indigo-950/80 to-slate-950 text-white relative"
            >
              {/* Ambient Lights */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/15 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/15 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none" />

              {/* Top Row: Account Label & Security */}
              <div className="relative z-10 flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-widest text-purple-300">
                      Primary Checking (USD)
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-200 text-[10px] font-bold border border-purple-500/30">
                      Active • Tier 1
                    </span>
                  </div>
                  <p className="text-xs text-white/50 mt-0.5">United States Federal Reserve Member</p>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-emerald-400 text-xs font-bold">
                    <ShieldCheck className="w-4 h-4" />
                    <span>FDIC Protected</span>
                  </div>
                </div>
              </div>

              {/* Center: Main Balance */}
              <div className="relative z-10 my-4 space-y-2">
                <span className="text-xs font-medium text-white/50 block">Available Balance</span>
                <div className="flex items-baseline gap-3 flex-wrap">
                  <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black font-mono tracking-tight text-white drop-shadow-md">
                    {loading ? (
                      <div className="h-14 w-56 bg-white/10 rounded-2xl animate-pulse" />
                    ) : hideBalance ? (
                      '••••••••'
                    ) : (
                      formatCurrency(balance)
                    )}
                  </h1>

                  {!loading && reservedBalance != null && reservedBalance > 0 && (
                    <span className="px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold text-xs border border-indigo-500/30">
                      +{formatCurrency(reservedBalance)} pending clearance
                    </span>
                  )}
                </div>

                {!loading && (
                  <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold pt-1">
                    <TrendingUp className="w-4 h-4" />
                    <span>+{growthPercent}% income increase this month</span>
                  </div>
                )}
              </div>

              {/* Bottom Row: Direct Deposit Credentials (Routing & Account) */}
              <div className="relative z-10 flex items-center gap-4 sm:gap-8 pt-3 border-t border-white/10 flex-wrap">
                {/* Routing Number */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white/40">Routing (ABA):</span>
                  <span className="font-mono font-bold text-xs text-white/90">{routingNumber}</span>
                  <button
                    onClick={() => handleCopy(routingNumber, 'routing')}
                    className="p-1 text-white/40 hover:text-purple-300 transition-colors"
                    title="Copy Routing Number"
                  >
                    {copiedField === 'routing' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>

                {/* Account Number */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white/40">Account:</span>
                  <span className="font-mono font-bold text-xs text-white/90">
                    {hideBalance ? '••••••••' : accountNumber}
                  </span>
                  <button
                    onClick={() => handleCopy(accountNumber, 'account')}
                    className="p-1 text-white/40 hover:text-purple-300 transition-colors"
                    title="Copy Account Number"
                  >
                    {copiedField === 'account' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>

                {copiedField && (
                  <span className="text-[11px] text-emerald-400 font-semibold animate-pulse">
                    ✓ {copiedField === 'routing' ? 'Routing number' : 'Account number'} copied!
                  </span>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'vault' && (
            <motion.div
              key="vault"
              initial={{ opacity: 0, x: 15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -15 }}
              transition={{ duration: 0.25 }}
              className="w-full h-full"
            >
              <VaultCard
                balanceCents={effectiveVaultBalanceCents}
                goalName="Treasury High-Yield Savings Vault"
                apyPercent={4.85}
                onDepositClick={onDepositClick}
                onWithdrawClick={onWithdrawClick}
              />
            </motion.div>
          )}

          {activeTab === 'card' && (
            <motion.div
              key="card"
              initial={{ opacity: 0, x: 15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -15 }}
              transition={{ duration: 0.25 }}
              className="w-full h-full"
            >
              <DigitalCardPreview
                cardHolder={userName.toUpperCase()}
                cardNumber="5542889012234567"
                expiry="12/28"
                cvv="739"
                cardType="debit"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
