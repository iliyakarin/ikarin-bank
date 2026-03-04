"use client";
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Database, Clock, DollarSign, TrendingUp, Users, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { DataErrorBoundary } from '@/components/ErrorBoundaryWrapper';

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
          <div key={i} className="h-32 bg-black/20 rounded-2xl animate-pulse" />
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

  return (
    <div className="space-y-8">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="p-6 bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-2xl border border-blue-500/30"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium mb-1">24h Volume</p>
              <p className="text-2xl font-bold text-white">{formatCurrency(metrics.totalVolume)}</p>
              <p className="text-green-400 text-xs mt-2 flex items-center gap-1">
                <ArrowUpRight className="w-3 h-3" />
                +12.5% from yesterday
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-500/30 rounded-xl flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 bg-gradient-to-br from-green-500/20 to-green-600/20 rounded-2xl border border-green-500/30"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium mb-1">Transactions</p>
              <p className="text-2xl font-bold text-white">{formatNumber(metrics.transactionCount)}</p>
              <p className="text-green-400 text-xs mt-2 flex items-center gap-1">
                <ArrowUpRight className="w-3 h-3" />
                +8.3% from yesterday
              </p>
            </div>
            <div className="w-12 h-12 bg-green-500/30 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-2xl border border-purple-500/30"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium mb-1">Total Balance</p>
              <p className="text-2xl font-bold text-white">{formatCurrency(metrics.totalBalance)}</p>
              <p className="text-green-400 text-xs mt-2 flex items-center gap-1">
                <ArrowUpRight className="w-3 h-3" />
                +5.7% from last week
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-500/30 rounded-xl flex items-center justify-center">
              <Database className="w-6 h-6 text-purple-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-6 bg-gradient-to-br from-orange-500/20 to-orange-600/20 rounded-2xl border border-orange-500/30"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium mb-1">Active Users</p>
              <p className="text-2xl font-bold text-white">{formatNumber(metrics.activeUsers)}</p>
              <p className="text-red-400 text-xs mt-2 flex items-center gap-1">
                <ArrowDownRight className="w-3 h-3" />
                -2.1% from yesterday
              </p>
            </div>
            <div className="w-12 h-12 bg-orange-500/30 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-orange-400" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Additional Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent High Value Transactions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="p-6 bg-black/20 rounded-2xl border border-white/10"
        >
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-yellow-400" />
            High Value Transactions
          </h3>
          <div className="space-y-3">
            {metrics.topTransactions.slice(0, 5).map((transaction, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-black/20 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-yellow-500/20 rounded-lg flex items-center justify-center text-yellow-400 text-sm font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">{transaction.merchant}</p>
                    <p className="text-white/40 text-xs">
                      {new Date(transaction.created_at + 'Z').toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-white font-bold">{formatCurrency(transaction.amount)}</p>
                  <p className="text-white/40 text-xs">ID: {transaction.account_id}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Hourly Volume Chart */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
          className="p-6 bg-black/20 rounded-2xl border border-white/10"
        >
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            24h Transaction Volume
          </h3>
          <div className="space-y-2">
            {metrics.hourlyVolume.slice(-8).map((hour, index) => (
              <div key={index} className="flex items-center gap-3">
                <span className="text-white/60 text-sm w-12">
                  {hour.hour}:00
                </span>
                <div className="flex-1 h-8 bg-black/20 rounded-lg overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg transition-all"
                    style={{ width: `${(hour.count / Math.max(...metrics.hourlyVolume.map(h => h.count))) * 100}%` }}
                  />
                </div>
                <span className="text-white text-sm font-medium w-16 text-right">
                  {formatCurrency(hour.total)}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Average Transaction Size & Merchant Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="p-6 bg-gradient-to-br from-indigo-500/20 to-indigo-600/20 rounded-2xl border border-indigo-500/30 text-center"
        >
          <h4 className="text-white/60 text-sm font-medium mb-2">Avg Transaction Size</h4>
          <p className="text-3xl font-bold text-white">{formatCurrency(metrics.avgTransactionSize)}</p>
          <p className="text-indigo-400 text-xs mt-2">Last 24 hours</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="p-6 bg-gradient-to-br from-pink-500/20 to-pink-600/20 rounded-2xl border border-pink-500/30 text-center"
        >
          <h4 className="text-white/60 text-sm font-medium mb-2">Top Merchant</h4>
          <p className="text-xl font-bold text-white truncate">
            {metrics.merchantStats[0]?.merchant || 'N/A'}
          </p>
          <p className="text-pink-400 text-xs mt-2">
            {formatCurrency(metrics.merchantStats[0]?.total_amount || 0)} volume
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="p-6 bg-gradient-to-br from-cyan-500/20 to-cyan-600/20 rounded-2xl border border-cyan-500/30 text-center"
        >
          <h4 className="text-white/60 text-sm font-medium mb-2">New Users Today</h4>
          <p className="text-3xl font-bold text-white">
            {metrics.userGrowth.filter(u =>
              new Date(u.date).toDateString() === new Date().toDateString()
            )[0]?.count || 0}
          </p>
          <p className="text-cyan-400 text-xs mt-2">+18% growth rate</p>
        </motion.div>
      </div>
    </div>
  );
}