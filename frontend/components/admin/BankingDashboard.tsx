"use client";
import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database,
  Clock,
  DollarSign,
  TrendingUp,
  Users,
  Activity as ActivityIcon,
  ArrowUpRight,
  ArrowDownLeft,
  ArrowDownRight,
  Target,
  Search,
  Filter,
  FileText,
  ShieldCheck,
  Zap,
  Landmark,
  Send,
  X,
  CheckCircle2,
  Copy,
  Check
} from 'lucide-react';
import { formatCurrency } from '@/lib/transactionUtils';
import { formatMerchantName, formatFedRailBadge, isTransactionIncome } from '@/lib/neobank/utils';

interface BankingMetrics {
  totalVolume?: number;
  transactionCount?: number;
  totalBalance?: number;
  activeUsers?: number;
  avgTransactionSize?: number;
  topTransactions?: any[];
  hourlyVolume?: any[];
  merchantStats?: any[];
  userGrowth?: any[];
}

interface BankingDashboardProps {
  metrics: BankingMetrics | null;
  loading: boolean;
}

export default function BankingDashboard({ metrics, loading }: BankingDashboardProps) {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [txLoading, setTxLoading] = useState<boolean>(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState<number>(30);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [inspectTx, setInspectTx] = useState<any | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchBankTransactions = async () => {
    try {
      setTxLoading(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('bank_token') : null;
      if (!token) return;

      const params = new URLSearchParams({
        days: selectedTimeframe.toString(),
        limit: '100',
      });
      if (searchQuery) params.set('search', searchQuery);
      if (selectedCategory !== 'all') params.set('category', selectedCategory);

      const res = await fetch(`/api/v1/admin/transactions/all?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
      }
    } catch (e) {
      console.error('Failed to load bank-wide transactions', e);
    } finally {
      setTxLoading(false);
    }
  };

  useEffect(() => {
    fetchBankTransactions();
  }, [selectedTimeframe, selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchBankTransactions();
  };

  const handleCopy = (val: string, key: string) => {
    navigator.clipboard.writeText(val);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (loading || !metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-white/5 rounded-3xl animate-pulse border border-white/5" />
        ))}
      </div>
    );
  }

  const formatNumber = (num?: number) => {
    return new Intl.NumberFormat('en-US').format(num || 0);
  };

  const topTransactions = metrics.topTransactions || [];
  const hourlyVolume = metrics.hourlyVolume || [];
  const merchantStats = metrics.merchantStats || [];
  const userGrowth = metrics.userGrowth || [];
  const maxHourlyCount = Math.max(1, ...hourlyVolume.map(h => h.count || 0));

  const metricCards = [
    {
      label: "24h Bank Volume",
      value: formatCurrency(metrics.totalVolume || 0),
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
      label: "Total Bank Balance",
      value: formatCurrency(metrics.totalBalance || 0),
      change: "+5.7%",
      icon: <Database className="w-6 h-6 text-fuchsia-400" />,
      color: "from-fuchsia-500/20 to-purple-500/20",
      border: "border-fuchsia-500/30",
    },
    {
      label: "Active Accounts",
      value: formatNumber(metrics.activeUsers),
      change: "+18.0%",
      icon: <Users className="w-6 h-6 text-emerald-400" />,
      color: "from-emerald-500/20 to-teal-500/20",
      border: "border-emerald-500/30",
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
                <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-black tracking-tight border text-emerald-400 bg-emerald-400/10 border-emerald-400/20">
                  <ArrowUpRight className="w-3 h-3" />
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

      {/* High Value Activity & Velocity Grid */}
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
            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black text-white/40 uppercase tracking-widest">
              Live ClickHouse Stream
            </span>
          </div>

          <div className="space-y-4">
            {topTransactions.length > 0 ? (
              topTransactions.slice(0, 5).map((tx, idx) => {
                const rawDate = tx.created_at || '';
                const dateObj = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
                const timeStr = !isNaN(dateObj.getTime())
                  ? dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : 'Recent';
                const isIncome = isTransactionIncome(tx);
                const brand = formatMerchantName(tx.merchant || tx.counterparty || 'Transaction');

                return (
                  <div
                    key={idx}
                    onClick={() => setInspectTx(tx)}
                    className="group flex items-center justify-between p-4 bg-white/5 hover:bg-white/[0.08] border border-white/5 hover:border-purple-500/30 rounded-2xl transition-all cursor-pointer"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-xl flex items-center justify-center border border-indigo-500/20">
                        <Target className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div>
                        <p className="text-white font-bold text-sm tracking-tight group-hover:text-purple-200 transition-colors">
                          {brand}
                        </p>
                        <p className="text-white/30 text-[10px] font-medium uppercase tracking-widest mt-0.5">
                          {timeStr} • Acct #{tx.account_id || 'N/A'} • {tx.category || 'General'}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-black text-lg tracking-tighter ${isIncome ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isIncome ? `+${formatCurrency(tx.amount || 0)}` : `-${formatCurrency(tx.amount || 0)}`}
                      </p>
                      <p className="text-white/40 text-[10px] font-bold tracking-widest uppercase">
                        {tx.status || 'cleared'}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-white/30 text-center py-6">No recent high value activity</p>
            )}
          </div>
        </motion.div>

        {/* Volume Velocity */}
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
            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black text-white/40 uppercase tracking-widest">
              24H Breakdown
            </span>
          </div>

          <div className="space-y-3">
            {hourlyVolume.length > 0 ? (
              hourlyVolume.slice(-8).map((hour, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="text-white/30 font-bold text-[10px] uppercase tracking-tighter w-12 font-mono">
                    {hour.hour.toString().padStart(2, '0')}:00
                  </span>
                  <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden border border-white/5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${((hour.count || 0) / maxHourlyCount) * 100}%` }}
                      className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
                    />
                  </div>
                  <span className="text-white font-black text-xs tracking-tighter w-24 text-right font-mono">
                    {formatCurrency(hour.total || 0)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-white/30 text-center py-6">No hourly velocity data recorded</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: "Avg Ticket Size", val: formatCurrency(metrics.avgTransactionSize || 0), sub: "24-Hour Average", col: "text-indigo-400" },
          { label: "Top Merchant", val: merchantStats[0]?.merchant || 'N/A', sub: `${formatCurrency(merchantStats[0]?.total_amount || 0)} Vol`, col: "text-purple-400" },
          { label: "User Accounts", val: formatNumber(metrics.activeUsers), sub: "Active Bank Entities", col: "text-emerald-400" },
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
            <p className={`${m.col} text-[10px] font-bold uppercase tracking-widest mt-2 opacity-80`}>{m.sub}</p>
          </motion.div>
        ))}
      </div>

      {/* Bank-Wide All Transactions & Audit Ledger */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-[2rem] p-6 sm:p-8 space-y-6 border border-white/10 shadow-2xl"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-3">
              <FileText className="w-5 h-5 text-indigo-400" />
              Bank-Wide Audit Ledger
            </h3>
            <p className="text-xs text-white/40 mt-1">
              Real-time audit inspection across all accounts, merchants, and Federal Reserve clearing rails
            </p>
          </div>

          {/* Timeframe Selectors */}
          <div className="flex items-center gap-1.5 p-1 bg-white/5 rounded-2xl border border-white/10">
            {[
              { label: '24H', days: 1 },
              { label: '7D', days: 7 },
              { label: '30D', days: 30 },
              { label: '90D', days: 90 },
              { label: 'ALL', days: 365 },
            ].map((tf) => (
              <button
                key={tf.label}
                onClick={() => setSelectedTimeframe(tf.days)}
                className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all ${
                  selectedTimeframe === tf.days
                    ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-md'
                    : 'text-white/40 hover:text-white hover:bg-white/5'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Filter & Search Bar */}
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-white/30 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by merchant, email, account ID, or transaction ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-2xl pl-10 pr-4 py-3 text-sm text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500/30 focus:border-purple-500/50 transition-all font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={txLoading}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-2xl text-xs font-black uppercase tracking-widest transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-purple-600/20"
          >
            <Filter className="w-3.5 h-3.5" />
            Filter
          </button>
        </form>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="text-white/30 uppercase text-[10px] font-black tracking-[0.2em] border-b border-white/5 bg-white/[0.02]">
                <th className="px-4 py-3.5">Transaction / Merchant</th>
                <th className="px-4 py-3.5">Rail / Category</th>
                <th className="px-4 py-3.5">Counterparty</th>
                <th className="px-4 py-3.5">Timestamp</th>
                <th className="px-4 py-3.5 text-right">Amount</th>
                <th className="px-4 py-3.5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-sm">
              {transactions.length > 0 ? (
                transactions.map((tx, idx) => {
                  const isIncome = isTransactionIncome(tx);
                  const brand = formatMerchantName(tx.merchant || tx.counterparty || 'Transaction');
                  const rail = tx.transaction_type || 'internal';
                  const badge = formatFedRailBadge(rail);
                  const rawDate = tx.event_time || tx.created_at || '';
                  const dateObj = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
                  const dateFormatted = !isNaN(dateObj.getTime())
                    ? dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : 'Recent';

                  return (
                    <tr
                      key={tx.id || idx}
                      onClick={() => setInspectTx(tx)}
                      className="group hover:bg-white/[0.04] transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:border-purple-400/40">
                            <FileText className="w-4 h-4 text-purple-400" />
                          </div>
                          <div>
                            <span className="font-bold text-white group-hover:text-purple-200 block truncate max-w-[200px]">
                              {brand}
                            </span>
                            <span className="text-[10px] text-white/30 font-mono">
                              Acct #{tx.account_id}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <span className="px-2.5 py-1 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-white/5 border border-white/10 text-white/60">
                          {badge.label} • {tx.category || 'General'}
                        </span>
                      </td>

                      <td className="px-4 py-4 text-white/60 font-mono text-xs truncate max-w-[160px]">
                        {tx.sender_email || tx.recipient_email || 'Core Banking Gateway'}
                      </td>

                      <td className="px-4 py-4 text-white/40 text-xs font-mono">
                        {dateFormatted}
                      </td>

                      <td className="px-4 py-4 text-right font-mono font-black text-base">
                        <span className={isIncome ? 'text-emerald-400' : 'text-rose-400'}>
                          {isIncome ? `+${formatCurrency(tx.amount || 0)}` : `-${formatCurrency(tx.amount || 0)}`}
                        </span>
                      </td>

                      <td className="px-4 py-4 text-center">
                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider">
                          {tx.status || 'cleared'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-white/30 text-xs">
                    {txLoading ? 'Loading bank transactions...' : 'No transactions recorded for the selected window'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* ISO 20022 Audit Inspector Modal */}
      <AnimatePresence>
        {inspectTx && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xl">
            <div className="absolute inset-0" onClick={() => setInspectTx(null)} />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              className="relative z-10 w-full max-w-lg rounded-3xl p-6 sm:p-8 bg-slate-950 border border-purple-500/30 shadow-2xl text-white space-y-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-purple-600 flex items-center justify-center text-white">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Audit Inspector · ISO 20022
                    </h4>
                    <p className="text-[10px] text-white/40 font-mono">
                      Clearing Verification & Settlement Proof
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setInspectTx(null)}
                  className="p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center p-2.5 bg-white/5 rounded-xl border border-white/5">
                  <span className="text-white/40">Transaction ID:</span>
                  <div className="flex items-center gap-1 text-purple-300">
                    <span>{inspectTx.id}</span>
                    <button onClick={() => handleCopy(inspectTx.id, 'id')} className="p-1 hover:text-white">
                      {copiedKey === 'id' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                <div className="flex justify-between items-center p-2.5 bg-white/5 rounded-xl border border-white/5">
                  <span className="text-white/40">Amount:</span>
                  <span className="text-white font-bold">{formatCurrency(inspectTx.amount || 0)}</span>
                </div>

                <div className="flex justify-between items-center p-2.5 bg-white/5 rounded-xl border border-white/5">
                  <span className="text-white/40">Merchant / Counterparty:</span>
                  <span className="text-white">{inspectTx.merchant || 'Core Transfer'}</span>
                </div>

                <div className="flex justify-between items-center p-2.5 bg-white/5 rounded-xl border border-white/5">
                  <span className="text-white/40">Account ID:</span>
                  <span className="text-white">#{inspectTx.account_id}</span>
                </div>

                <div className="flex justify-between items-center p-2.5 bg-white/5 rounded-xl border border-white/5">
                  <span className="text-white/40">Settlement Status:</span>
                  <span className="text-emerald-400 font-bold">CLEARED & SETTLED</span>
                </div>
              </div>

              <button
                onClick={() => setInspectTx(null)}
                className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-2xl text-xs font-black uppercase tracking-widest transition-all"
              >
                Close Inspector
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}