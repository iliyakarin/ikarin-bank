'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Zap,
  Landmark,
  Clock,
  Send,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Building2,
  DollarSign,
} from 'lucide-react';
import { validateAbaRouting, formatFedRailBadge } from '@/lib/neobank/utils';
import { formatCurrency } from '@/lib/transactionUtils';
import { FastPayPayee } from '@/lib/neobank/types';
import {
  lookupFedRouting,
  createFedNowTransfer,
  createWireTransfer,
  createACHTransfer,
  createP2PTransfer,
} from '@/lib/api/transfers';
import { Account } from '@/lib/api/accounts';

interface SmartTransferHubProps {
  accounts: Account[];
  initialPayee?: FastPayPayee | null;
  onSuccess?: (txResult: any) => void;
  onCancel?: () => void;
}

export default function SmartTransferHub({
  accounts,
  initialPayee = null,
  onSuccess,
  onCancel,
}: SmartTransferHubProps) {
  // Step state: 1 = Recipient, 2 = Amount & Rail, 3 = Confirming/Success
  const [step, setStep] = useState<1 | 2 | 3>(initialPayee ? 2 : 1);

  // Form states
  const [searchQuery, setSearchQuery] = useState(initialPayee?.name || '');
  const [recipientRouting, setRecipientRouting] = useState(initialPayee?.routingNumber || '');
  const [recipientAccount, setRecipientAccount] = useState(initialPayee?.accountNumber || '109823481');
  const [recipientName, setRecipientName] = useState(initialPayee?.name || '');
  const [selectedSourceAccount, setSelectedSourceAccount] = useState<number>(
    accounts[0]?.id || 1
  );

  // Directory lookup state
  const [institutionName, setInstitutionName] = useState<string | null>(null);
  const [districtName, setDistrictName] = useState<string | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [routingError, setRoutingError] = useState<string | null>(null);

  // Amount & Rail selection
  const [amountStr, setAmountStr] = useState('100.00');
  const [selectedRail, setSelectedRail] = useState<'fednow' | 'wire' | 'ach' | 'internal'>(
    initialPayee?.preferredRail === 'card' ? 'fednow' : (initialPayee?.preferredRail as any) || 'fednow'
  );
  const [memo, setMemo] = useState('Payment via KarinBank');

  // Execution state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [completedTx, setCompletedTx] = useState<any | null>(null);

  // Quick Amount Chips
  const AMOUNT_CHIPS = ['25.00', '50.00', '100.00', '250.00', '500.00', '1000.00'];

  // Handle ABA live lookup
  useEffect(() => {
    const cleanRouting = recipientRouting.replace(/\D/g, '');
    if (cleanRouting.length === 9) {
      const validation = validateAbaRouting(cleanRouting);
      if (!validation.valid) {
        setRoutingError(validation.error || 'Invalid ABA Routing Number');
        setInstitutionName(null);
        return;
      }

      setRoutingError(null);
      setLookupLoading(true);

      lookupFedRouting(cleanRouting)
        .then((res) => {
          if (res.institution?.name) {
            setInstitutionName(res.institution.name);
            setDistrictName(res.district?.name || validation.district || 'Federal Reserve');
            if (res.institution.fednow_participant) {
              setSelectedRail('fednow');
            } else if (res.institution.fedwire_participant) {
              setSelectedRail('wire');
            }
          } else {
            setInstitutionName(`${validation.district} Federal Reserve District Bank`);
            setDistrictName(validation.district || 'Federal Reserve');
          }
        })
        .catch(() => {
          setInstitutionName(`${validation.district} Federal Reserve District Bank`);
          setDistrictName(validation.district || 'Federal Reserve');
        })
        .finally(() => setLookupLoading(false));
    } else {
      setInstitutionName(null);
      if (cleanRouting.length > 0 && cleanRouting.length < 9) {
        setRoutingError('Enter 9-digit ABA routing number');
      } else {
        setRoutingError(null);
      }
    }
  }, [recipientRouting]);

  // Handle Payee selection from Quick Search
  const handleSelectQuickRecipient = (name: string, routing: string, rail: 'fednow' | 'wire' | 'ach') => {
    setRecipientName(name);
    setRecipientRouting(routing);
    setSelectedRail(rail);
    setStep(2);
  };

  // Submit transfer
  const handleExecuteTransfer = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    const amountNum = parseFloat(amountStr);
    if (isNaN(amountNum) || amountNum <= 0) {
      setSubmitError('Please enter a valid transfer amount.');
      setIsSubmitting(false);
      return;
    }

    try {
      if (selectedRail === 'fednow') {
        const result = await createFedNowTransfer({
          account_id: selectedSourceAccount,
          amount: amountNum,
          creditor_routing: recipientRouting || '021000021',
          creditor_name: recipientName || 'Creditor',
          creditor_account: recipientAccount || '109823481',
          remittance_info: memo,
        });
        setCompletedTx(result);
        setStep(3);
        if (onSuccess) onSuccess(result);
      } else if (selectedRail === 'wire') {
        const result = await createWireTransfer({
          account_id: selectedSourceAccount,
          amount: amountNum,
          receiver_routing: recipientRouting || '011000015',
          receiver_name: recipientName || 'Beneficiary',
          receiver_account: recipientAccount || '109823481',
          payment_reference: memo,
        });
        setCompletedTx(result);
        setStep(3);
        if (onSuccess) onSuccess(result);
      } else if (selectedRail === 'ach') {
        const result = await createACHTransfer({
          account_id: selectedSourceAccount,
          amount: amountNum,
          receiver_routing: recipientRouting || '121000358',
          receiver_name: recipientName || 'Receiver',
          receiver_account: recipientAccount || '109823481',
          payment_description: memo,
        });
        setCompletedTx(result);
        setStep(3);
        if (onSuccess) onSuccess(result);
      } else {
        // Internal P2P
        const result = await createP2PTransfer({
          source_account_id: selectedSourceAccount,
          recipient_email: recipientName.includes('@') ? recipientName : 'recipient@example.com',
          amount: amountNum,
          commentary: memo,
        });
        setCompletedTx(result);
        setStep(3);
        if (onSuccess) onSuccess(result);
      }
    } catch (err: any) {
      setSubmitError(err.message || 'Transfer failed. Please check your balance and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const badgeInfo = formatFedRailBadge(selectedRail);

  return (
    <div className="w-full max-w-2xl mx-auto rounded-3xl p-6 sm:p-8 bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-950 border border-white/15 shadow-2xl backdrop-blur-2xl text-white relative overflow-hidden">
      {/* Ambient background light */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl -mr-24 -mt-24 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl -ml-24 -mb-24 pointer-events-none" />

      {/* Header Stepper */}
      <div className="relative z-10 flex items-center justify-between pb-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
            <Send className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">Smart Transfer Hub</h2>
            <p className="text-xs text-white/50">United States Multi-Rail Instant Settlement</p>
          </div>
        </div>

        {/* Stepper Dots */}
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full transition-all ${step >= 1 ? 'bg-purple-500' : 'bg-white/20'}`} />
          <div className={`w-2.5 h-2.5 rounded-full transition-all ${step >= 2 ? 'bg-purple-500' : 'bg-white/20'}`} />
          <div className={`w-2.5 h-2.5 rounded-full transition-all ${step >= 3 ? 'bg-emerald-400' : 'bg-white/20'}`} />
        </div>
      </div>

      {/* Step 1: Choose Recipient */}
      {step === 1 && (
        <motion.div
          key="step1"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="relative z-10 py-6 space-y-6"
        >
          {/* Universal Search / Recipient Input */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-white/60">
              Recipient Name, ABA Routing, or Email
            </label>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setRecipientName(e.target.value);
                  if (/^\d+$/.test(e.target.value)) {
                    setRecipientRouting(e.target.value);
                  }
                }}
                placeholder="Enter contact name, 9-digit ABA Routing, or email..."
                className="w-full pl-12 pr-4 py-4 rounded-2xl bg-white/[0.05] border border-white/15 focus:border-purple-500/60 focus:bg-white/[0.08] text-white text-sm outline-none transition-all placeholder:text-white/30"
              />
            </div>
          </div>

          {/* Quick Pay Pre-Sets */}
          <div className="space-y-3">
            <span className="text-xs font-semibold text-white/40 uppercase tracking-wider block">
              Suggested Verified Institutions
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() =>
                  handleSelectQuickRecipient('David Chen (JPMorgan Chase)', '021000021', 'fednow')
                }
                className="p-3.5 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-emerald-500/40 text-left transition-all flex items-center justify-between group"
              >
                <div>
                  <span className="text-sm font-bold text-white block group-hover:text-emerald-300">
                    JPMorgan Chase (FedNow)
                  </span>
                  <span className="text-xs text-white/40 font-mono">RTN: 021000021</span>
                </div>
                <div className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-[10px] font-bold border border-emerald-500/30">
                  ⚡ 24/7
                </div>
              </button>

              <button
                onClick={() =>
                  handleSelectQuickRecipient('Vanguard Brokerage (BNY Mellon)', '011000015', 'wire')
                }
                className="p-3.5 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
              >
                <div>
                  <span className="text-sm font-bold text-white block group-hover:text-indigo-300">
                    Vanguard Settlement (Fedwire)
                  </span>
                  <span className="text-xs text-white/40 font-mono">RTN: 011000015</span>
                </div>
                <div className="px-2 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 text-[10px] font-bold border border-indigo-500/30">
                  🏛️ RTGS
                </div>
              </button>
            </div>
          </div>

          {/* Continue Button */}
          <button
            onClick={() => setStep(2)}
            disabled={!recipientName && !recipientRouting}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-purple-500 to-indigo-600 font-bold text-sm text-white hover:from-purple-400 hover:to-indigo-500 active:scale-98 transition-all disabled:opacity-40 disabled:pointer-events-none flex items-center justify-center gap-2 shadow-xl shadow-purple-500/20"
          >
            <span>Proceed to Amount</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      )}

      {/* Step 2: Amount, Rail & Source Account */}
      {step === 2 && (
        <motion.div
          key="step2"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          className="relative z-10 py-6 space-y-6"
        >
          {/* Selected Recipient Summary Card */}
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-sm border border-purple-500/30">
                {recipientName ? recipientName.slice(0, 2).toUpperCase() : 'RT'}
              </div>
              <div>
                <span className="text-sm font-bold text-white block">{recipientName || 'External Payee'}</span>
                <span className="text-xs text-white/40 font-mono">
                  {recipientRouting ? `ABA: ${recipientRouting}` : 'KarinBank Direct Ledger'}
                </span>
              </div>
            </div>

            <button
              onClick={() => setStep(1)}
              className="text-xs font-semibold text-purple-400 hover:text-purple-300"
            >
              Change
            </button>
          </div>

          {/* Institution Directory Status (if ABA entered) */}
          {institutionName && (
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
              <Building2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-xs font-bold text-emerald-300 block truncate">
                  {institutionName}
                </span>
                <span className="text-[11px] text-emerald-400/70">
                  {districtName} District • FedNow & Fedwire Enabled
                </span>
              </div>
            </div>
          )}

          {/* Amount Keypad & Input */}
          <div className="space-y-3 text-center">
            <span className="text-xs font-bold uppercase tracking-wider text-white/50 block">
              Transfer Amount
            </span>

            <div className="relative inline-block mx-auto">
              <span className="text-3xl text-white/40 font-mono absolute -left-7 top-2">$</span>
              <input
                type="text"
                value={amountStr}
                onChange={(e) => setAmountStr(e.target.value)}
                className="text-4xl sm:text-5xl font-black font-mono tracking-tight bg-transparent text-center text-white outline-none border-b-2 border-purple-500/50 focus:border-purple-400 pb-2 w-56"
              />
            </div>

            {/* Quick Amount Chips */}
            <div className="flex items-center justify-center gap-2 flex-wrap pt-2">
              {AMOUNT_CHIPS.map((chip) => (
                <button
                  key={chip}
                  onClick={() => setAmountStr(chip)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
                    amountStr === chip
                      ? 'bg-purple-500 text-white shadow-md'
                      : 'bg-white/[0.05] text-white/60 hover:bg-white/10 hover:text-white border border-white/10'
                  }`}
                >
                  ${chip}
                </button>
              ))}
            </div>
          </div>

          {/* Federal Settlement Rail Selector */}
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-white/50 block">
              Select Settlement Rail
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* FedNow */}
              <button
                onClick={() => setSelectedRail('fednow')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedRail === 'fednow'
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-white shadow-lg'
                    : 'bg-white/[0.03] border-white/10 text-white/60 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-emerald-400">⚡ FedNow 24/7</span>
                  <span className="text-[10px] font-mono font-bold text-white/50">$0.00 fee</span>
                </div>
                <p className="text-[11px] text-white/60">Instant settlement in &lt;2.5s</p>
              </button>

              {/* Fedwire RTGS */}
              <button
                onClick={() => setSelectedRail('wire')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedRail === 'wire'
                    ? 'bg-indigo-500/20 border-indigo-500/50 text-white shadow-lg'
                    : 'bg-white/[0.03] border-white/10 text-white/60 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-indigo-400">🏛️ Fedwire RTGS</span>
                  <span className="text-[10px] font-mono font-bold text-white/50">$15.00 fee</span>
                </div>
                <p className="text-[11px] text-white/60">Institutional high-value clearance</p>
              </button>

              {/* FedACH Direct */}
              <button
                onClick={() => setSelectedRail('ach')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedRail === 'ach'
                    ? 'bg-amber-500/20 border-amber-500/50 text-white shadow-lg'
                    : 'bg-white/[0.03] border-white/10 text-white/60 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-amber-400">⏱️ FedACH</span>
                  <span className="text-[10px] font-mono font-bold text-white/50">$0.00 fee</span>
                </div>
                <p className="text-[11px] text-white/60">Standard direct batch (1-2 days)</p>
              </button>
            </div>
          </div>

          {/* Memo Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-white/50">Memo / Note (Optional)</label>
            <input
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="e.g. Invoice #291, Rent, Dinner"
              className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/10 focus:border-purple-500/50 text-white text-xs outline-none"
            />
          </div>

          {/* Error Banner */}
          {submitError && (
            <div className="p-3.5 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{submitError}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-5 py-4 rounded-2xl bg-white/10 hover:bg-white/15 text-white/80 font-bold text-sm transition-all"
            >
              Back
            </button>
            <button
              onClick={handleExecuteTransfer}
              disabled={isSubmitting}
              className="flex-1 py-4 rounded-2xl bg-gradient-to-r from-purple-500 to-indigo-600 font-bold text-sm text-white hover:from-purple-400 hover:to-indigo-500 active:scale-98 transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-xl shadow-purple-500/20"
            >
              {isSubmitting ? (
                <span className="animate-pulse">Authorizing & Clearing...</span>
              ) : (
                <>
                  <span>Send ${amountStr} via {badgeInfo.label}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </motion.div>
      )}

      {/* Step 3: Success Confirmation */}
      {step === 3 && (
        <motion.div
          key="step3"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative z-10 py-8 text-center space-y-6"
        >
          <div className="w-20 h-20 rounded-3xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-2xl shadow-emerald-500/20">
            <CheckCircle2 className="w-10 h-10" />
          </div>

          <div className="space-y-1">
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
              Payment Cleared & Settled
            </span>
            <h2 className="text-3xl font-black text-white font-mono">
              ${amountStr} USD
            </h2>
            <p className="text-xs text-white/60">
              Funds transferred to {recipientName} via {badgeInfo.label}
            </p>
          </div>

          {/* Reference IDs Box */}
          <div className="p-4 rounded-2xl bg-black/40 border border-white/10 text-left space-y-2 text-xs font-mono">
            <div className="flex justify-between text-white/50">
              <span>Status:</span>
              <span className="text-emerald-400 font-bold">CLEARED (ISO 20022)</span>
            </div>
            {completedTx?.imad && (
              <div className="flex justify-between text-white/70">
                <span>Fedwire IMAD:</span>
                <span className="text-white font-bold">{completedTx.imad}</span>
              </div>
            )}
            {completedTx?.end_to_end_id && (
              <div className="flex justify-between text-white/70">
                <span>End-to-End ID:</span>
                <span className="text-white font-bold">{completedTx.end_to_end_id}</span>
              </div>
            )}
            {completedTx?.trace_number && (
              <div className="flex justify-between text-white/70">
                <span>ACH Trace Number:</span>
                <span className="text-white font-bold">{completedTx.trace_number}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setStep(1);
                setSearchQuery('');
                setAmountStr('100.00');
              }}
              className="flex-1 py-3.5 rounded-2xl bg-white/10 hover:bg-white/15 text-white font-bold text-sm transition-all"
            >
              Send Another Payment
            </button>
            {onCancel && (
              <button
                onClick={onCancel}
                className="px-6 py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition-all"
              >
                Done
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
