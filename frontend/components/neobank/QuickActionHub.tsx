'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Send, ArrowDownLeft, FileText, Lock, Plus } from 'lucide-react';
import FastPayCarousel from './FastPayCarousel';
import { FastPayPayee } from '@/lib/neobank/types';

interface QuickActionHubProps {
  onSendClick?: () => void;
  onDepositClick?: () => void;
  onPayBillsClick?: () => void;
  onCardControlsClick?: () => void;
  onSelectPayee?: (payee: FastPayPayee) => void;
}

export default function QuickActionHub({
  onSendClick,
  onDepositClick,
  onPayBillsClick,
  onCardControlsClick,
  onSelectPayee,
}: QuickActionHubProps) {
  const actions = [
    {
      id: 'send',
      label: 'Send Money',
      sublabel: 'FedNow & Wire',
      icon: Send,
      gradient: 'from-purple-500 to-indigo-600',
      shadow: 'shadow-purple-500/20',
      border: 'hover:border-purple-400/50',
      onClick: onSendClick,
    },
    {
      id: 'deposit',
      label: 'Add Funds',
      sublabel: 'Direct Deposit',
      icon: ArrowDownLeft,
      gradient: 'from-emerald-500 to-teal-600',
      shadow: 'shadow-emerald-500/20',
      border: 'hover:border-emerald-400/50',
      onClick: onDepositClick,
    },
    {
      id: 'bills',
      label: 'Pay Bills',
      sublabel: 'Utilities & Cards',
      icon: FileText,
      gradient: 'from-blue-500 to-indigo-600',
      shadow: 'shadow-blue-500/20',
      border: 'hover:border-blue-400/50',
      onClick: onPayBillsClick,
    },
    {
      id: 'cards',
      label: 'Card Controls',
      sublabel: 'Limits & Freeze',
      icon: Lock,
      gradient: 'from-indigo-600 to-purple-700',
      shadow: 'shadow-indigo-500/20',
      border: 'hover:border-indigo-400/50',
      onClick: onCardControlsClick,
    },
  ];

  return (
    <div className="w-full space-y-6">
      {/* 4 Main Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <motion.button
              key={action.id}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={action.onClick}
              className={`p-4 rounded-3xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] ${action.border} backdrop-blur-xl transition-all flex flex-col items-start justify-between gap-3 shadow-xl group text-left`}
            >
              <div
                className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${action.gradient} ${action.shadow} flex items-center justify-center text-white shadow-lg group-hover:scale-105 transition-transform`}
              >
                <Icon className="w-5 h-5" />
              </div>

              <div>
                <span className="text-sm font-bold text-white block group-hover:text-purple-200 transition-colors">
                  {action.label}
                </span>
                <span className="text-[11px] font-medium text-white/40 block mt-0.5">
                  {action.sublabel}
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Fast Pay Avatars Carousel */}
      <FastPayCarousel
        onSelectPayee={(payee) => {
          if (onSelectPayee) onSelectPayee(payee);
          else if (onSendClick) onSendClick();
        }}
        onAddPayeeClick={onSendClick}
      />
    </div>
  );
}
