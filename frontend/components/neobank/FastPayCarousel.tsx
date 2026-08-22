'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Plus, Zap, Landmark, Clock, Send, User } from 'lucide-react';
import { FastPayPayee } from '@/lib/neobank/types';

export const DEFAULT_FAVORITE_PAYEES: FastPayPayee[] = [
  {
    id: 'fav-1',
    name: 'David Chen',
    email: 'david.chen@example.com',
    initials: 'DC',
    avatarColor: 'from-emerald-500 to-teal-600',
    preferredRail: 'fednow',
    bankName: 'JPMorgan Chase (FedNow)',
    routingNumber: '021000021',
  },
  {
    id: 'fav-2',
    name: 'Sarah Jenkins',
    email: 'sarah.j@example.com',
    initials: 'SJ',
    avatarColor: 'from-purple-500 to-indigo-600',
    preferredRail: 'fednow',
    bankName: 'Wells Fargo (FedNow)',
    routingNumber: '121000248',
  },
  {
    id: 'fav-3',
    name: 'Vanguard Brokerage',
    email: 'settlement@vanguard.com',
    initials: 'VG',
    avatarColor: 'from-indigo-600 to-blue-700',
    preferredRail: 'wire',
    bankName: 'BNY Mellon (Fedwire RTGS)',
    routingNumber: '011000015',
  },
  {
    id: 'fav-4',
    name: 'PG&E Electric Utility',
    email: 'billing@pge.com',
    initials: 'PE',
    avatarColor: 'from-amber-500 to-orange-600',
    preferredRail: 'ach',
    bankName: 'Bank of America (FedACH)',
    routingNumber: '121000358',
  },
  {
    id: 'fav-5',
    name: 'Emily Davis',
    email: 'emily.d@karinbank.com',
    initials: 'ED',
    avatarColor: 'from-rose-500 to-pink-600',
    preferredRail: 'internal',
    bankName: 'KarinBank Internal P2P',
  },
];

interface FastPayCarouselProps {
  payees?: FastPayPayee[];
  onSelectPayee: (payee: FastPayPayee) => void;
  onAddPayeeClick?: () => void;
}

export default function FastPayCarousel({
  payees = DEFAULT_FAVORITE_PAYEES,
  onSelectPayee,
  onAddPayeeClick,
}: FastPayCarouselProps) {
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

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold uppercase tracking-wider text-white/50">
          Fast Transfers & Favorites
        </span>
        <button
          onClick={onAddPayeeClick}
          className="text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Payee</span>
        </button>
      </div>

      {/* Horizontal Avatar List */}
      <div className="flex items-center gap-4 overflow-x-auto no-scrollbar py-2 px-1">
        {/* Quick Add Button */}
        <motion.button
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          onClick={onAddPayeeClick}
          className="flex flex-col items-center gap-2 group flex-shrink-0"
        >
          <div className="w-14 h-14 rounded-2xl bg-white/[0.04] group-hover:bg-purple-500/20 border border-dashed border-white/20 group-hover:border-purple-400/50 flex items-center justify-center text-white/40 group-hover:text-purple-300 transition-all shadow-md">
            <Plus className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-medium text-white/50 group-hover:text-white transition-colors">
            Add New
          </span>
        </motion.button>

        {/* Favorite Payees */}
        {payees.map((payee) => (
          <motion.button
            key={payee.id}
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onSelectPayee(payee)}
            className="flex flex-col items-center gap-2 group flex-shrink-0"
          >
            {/* Avatar Container with Preferred Rail Badge */}
            <div className="relative">
              <div
                className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${payee.avatarColor} border border-white/20 flex items-center justify-center text-white font-bold text-base shadow-lg group-hover:shadow-purple-500/20 transition-all`}
              >
                {payee.initials}
              </div>

              {/* Little Rail Badge Indicator */}
              <div
                className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-slate-950 border border-white/20 flex items-center justify-center shadow-md"
                title={`Preferred: ${payee.preferredRail.toUpperCase()}`}
              >
                {getRailIcon(payee.preferredRail)}
              </div>
            </div>

            {/* Name label */}
            <span className="text-[11px] font-semibold text-white/80 group-hover:text-purple-300 transition-colors truncate max-w-[72px] text-center">
              {payee.name.split(' ')[0]}
            </span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
