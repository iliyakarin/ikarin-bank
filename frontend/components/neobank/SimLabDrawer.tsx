'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap,
  X,
  Play,
  Activity,
  Terminal,
  Landmark,
  ShieldAlert,
  Server,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Database,
} from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';
import { formatCurrency } from '@/lib/transactionUtils';

interface SimLabDrawerProps {
  onScenarioInjected?: () => void;
}

export default function SimLabDrawer({ onScenarioInjected }: SimLabDrawerProps) {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isInjecting, setIsInjecting] = useState<string | null>(null);
  const [logMessages, setLogMessages] = useState<string[]>([
    'ClickHouse telemetry streaming on banking_log.transactions...',
    'Kafka broker ready: localhost:9092 [Topic: fednow_inbound]',
    'FRB Master Account #FRB-01-KARIN: $500,000,000.00 reserves',
  ]);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // STRICT ROLE GATE: Never render for regular consumer accounts
  if (user?.role !== 'admin') {
    return null;
  }

  const SCENARIOS = [
    {
      id: 'fednow-dinner',
      name: 'FedNow Instant P2P ($31.81)',
      desc: 'David Chen -> KarinBank via FedNow 24/7/365 rail',
      rail: 'fednow',
      endpoint: '/api/v1/transfers/fednow',
      payload: {
        account_id: 1,
        amount: 31.81,
        creditor_routing: '021000021',
        creditor_name: 'David Chen',
        creditor_account: '109823481',
        remittance_info: 'Dinner & Drinks Split (FedNow)',
      },
    },
    {
      id: 'fedwire-escrow',
      name: 'Fedwire RTGS Escrow ($6,504.43)',
      desc: 'Vanguard BNY Mellon Institutional Liquidity Settlement',
      rail: 'wire',
      endpoint: '/api/v1/transfers/wire',
      payload: {
        account_id: 1,
        amount: 6504.43,
        receiver_routing: '011000015',
        receiver_name: 'Vanguard BNY Mellon',
        receiver_account: '882910482',
        payment_reference: 'Vanguard Escrow Liquidity',
      },
    },
    {
      id: 'fedach-utility',
      name: 'FedACH Direct Utility Debit ($179.19)',
      desc: 'PG&E Electric Utility Direct Debit Settlement',
      rail: 'ach',
      endpoint: '/api/v1/transfers/ach',
      payload: {
        account_id: 1,
        amount: 179.19,
        receiver_routing: '121000358',
        receiver_name: 'PG&E Utility',
        receiver_account: '992019283',
        payment_description: 'Monthly Electric Bill',
      },
    },
  ];

  const handleInjectScenario = async (scenario: (typeof SCENARIOS)[0]) => {
    setIsInjecting(scenario.id);
    setStatusMsg(null);

    try {
      const res = await fetch(scenario.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('bank_token')}`,
        },
        body: JSON.stringify(scenario.payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Injection failed');
      }

      const data = await res.json();
      const refId = data.imad || data.end_to_end_id || data.trace_number || data.transaction_id || 'OK';
      const logEntry = `[${new Date().toLocaleTimeString()}] INJECTED: ${scenario.name} -> Settled (${refId})`;
      setLogMessages((prev) => [logEntry, ...prev.slice(0, 7)]);
      setStatusMsg({ type: 'success', text: `Scenario "${scenario.name}" injected & cleared!` });

      if (onScenarioInjected) {
        onScenarioInjected();
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Injection failed' });
    } finally {
      setIsInjecting(null);
    }
  };

  return (
    <>
      {/* Floating Trigger Button (Admin Only) */}
      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 px-4 py-3 rounded-2xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 font-black text-xs uppercase tracking-wider flex items-center gap-2 shadow-2xl shadow-amber-500/40 border border-amber-300/40 cursor-pointer"
        title="Open Simulator & Developer Drawer (Admin Only)"
      >
        <Zap className="w-4 h-4 fill-slate-950" />
        <span>⚡ Sim Lab</span>
      </motion.button>

      {/* Floating Slide-Over Drawer */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
            <div className="absolute inset-0" onClick={() => setIsOpen(false)} />

            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 250 }}
              className="relative z-10 w-full max-w-md h-full bg-slate-950 border-l border-white/15 p-6 sm:p-7 flex flex-col justify-between overflow-y-auto text-white shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Drawer Header */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
                      <Zap className="w-5 h-5 fill-amber-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-black uppercase tracking-wider text-amber-400">
                          Simulator Lab
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-mono font-bold">
                          ADMIN ONLY
                        </span>
                      </div>
                      <span className="text-xs text-white/50 block font-mono">
                        FRB Master Account & Telemetry
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => setIsOpen(false)}
                    className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white flex items-center justify-center"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* FRB Master Account Reserves Card */}
                <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-950/40 via-slate-900 to-slate-950 border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400/80 flex items-center gap-1.5">
                      <Landmark className="w-3.5 h-3.5" />
                      <span>Federal Reserve Master Account</span>
                    </span>
                    <span className="text-[10px] text-emerald-400 font-mono font-bold">LIVE RTGS</span>
                  </div>
                  <div className="text-2xl font-black font-mono tracking-tight text-white">
                    $500,000,000.00
                  </div>
                  <div className="flex justify-between text-[10px] text-white/40 font-mono">
                    <span>ABA: 011000015 (Boston FRB)</span>
                    <span>FedNow Active</span>
                  </div>
                </div>

                {/* Status Notice */}
                {statusMsg && (
                  <div
                    className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
                      statusMsg.type === 'success'
                        ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
                        : 'bg-rose-500/20 border-rose-500/30 text-rose-300'
                    }`}
                  >
                    {statusMsg.type === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    )}
                    <span>{statusMsg.text}</span>
                  </div>
                )}

                {/* Fast Scenario Injections */}
                <div className="space-y-2.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-white/50 block">
                    Instant Scenario Injection
                  </span>

                  {SCENARIOS.map((sc) => (
                    <button
                      key={sc.id}
                      onClick={() => handleInjectScenario(sc)}
                      disabled={isInjecting !== null}
                      className="w-full p-3.5 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-amber-400/40 text-left transition-all flex items-center justify-between group disabled:opacity-50"
                    >
                      <div className="space-y-0.5">
                        <span className="text-xs font-bold text-white block group-hover:text-amber-300">
                          {sc.name}
                        </span>
                        <span className="text-[11px] text-white/40 block">{sc.desc}</span>
                      </div>

                      <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center group-hover:scale-105 transition-transform flex-shrink-0 ml-2">
                        {isInjecting === sc.id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-3.5 h-3.5 fill-amber-300" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>

                {/* ClickHouse Telemetry Stream Terminal */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-white/50 flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5 text-purple-400" />
                      <span>ClickHouse Telemetry Stream</span>
                    </span>
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  </div>

                  <div className="p-3.5 rounded-2xl bg-black border border-white/10 font-mono text-[10px] text-emerald-400/90 space-y-1.5 max-h-48 overflow-y-auto">
                    {logMessages.map((msg, i) => (
                      <div key={i} className="leading-relaxed border-b border-white/5 pb-1">
                        &gt; {msg}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Drawer Footer */}
              <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-white/40 font-mono">
                <span>Simulator Service :8004</span>
                <span>ISO 20022 Schema</span>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
