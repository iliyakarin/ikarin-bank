'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Unlock, Zap, Shield, Smartphone } from 'lucide-react';
import { formatCardNumberMasked } from '@/lib/neobank/utils';

interface DigitalCardPreviewProps {
  cardNumber?: string;
  cardHolder?: string;
  expiry?: string;
  cvv?: string;
  cardType?: 'debit' | 'credit' | 'virtual';
  isFrozenInitial?: boolean;
  onToggleFreeze?: (frozen: boolean) => void;
}

export default function DigitalCardPreview({
  cardNumber = '5542889012234567',
  cardHolder = 'JOHN DOE',
  expiry = '12/28',
  cvv = '739',
  cardType = 'debit',
  isFrozenInitial = false,
  onToggleFreeze,
}: DigitalCardPreviewProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [isFrozen, setIsFrozen] = useState(isFrozenInitial);

  const handleToggleFreeze = () => {
    const nextState = !isFrozen;
    setIsFrozen(nextState);
    if (onToggleFreeze) onToggleFreeze(nextState);
  };

  const handleToggleDetails = () => {
    setShowDetails((prev) => !prev);
    // Auto-hide sensitive CVV after 12 seconds
    if (!showDetails) {
      setTimeout(() => setShowDetails(false), 12000);
    }
  };

  const formattedNumber = showDetails
    ? cardNumber.replace(/(\d{4})/g, '$1 ').trim()
    : formatCardNumberMasked(cardNumber);

  return (
    <div className="relative w-full h-full rounded-3xl p-7 flex flex-col justify-between overflow-hidden shadow-2xl border border-white/20 bg-gradient-to-br from-slate-900 via-indigo-950/80 to-purple-950/90 text-white group">
      {/* Holographic / Iridescent Sheen Accent */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/15 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/15 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none" />

      {/* Frozen Overlay */}
      {isFrozen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute inset-0 z-30 bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center gap-2 text-cyan-300 p-6 text-center"
        >
          <div className="w-12 h-12 rounded-full bg-cyan-500/20 border border-cyan-400/30 flex items-center justify-center">
            <Lock className="w-6 h-6 text-cyan-300" />
          </div>
          <span className="text-sm font-bold text-white uppercase tracking-wider">Card is Frozen</span>
          <p className="text-xs text-white/60 max-w-[240px]">
            All online and physical POS transactions are temporarily suspended.
          </p>
          <button
            onClick={handleToggleFreeze}
            className="mt-2 px-4 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/40 text-cyan-200 text-xs font-bold transition-all"
          >
            Unfreeze Card
          </button>
        </motion.div>
      )}

      {/* Top Card Row: Chip & Type */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* EMV Metallic Chip */}
          <div className="w-11 h-8 rounded-lg bg-gradient-to-br from-amber-200 via-yellow-400 to-amber-600 border border-yellow-300/40 shadow-md flex items-center justify-center">
            <div className="w-full h-[1px] bg-amber-700/40 my-auto" />
          </div>
          {/* Contactless symbol */}
          <span className="text-white/40 text-sm font-mono tracking-widest">))))</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-white/10 text-white/80 text-[10px] font-bold uppercase tracking-widest border border-white/10">
            KarinBank {cardType.toUpperCase()}
          </span>
          <button
            onClick={handleToggleFreeze}
            className={`p-1.5 rounded-lg border transition-all ${
              isFrozen
                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
                : 'bg-white/5 border-white/10 text-white/60 hover:text-white hover:bg-white/10'
            }`}
            title={isFrozen ? 'Unfreeze Card' : 'Freeze Card'}
          >
            {isFrozen ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Center: Card Number */}
      <div className="relative z-10 my-4 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-white/40 uppercase tracking-widest">Card Number</span>
          <button
            onClick={handleToggleDetails}
            className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 transition-colors"
          >
            {showDetails ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{showDetails ? 'Hide CVV' : 'Reveal CVV'}</span>
          </button>
        </div>
        <div className="text-2xl lg:text-3xl font-black font-mono tracking-widest text-white drop-shadow-md">
          {formattedNumber}
        </div>
      </div>

      {/* Bottom Card Row: Holder, Expiry & CVV */}
      <div className="relative z-10 flex items-end justify-between pt-2 border-t border-white/10">
        <div>
          <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">Cardholder</span>
          <span className="text-sm font-bold text-white tracking-wider block">{cardHolder}</span>
        </div>

        <div className="flex items-center gap-4">
          <div>
            <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">Expires</span>
            <span className="text-sm font-bold font-mono text-white block">{expiry}</span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">CVV</span>
            <span className="text-sm font-bold font-mono text-purple-300 block">
              {showDetails ? cvv : '•••'}
            </span>
          </div>

          {/* Apple Pay badge */}
          <div className="w-8 h-8 rounded-lg bg-black/40 border border-white/10 flex items-center justify-center text-white/60">
            <Smartphone className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
}
