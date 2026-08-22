'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CreditCard,
  Lock,
  Unlock,
  ShieldCheck,
  Globe,
  Smartphone,
  Sliders,
  DollarSign,
  Plus,
  Zap,
  RotateCcw,
  CheckCircle2,
  Building2,
} from 'lucide-react';
import DigitalCardPreview from './DigitalCardPreview';
import { formatCurrency } from '@/lib/transactionUtils';
import { CardDetails } from '@/lib/neobank/types';

interface CardSecurityHubProps {
  cards?: CardDetails[];
  onGenerateVirtualCard?: () => void;
}

const DEFAULT_CARDS: CardDetails[] = [
  {
    id: 'card-debit-1',
    cardNumber: '5542889012234567',
    cardHolder: 'JOHN DOE',
    expiry: '12/28',
    cvv: '739',
    cardType: 'debit',
    isFrozen: false,
    dailySpendingLimitCents: 500000, // $5,000
    monthlySpendingLimitCents: 2000000, // $20,000
    onlinePaymentsEnabled: true,
    contactlessEnabled: true,
    atmWithdrawalsEnabled: true,
  },
  {
    id: 'card-credit-2',
    cardNumber: '4532148803436467',
    cardHolder: 'JOHN DOE',
    expiry: '08/29',
    cvv: '456',
    cardType: 'credit',
    isFrozen: false,
    dailySpendingLimitCents: 1500000, // $15,000
    monthlySpendingLimitCents: 5000000, // $50,000
    onlinePaymentsEnabled: true,
    contactlessEnabled: true,
    atmWithdrawalsEnabled: false,
  },
];

