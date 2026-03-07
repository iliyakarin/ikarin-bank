"use client";

import { useMemo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

interface BalanceHistoryChartProps {
    history: { date: string; balance: number; daily_change: number }[];
    loading: boolean;
    error: string | null;
}

export default function BalanceHistoryChart({ history, loading, error }: BalanceHistoryChartProps) {
    const { settings } = useAuth();
    const chartData = useMemo(() => {
        if (!history || history.length === 0) return [];

        const minBalance = Math.min(...history.map(h => h.balance));
        const maxBalance = Math.max(...history.map(h => h.balance));
        const range = maxBalance - minBalance || 1;

        return history.map(h => ({
            ...h,
            normalizedHeight: ((h.balance - minBalance) / range) * 100,
        }));
    }, [history]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(settings.useEUDates ? 'en-GB' : 'en-US', { month: 'short', day: 'numeric' });
    };

    if (error) {
        return (
            <div className="glass-panel p-8 rounded-[2rem] text-center">
                <p className="text-rose-400">Failed to load balance history</p>
                <p className="text-white/40 text-sm mt-2">{error}</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="glass-panel p-8 rounded-[2rem] space-y-4">
                <div className="h-4 w-32 bg-white/10 rounded animate-pulse" />
                <div className="h-64 bg-white/5 rounded-2xl animate-pulse" />
            </div>
        );
    }

    if (!chartData || chartData.length === 0) {
        return (
            <div className="glass-panel p-8 rounded-[2rem] text-center">
                <p className="text-white/40">No balance history available</p>
            </div>
        );
    }

    const firstBalance = chartData[0]?.balance || 0;
    const lastBalance = chartData[chartData.length - 1]?.balance || 0;
    const isGrowth = lastBalance >= firstBalance;
    const growthPercent = firstBalance > 0
        ? ((lastBalance - firstBalance) / firstBalance) * 100
        : 0;

    return (
        <div className="glass-panel p-8 rounded-[2rem] space-y-6">
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">Balance Trend</h3>
                    <div className="flex items-center gap-2">
                        <span className={`flex items-center gap-1 text-sm font-bold ${isGrowth ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                            {isGrowth ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                            {Math.abs(growthPercent).toFixed(1)}%
                        </span>
                        <span className="text-white/40 text-sm">
                            over {chartData.length} days
                        </span>
                    </div>
                </div>
                <div className="text-right">
                    <p className="text-white/40 text-sm">Current Balance</p>
                    <p className="text-2xl font-bold text-white">{formatCurrency(lastBalance)}</p>
                </div>
            </div>

            {/* Chart */}
            <div className="relative h-64 bg-white/5 rounded-2xl overflow-hidden">
                {/* Grid lines */}
                <div className="absolute inset-0 flex flex-col justify-between p-4">
                    {[0, 25, 50, 75, 100].map((line) => (
                        <div key={line} className="relative w-full">
                            <div className="absolute left-0 w-full border-t border-white/5" />
                        </div>
                    ))}
                </div>

                {/* Bars */}
                <div className="absolute inset-0 flex items-end justify-between p-4 gap-1">
                    {chartData.map((data, index) => (
                        <div
                            key={index}
                            className="flex-1 group relative min-w-[20px] max-w-[60px]"
                        >
                            <div
                                className="w-full bg-gradient-to-t from-primary-600 to-primary-400 rounded-t-lg transition-all duration-300 hover:from-primary-500 hover:to-primary-300 cursor-pointer"
                                style={{ height: `${Math.max(data.normalizedHeight, 5)}%` }}
                            >
                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-black/90 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                    <div className="font-bold">{formatCurrency(data.balance)}</div>
                                    <div className="text-white/60">{formatDate(data.date)}</div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Date labels */}
            <div className="flex justify-between text-xs text-white/30">
                <span>{formatDate(chartData[0]?.date)}</span>
                <span>{formatDate(chartData[Math.floor(chartData.length / 2)]?.date)}</span>
                <span>{formatDate(chartData[chartData.length - 1]?.date)}</span>
            </div>
        </div>
    );
}
