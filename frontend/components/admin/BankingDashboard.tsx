"use client";
import React from 'react';
import { motion } from 'framer-motion';
import {
  Database,
  Clock,
  DollarSign,
  TrendingUp,
  Users,
  Activity as ActivityIcon,
  ArrowUpRight,
  ArrowDownRight,
  Target
} from 'lucide-react';

interface BankingMetrics {
  totalVolume: number;
  transactionCount: number;
  totalBalance: number;
  activeUsers: number;
  avgTransactionSize: number;
  topTransactions: any[];
  hourlyVolume: any[];
  merchantStats: any[];
  userGrowth: any[];
}

interface BankingDashboardProps {
  metrics: BankingMetrics;
  loading: boolean;
}

export default function BankingDashboard({ metrics, loading }: BankingDashboardProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-white/5 rounded-3xl animate-pulse border border-white/5" />
        ))}
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const metricCards = [
    {
      label: "24h Volume",
      value: formatCurrency(metrics.totalVolume),
      change: "+12.5%",
      icon: <DollarSign className="w-6 h-6 text-purple-400" />,
      color: "from-purple-500/20 to-indigo-500/20",
      border: "border-purple-500/30",
    },
    {
      label: "Transactions",
      value: formatNumber(metrics.transactionCount),
      change: "+8.3%",
      icon: <ActivityIcon className="w-6 h-6 text-indigo-400" />,
      color: "from-indigo-500/20 to-blue-500/20",
      border: "border-indigo-500/30",
    },
    {
      label: "Total Balance",
      value: formatCurrency(metrics.totalBalance),
      change: "+5.7%",
      icon: <Database className="w-6 h-6 text-fuchsia-400" />,
      color: "from-fuchsia-500/20 to-purple-500/20",
      border: "border-fuchsia-500/30",
    },
    {
      label: "Active Users",
      value: formatNumber(metrics.activeUsers),
      change: "-2.1%",
      icon: <Users className="w-6 h-6 text-slate-400" />,
      color: "from-slate-500/20 to-slate-600/20",
      border: "border-slate-500/30",
      isNegative: true,
    }
  ];

  return (
    <div className="space-y-10">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricCards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`p-6 bg-gradient-to-br ${card.color} rounded-3xl border ${card.border} backdrop-blur-md relative overflow-hidden group`}
          >
            <div className="absolute top-0 right-0 w-24 h-24 bg-white/5 rounded-full -mr-12 -mt-12 transition-transform group-hover:scale-110" />
            <div className="relative flex items-start justify-between">
              <div>
                <p className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em] mb-2">{card.label}</p>
                <p className="text-3xl font-black text-white tracking-tighter">{card.value}</p>
                <div className={`mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-black tracking-tight border ${card.isNegative
                    ? 'text-red-400 bg-red-400/10 border-red-400/20'
                    : 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
                  }`}>
                  {card.isNegative ? <ArrowDownRight className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                  {card.change}
                </div>
              </div>
              <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center border border-white/10 group-hover:border-white/20 transition-all">
                {card.icon}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* High Value Transactions */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          className="glass-panel rounded-[2rem] p-8 space-y-6"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-white font-bold text-xl flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-indigo-400" />
              High Value Activity
            </h3>
            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black text-white/40 uppercase tracking-widest">Live Feed</span>
          </div>

          <div className="space-y-4">
            {metrics.topTransactions.slice(0, 5).map((tx, idx) => (
              <div key={idx} className="group flex items-center justify-between p-4 bg-white/5 hover:bg-white/[0.08] border border-white/5 rounded-2xl transition-all cursor-default">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-xl flex items-center justify-center border border-indigo-500/20">
                    <Target className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div>
                    <p className="text-white font-bold text-sm tracking-tight">{tx.merchant}</p>
                    <p className="text-white/30 text-[10px] font-medium uppercase tracking-widest mt-0.5">
                      {new Date(tx.created_at + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • ID: {tx.account_id}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-white font-black text-lg tracking-tighter">{formatCurrency(tx.amount)}</p>
                  <p className="text-emerald-400/60 text-[10px] font-bold tracking-widest uppercase">Verified</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Volume Heatmap */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}
          className="glass-panel rounded-[2rem] p-8 space-y-6"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-white font-bold text-xl flex items-center gap-3">
              <Clock className="w-5 h-5 text-purple-400" />
              Transaction Velocity
            </h3>
            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black text-white/40 uppercase tracking-widest">24H Window</span>
          </div>

          <div className="space-y-3">
            {metrics.hourlyVolume.slice(-8).map((hour, i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="text-white/30 font-bold text-[10px] uppercase tracking-tighter w-10">
                  {hour.hour}:00
                </span>
                <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden border border-white/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(hour.count / Math.max(...metrics.hourlyVolume.map(h => h.count))) * 100}%` }}
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
                  />
                </div>
                <span className="text-white font-black text-xs tracking-tighter w-20 text-right">
                  {formatCurrency(hour.total)}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-4">
        {[
          { label: "Avg Ticket Size", val: formatCurrency(metrics.avgTransactionSize), sub: "Last 24 hours", col: "text-indigo-400" },
          { label: "Top Merchant", val: metrics.merchantStats[0]?.merchant || 'N/A', sub: `${formatCurrency(metrics.merchantStats[0]?.total_amount || 0)} Vol`, col: "text-purple-400" },
          { label: "New Users", val: metrics.userGrowth.filter(u => new Date(u.date).toDateString() === new Date().toDateString())[0]?.count || 0, sub: "+18% Net/Growth", col: "text-fuchsia-400" },
        ].map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 + (i * 0.1) }}
            className="p-6 bg-white/5 border border-white/10 rounded-[2rem] text-center group hover:bg-white/[0.08] transition-all"
          >
            <p className="text-white/30 text-[10px] font-black uppercase tracking-[0.2em] mb-2">{m.label}</p>
            <p className="text-2xl font-black text-white tracking-tighter truncate px-2">{m.val}</p>
            <p className={`${m.col} text-[10px] font-bold uppercase tracking-widest mt-2 opacity-60`}>{m.sub}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}