export default function CardSecurityHub({
  cards = DEFAULT_CARDS,
  onGenerateVirtualCard,
}: CardSecurityHubProps) {
  const [selectedCardId, setSelectedCardId] = useState<string>(cards[0]?.id || 'card-debit-1');
  const [cardStates, setCardStates] = useState<Record<string, CardDetails>>(() => {
    const map: Record<string, CardDetails> = {};
    for (const c of cards) {
      map[c.id] = { ...c };
    }
    return map;
  });

  const [notification, setNotification] = useState<string | null>(null);

  const currentCard = cardStates[selectedCardId] || cards[0];

  const updateCurrentCard = (updates: Partial<CardDetails>) => {
    setCardStates((prev) => ({
      ...prev,
      [selectedCardId]: {
        ...prev[selectedCardId],
        ...updates,
      },
    }));
    setNotification('Card security preferences updated instantly.');
    setTimeout(() => setNotification(null), 3000);
  };

  return (
    <div className="w-full space-y-8 text-white">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-widest text-purple-400">
              Security & Controls
            </span>
            <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-mono text-[10px] font-bold border border-purple-500/30">
              Zero-Liability Protection
            </span>
          </div>
          <h1 className="text-3xl lg:text-4xl font-black text-white tracking-tight mt-1">
            Card Management Hub
          </h1>
        </div>

        {/* Generate Virtual Card Button */}
        <button
          onClick={onGenerateVirtualCard}
          className="px-5 py-3 rounded-2xl bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 font-bold text-xs text-white transition-all flex items-center gap-2 shadow-lg shadow-purple-500/20 active:scale-98 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Virtual Card</span>
        </button>
      </div>

      {/* Card Switcher Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
        {cards.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelectedCardId(c.id)}
            className={`px-4 py-2.5 rounded-2xl text-xs font-bold transition-all flex items-center gap-2.5 ${
              selectedCardId === c.id
                ? 'bg-white/15 text-white border border-white/20 shadow-lg'
                : 'bg-white/[0.04] text-white/50 hover:text-white border border-white/5'
            }`}
          >
            <CreditCard className="w-4 h-4" />
            <span className="capitalize">{c.cardType || c.type || 'debit'} Card</span>
            <span className="font-mono text-[10px] text-white/40">•••• {(c.cardNumber || c.number || '0000').slice(-4)}</span>
          </button>
        ))}
      </div>

      {/* Notification banner */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{notification}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Grid: Card Preview on Left, Security Controls on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: 3D Digital Card Preview */}
        <div className="lg:col-span-5 min-h-[280px]">
          <DigitalCardPreview
            cardNumber={currentCard.cardNumber}
            cardHolder={currentCard.cardHolder}
            expiry={currentCard.expiry}
            cvv={currentCard.cvv}
            cardType={currentCard.cardType}
            isFrozenInitial={currentCard.isFrozen}
            onToggleFreeze={(frozen) => updateCurrentCard({ isFrozen: frozen })}
          />
        </div>

        {/* Right: Security & Spending Controls */}
        <div className="lg:col-span-7 space-y-6">
          {/* Spending Limit Sliders */}
          <div className="p-6 sm:p-7 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-300 flex items-center justify-center">
                  <Sliders className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold text-white">Dynamic Spending Limits</h3>
              </div>
              <span className="text-xs text-white/40 font-mono">Live Adjustment</span>
            </div>

            {/* Daily Limit */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-white/60 font-semibold">Daily Purchase Limit</span>
                <span className="font-mono font-bold text-purple-300 text-sm">
                  {formatCurrency((currentCard.dailySpendingLimitCents || 500000) / 100)}
                </span>
              </div>
              <input
                type="range"
                min={50000}
                max={2500000}
                step={50000}
                value={currentCard.dailySpendingLimitCents || 500000}
                onChange={(e) =>
                  updateCurrentCard({ dailySpendingLimitCents: parseInt(e.target.value) })
                }
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div className="flex justify-between text-[10px] text-white/30 font-mono">
                <span>$500</span>
                <span>$25,000 max</span>
              </div>
            </div>

            {/* Monthly Limit */}
            <div className="space-y-2 pt-2 border-t border-white/5">
              <div className="flex justify-between items-center text-xs">
                <span className="text-white/60 font-semibold">Monthly Purchase Limit</span>
                <span className="font-mono font-bold text-indigo-300 text-sm">
                  {formatCurrency((currentCard.monthlySpendingLimitCents || 2000000) / 100)}
                </span>
              </div>
              <input
                type="range"
                min={100000}
                max={10000000}
                step={100000}
                value={currentCard.monthlySpendingLimitCents || 2000000}
                onChange={(e) =>
                  updateCurrentCard({ monthlySpendingLimitCents: parseInt(e.target.value) })
                }
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] text-white/30 font-mono">
                <span>$1,000</span>
                <span>$100,000 max</span>
              </div>
            </div>
          </div>

          {/* Security Switches Bento */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Online Transactions */}
            <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-white block">Online Purchases</span>
                  <span className="text-[10px] text-white/40 block">E-Commerce & Subscriptions</span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={currentCard.onlinePaymentsEnabled}
                onChange={(e) =>
                  updateCurrentCard({ onlinePaymentsEnabled: e.target.checked })
                }
                className="w-5 h-5 rounded-md accent-purple-500 cursor-pointer"
              />
            </div>

            {/* Contactless & Apple Pay */}
            <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Smartphone className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-white block">Apple Pay & NFC</span>
                  <span className="text-[10px] text-white/40 block">Contactless POS Terminals</span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={currentCard.contactlessEnabled}
                onChange={(e) =>
                  updateCurrentCard({ contactlessEnabled: e.target.checked })
                }
                className="w-5 h-5 rounded-md accent-purple-500 cursor-pointer"
              />
            </div>

            {/* ATM Cash Withdrawals */}
            <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <DollarSign className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-white block">ATM Withdrawals</span>
                  <span className="text-[10px] text-white/40 block">Physical Cash Machines</span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={currentCard.atmWithdrawalsEnabled}
                onChange={(e) =>
                  updateCurrentCard({ atmWithdrawalsEnabled: e.target.checked })
                }
                className="w-5 h-5 rounded-md accent-purple-500 cursor-pointer"
              />
            </div>

            {/* Instant Freeze */}
            <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    currentCard.isFrozen
                      ? 'bg-rose-500/20 text-rose-400'
                      : 'bg-indigo-500/20 text-indigo-400'
                  }`}
                >
                  {currentCard.isFrozen ? <Lock className="w-5 h-5" /> : <Unlock className="w-5 h-5" />}
                </div>
                <div>
                  <span className="text-xs font-bold text-white block">Freeze Card</span>
                  <span className="text-[10px] text-white/40 block">Temporarily Lock Card</span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={currentCard.isFrozen}
                onChange={(e) => updateCurrentCard({ isFrozen: e.target.checked })}
                className="w-5 h-5 rounded-md accent-rose-500 cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
