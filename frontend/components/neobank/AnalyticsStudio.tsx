'use client';

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  PieChart as PieIcon,
  BarChart3,
  Calendar,
  Zap,
  Landmark,
  Clock,
  CreditCard,
  Building2,
  Sparkles,
  ArrowUpRight,
  Filter,
} from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import {
  formatFedRailBadge,
  formatMerchantName,
  filterTransactionsByTimeRange,
  generateChartBuckets,
  TimeRange,
} from '@/lib/neobank/utils';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

interface AnalyticsStudioProps {
  transactions: any[];
  loading?: boolean;
}

export default function AnalyticsStudio({ transactions = [], loading = false }: AnalyticsStudioProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Filter transactions dynamically based on selected timeRange
  const filteredTransactions = useMemo(() => {
    return filterTransactionsByTimeRange(transactions, timeRange);
  }, [transactions, timeRange]);

  // Compute metrics from filtered transactions
  const metrics = useMemo(() => {
    let totalInflow = 0;
    let totalOutflow = 0;
    const categoryMap: Record<string, number> = {};
    const merchantMap: Record<string, number> = {};
    const railMap: Record<string, number> = {
      fednow: 0,
      wire: 0,
      ach: 0,
      internal: 0,
    };

    for (const tx of filteredTransactions) {
      const amt = typeof tx.amount === 'number' ? tx.amount : 0;
      if (amt > 0) {
        totalInflow += amt;
      } else {
        const absAmt = Math.abs(amt);
        totalOutflow += absAmt;

        const cat = tx.category || 'General Spending';
        categoryMap[cat] = (categoryMap[cat] || 0) + absAmt;

        const rawMerchant = tx.merchant || tx.counterparty || tx.recipient_email || 'Merchant';
        const brand = formatMerchantName(rawMerchant);
        merchantMap[brand] = (merchantMap[brand] || 0) + absAmt;

        const rail = (tx.transaction_type || tx.event_type || 'internal').toLowerCase();
        if (rail.includes('now')) railMap.fednow = (railMap.fednow || 0) + absAmt;
        else if (rail.includes('wire')) railMap.wire = (railMap.wire || 0) + absAmt;
        else if (rail.includes('ach')) railMap.ach = (railMap.ach || 0) + absAmt;
        else railMap.internal = (railMap.internal || 0) + absAmt;
      }
    }

    const netFlow = totalInflow - totalOutflow;
    const savingsRate = totalInflow > 0 ? Math.max(0, Math.round((netFlow / totalInflow) * 100)) : 0;

    const topCategories = Object.entries(categoryMap)
      .map(([name, amount]) => ({
        name,
        amount,
        percent: totalOutflow > 0 ? Math.round((amount / totalOutflow) * 100) : 0,
      }))
      .sort((a, b) => b.amount - a.amount);

    const topMerchants = Object.entries(merchantMap)
      .map(([name, amount]) => ({
        name,
        amount,
        percent: totalOutflow > 0 ? Math.round((amount / totalOutflow) * 100) : 0,
      }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 5);

    // Interval-based dynamic chart points
    const chartData = generateChartBuckets(filteredTransactions, timeRange);

    return {
      totalInflow,
      totalOutflow,
      netFlow,
      savingsRate,
      topCategories,
      topMerchants,
      railMap,
      chartData,
    };
  }, [filteredTransactions, timeRange]);

  return (
    <div className="w-full space-y-8 text-white">
      {/* Header & Range Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-widest text-purple-400">
              Telemetry & Insights
            </span>
            <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-mono text-[10px] font-bold border border-purple-500/30">
              ClickHouse Stream
            </span>
          </div>
          <h1 className="text-3xl lg:text-4xl font-black text-white tracking-tight mt-1">
            Analytics Studio
          </h1>
        </div>

        {/* Range Pill Selector */}
        <div className="flex items-center gap-1.5 p-1 bg-white/[0.04] backdrop-blur-xl rounded-2xl border border-white/10 self-start md:self-auto">
          {(['24h', '7d', '30d', '90d', '1y'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold font-mono transition-all ${
                timeRange === r
                  ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/20'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Summary KPI Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Inflow */}
        <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Total Inflow</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <span className="text-2xl lg:text-3xl font-black font-mono tracking-tight text-emerald-400 block">
            +{formatCurrency(metrics.totalInflow)}
          </span>
          <span className="text-[11px] text-white/40 block">Deposits, Wires & P2P</span>
        </div>

        {/* Outflow */}
        <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Total Outflow</span>
            <div className="w-8 h-8 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <span className="text-2xl lg:text-3xl font-black font-mono tracking-tight text-rose-400 block">
            -{formatCurrency(metrics.totalOutflow)}
          </span>
          <span className="text-[11px] text-white/40 block">Card, Bills & Transfers</span>
        </div>

        {/* Net Flow */}
        <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Net Cashflow</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <span
            className={`text-2xl lg:text-3xl font-black font-mono tracking-tight block ${
              metrics.netFlow >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {metrics.netFlow >= 0 ? `+${formatCurrency(metrics.netFlow)}` : `-${formatCurrency(Math.abs(metrics.netFlow))}`}
          </span>
          <span className="text-[11px] text-white/40 block">Retained Liquidity</span>
        </div>

        {/* Savings Rate */}
        <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Savings Rate</span>
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <span className="text-2xl lg:text-3xl font-black font-mono tracking-tight text-purple-300 block">
            {metrics.savingsRate}%
          </span>
          <span className="text-[11px] text-white/40 block">Goal Progress Benchmark</span>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Area Chart (2 cols) */}
        <div className="lg:col-span-2 p-6 sm:p-8 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-white">Daily Cashflow Trend</h3>
              <p className="text-xs text-white/40">Real-time settlement activity over time</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-purple-400 font-semibold">
              <div className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span>Volume ($)</span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics.chartData}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} />
                <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(5,5,16,0.9)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '16px',
                    color: '#fff',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorVolume)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Federal Reserve Settlement Rails Breakdown (1 col) */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-6">
          <div>
            <h3 className="text-lg font-bold text-white">Settlement Rail Volumes</h3>
            <p className="text-xs text-white/40">Distribution across US interbank networks</p>
          </div>

          <div className="space-y-4">
            {/* FedNow */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5" />
                  <span>FedNow 24/7 (Instant)</span>
                </span>
                <span className="font-mono text-white/90">{formatCurrency(metrics.railMap.fednow)}</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-emerald-400 rounded-full"
                  style={{
                    width: `${
                      metrics.totalOutflow > 0 ? (metrics.railMap.fednow / metrics.totalOutflow) * 100 : 35
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* Fedwire */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-indigo-400 flex items-center gap-1.5">
                  <Landmark className="w-3.5 h-3.5" />
                  <span>Fedwire RTGS</span>
                </span>
                <span className="font-mono text-white/90">{formatCurrency(metrics.railMap.wire)}</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-indigo-400 rounded-full"
                  style={{
                    width: `${
                      metrics.totalOutflow > 0 ? (metrics.railMap.wire / metrics.totalOutflow) * 100 : 45
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* FedACH */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-amber-400 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  <span>FedACH Direct</span>
                </span>
                <span className="font-mono text-white/90">{formatCurrency(metrics.railMap.ach)}</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full"
                  style={{
                    width: `${
                      metrics.totalOutflow > 0 ? (metrics.railMap.ach / metrics.totalOutflow) * 100 : 20
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 text-xs text-white/50 space-y-1">
            <span className="font-bold text-white/70 block">⚡ Real-Time Clearance</span>
            <p>94% of transfers settle in &lt;3 seconds via FedNow and RTGS lines.</p>
          </div>
        </div>
      </div>

      {/* Categories & Merchant Leaderboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Categories */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-5">
          <h3 className="text-lg font-bold text-white">Top Spending Categories</h3>

          <div className="space-y-3.5">
            {metrics.topCategories.slice(0, 5).map((cat) => (
              <div key={cat.name} className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-white/80">{cat.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-white/90">{formatCurrency(cat.amount)}</span>
                    <span className="text-[10px] text-white/40 font-mono">({cat.percent}%)</span>
                  </div>
                </div>
                <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                    style={{ width: `${cat.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Merchants */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-xl space-y-5">
          <h3 className="text-lg font-bold text-white">Top Payees & Merchants</h3>

          <div className="space-y-3">
            {metrics.topMerchants.map((m, idx) => (
              <div
                key={m.name}
                className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/5 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-300 flex items-center justify-center font-mono font-bold text-xs">
                    #{idx + 1}
                  </div>
                  <div>
                    <span className="text-xs font-bold text-white block">{m.name}</span>
                    <span className="text-[10px] text-white/40">{m.percent}% of total spend</span>
                  </div>
                </div>

                <span className="text-xs font-bold font-mono text-white">
                  {formatCurrency(m.amount)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
