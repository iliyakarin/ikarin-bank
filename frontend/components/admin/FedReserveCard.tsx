"use client";
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Landmark, 
  Zap, 
  Layers, 
  ArrowUpRight, 
  ArrowDownLeft, 
  RefreshCw, 
  ShieldCheck, 
  Building2,
  DollarSign,
  Activity
} from 'lucide-react';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';

export default function FedReserveCard() {
  const [reserves, setReserves] = useState<any | null>(null);
  const [statement, setStatement] = useState<any | null>(null);
  const [fedStatus, setFedStatus] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchFedData = async () => {
    try {
      const token = localStorage.getItem("bank_token");
      const headers = { Authorization: `Bearer ${token}` };

      const [resReserves, resStatement, resStatus] = await Promise.allSettled([
        fetch("/api/v1/admin/fed/reserves", { headers }).then(r => r.ok ? r.json() : null),
        fetch("/api/v1/admin/fed/statement", { headers }).then(r => r.ok ? r.json() : null),
        fetch("/api/v1/admin/fed/status", { headers }).then(r => r.ok ? r.json() : null),
      ]);

      if (resReserves.status === 'fulfilled' && resReserves.value) setReserves(resReserves.value);
      if (resStatement.status === 'fulfilled' && resStatement.value) setStatement(resStatement.value);
      if (resStatus.status === 'fulfilled' && resStatus.value) setFedStatus(resStatus.value);
    } catch (e) {
      console.error("Failed to load Fed Gateway metrics", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchFedData();
    const interval = setInterval(fetchFedData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = () => {
    setRefreshing(true);
    fetchFedData();
  };

  const balanceDollars = reserves ? (reserves.balance_cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "10,000,000.00";
  const overdraftDollars = reserves ? (reserves.daylight_overdraft_limit_cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "5,000,000.00";
  const totalLiquidity = reserves ? (reserves.available_liquidity_cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "15,000,000.00";

  return (
    <Card className="bg-gradient-to-br from-zinc-950/90 via-[#0d1322]/80 to-zinc-950/90 border border-blue-500/20 backdrop-blur-xl p-6 rounded-3xl shadow-2xl relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-2xl text-blue-400 shadow-inner">
            <Landmark className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white tracking-wide">
                Federal Reserve Settlement & Master Account
              </h3>
              <Badge variant="primary" className="text-[10px] tracking-wider uppercase">
                FRB SF Node 123456780
              </Badge>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Real-time multi-rail liquidity (Fedwire RTGS • FedNow 24/7 • FedACH)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>OPERATIONAL</span>
          </div>
          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all disabled:opacity-50 flex items-center gap-1.5 text-xs font-bold"
            title="Refresh Fed Reserve Statement"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-blue-400" : ""}`} />
            <span>Sync Fed</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {/* Master Account Reserve */}
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 relative group hover:border-blue-500/30 transition-all">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
            <span className="uppercase font-semibold tracking-wider">Fed Master Account Balance</span>
            <Building2 className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-black text-white tracking-tight mt-2">
            ${balanceDollars}
          </div>
          <div className="text-[11px] text-zinc-500 mt-2 flex items-center gap-1">
            <span>Account:</span>
            <span className="font-mono text-zinc-300">FRB-123456780-01</span>
          </div>
        </div>

        {/* Available Liquidity & Overdraft */}
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 relative group hover:border-emerald-500/30 transition-all">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
            <span className="uppercase font-semibold tracking-wider">Total Available Liquidity</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-300 tracking-tight mt-2">
            ${totalLiquidity}
          </div>
          <div className="text-[11px] text-zinc-500 mt-2 flex items-center justify-between">
            <span>Daylight Overdraft Limit:</span>
            <span className="font-semibold text-zinc-300">${overdraftDollars}</span>
          </div>
        </div>

        {/* Daily Rails Activity */}
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 relative group hover:border-purple-500/30 transition-all">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
            <span className="uppercase font-semibold tracking-wider">Today's Rails Volume</span>
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-center gap-3 mt-3">
            <div className="flex-1 text-center p-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
              <div className="text-[10px] text-blue-300 font-bold uppercase">Fedwire</div>
              <div className="text-sm font-black text-white mt-0.5">
                ${statement ? ((statement.fedwire_debits_cents + statement.fedwire_credits_cents) / 100).toLocaleString('en-US') : "0"}
              </div>
            </div>
            <div className="flex-1 text-center p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <div className="text-[10px] text-emerald-300 font-bold uppercase">FedNow</div>
              <div className="text-sm font-black text-white mt-0.5">
                ${statement ? ((statement.fednow_debits_cents + statement.fednow_credits_cents) / 100).toLocaleString('en-US') : "0"}
              </div>
            </div>
            <div className="flex-1 text-center p-2 rounded-xl bg-purple-500/10 border border-purple-500/20">
              <div className="text-[10px] text-purple-300 font-bold uppercase">FedACH</div>
              <div className="text-sm font-black text-white mt-0.5">
                ${statement ? ((statement.ach_debits_cents + statement.ach_credits_cents) / 100).toLocaleString('en-US') : "0"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Daily Statement Breakdown */}
      {statement && (
        <div className="mt-5 p-3.5 bg-black/40 rounded-2xl border border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-zinc-300">Statement Date:</span>
            <span className="font-mono text-zinc-400">{statement.statement_date}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-rose-400">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>Total Outflow: ${( (statement.fedwire_debits_cents + statement.fednow_debits_cents + statement.ach_debits_cents) / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <ArrowDownLeft className="w-3.5 h-3.5" />
              <span>Total Inflow: ${( (statement.fedwire_credits_cents + statement.fednow_credits_cents + statement.ach_credits_cents) / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
