'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { useTransactions, useBalance } from '@/hooks/useDashboard';
import { RefreshCw, CheckCircle2, ArrowRight, TrendingUp, Sparkles } from 'lucide-react';
import StoriesBar from '@/components/neobank/StoriesBar';
import HeroProductCarousel from '@/components/neobank/HeroProductCarousel';
import QuickActionHub from '@/components/neobank/QuickActionHub';
import DailyActivityFeed from '@/components/neobank/DailyActivityFeed';
import SimLabDrawer from '@/components/neobank/SimLabDrawer';
import SubAccountManager from '@/components/SubAccountManager';
import { FastPayPayee } from '@/lib/neobank/types';

export default function ClientDashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [showSuccess, setShowSuccess] = useState(false);

  const {
    transactions,
    loading: transactionsLoading,
    refresh: refreshTransactions,
  } = useTransactions(720, true);

  const {
    balance,
    reservedBalance,
    accounts,
    loading: balanceLoading,
    refresh: refreshBalance,
  } = useBalance(true);

  const handleRefreshAll = async () => {
    await Promise.all([refreshTransactions(), refreshBalance()]);
  };

  const isRefreshing = transactionsLoading || balanceLoading;

  // Handle URL success query flag
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('success') === 'true') {
      setShowSuccess(true);
      window.history.replaceState({}, '', window.location.pathname);
      const timer = setTimeout(() => setShowSuccess(false), 4000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleStoryAction = (actionType: string) => {
    switch (actionType) {
      case 'savings':
      case 'deposit':
        router.push('/client/deposit');
        break;
      case 'transfer':
        router.push('/client/send');
        break;
      case 'cashback':
      case 'security':
        router.push('/client/cards');
        break;
      case 'analytics':
        router.push('/client/analytics');
        break;
      default:
        router.push('/client/send');
    }
  };

  const handleSelectFastPay = (payee: FastPayPayee) => {
    router.push('/client/send');
  };

  const primaryAccount = accounts[0];
  const routingNum = primaryAccount?.routing_number || '123456780';
  const accountNum = primaryAccount?.account_number || '100000001';
  const displayName = user?.first_name ? `${user.first_name} ${user.last_name || ''}` : 'Consumer';

  return (
    <div className="space-y-8 pb-16 text-white max-w-7xl mx-auto">
      {/* Top Bar: User Greeting & Refresh Button */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-400 block">
            Good day, {displayName}
          </span>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Financial Dashboard
          </h1>
        </div>

        <button
          onClick={handleRefreshAll}
          disabled={isRefreshing}
          className="p-3 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] text-white/70 hover:text-white border border-white/10 transition-all flex items-center gap-2 text-xs font-semibold"
          title="Refresh Data"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-purple-400' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Success Banner */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-semibold flex items-center gap-3 shadow-lg"
          >
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <span>Operation completed and ledger balances updated successfully!</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 1. Stories & Financial Highlights Bar */}
      <section className="w-full">
        <StoriesBar onActionClick={handleStoryAction} />
      </section>

      {/* 2. Interactive Multi-Product Hero Carousel */}
      <section className="w-full">
        <HeroProductCarousel
          balance={balance || 0}
          reservedBalance={reservedBalance}
          routingNumber={routingNum}
          accountNumber={accountNum}
          userName={displayName}
          growthPercent={2.5}
          loading={balanceLoading}
          onDepositClick={() => router.push('/client/deposit')}
          onSendClick={() => router.push('/client/send')}
        />
      </section>

      {/* 3. Quick Action Hub & Fast Pay Avatars */}
      <section className="w-full">
        <QuickActionHub
          onSendClick={() => router.push('/client/send')}
          onDepositClick={() => router.push('/client/deposit')}
          onPayBillsClick={() => router.push('/client/send')}
          onCardControlsClick={() => router.push('/client/cards')}
          onSelectPayee={handleSelectFastPay}
        />
      </section>

      {/* 4. Sub-Accounts & Daily Activity Feed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Daily Activity Feed (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between px-1">
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">Recent Activity</h3>
              <p className="text-xs text-white/40">Tap any transaction for official ISO receipt</p>
            </div>

            <button
              onClick={() => router.push('/client/transactions')}
              className="text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <DailyActivityFeed
            transactions={transactions}
            loading={transactionsLoading}
            limit={12}
            onRepeatPayment={() => router.push('/client/send')}
          />
        </div>

        {/* Right Column: Multi-Account Management & Analytics Teaser (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Sub-Accounts Manager */}
          <SubAccountManager accounts={accounts} refresh={refreshBalance} />

          {/* Quick Analytics Teaser Card */}
          <motion.div
            whileHover={{ scale: 1.02, y: -2 }}
            onClick={() => router.push('/client/analytics')}
            className="p-6 rounded-3xl bg-gradient-to-br from-purple-950/40 via-slate-900 to-slate-950 border border-purple-500/20 hover:border-purple-500/40 shadow-xl backdrop-blur-xl cursor-pointer transition-all space-y-4 group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-2xl bg-purple-500/20 text-purple-300 flex items-center justify-center border border-purple-500/30">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-300 block">
                    Analytics Studio
                  </span>
                  <span className="text-sm font-bold text-white">ClickHouse Telemetry</span>
                </div>
              </div>

              <div className="p-2 rounded-xl bg-white/5 text-white/60 group-hover:text-white group-hover:bg-white/10 transition-colors">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>

            <p className="text-xs text-white/60 leading-relaxed">
              Explore your cashflow trends, spending distribution across 14 categories, and top merchant rankings in real-time.
            </p>

            <div className="pt-2 border-t border-white/5 flex items-center justify-between text-xs text-purple-400 font-semibold">
              <span>Open Full Analytics</span>
              <span className="font-mono text-[10px] text-white/40">30-Day Breakdown →</span>
            </div>
          </motion.div>
        </div>
      </div>

      {/* 5. Developer & Simulator Floating Drawer (Strictly Admin Role Gated) */}
      <SimLabDrawer onScenarioInjected={handleRefreshAll} />
    </div>
  );
}
