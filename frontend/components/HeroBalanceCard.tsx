"use client";
import React from 'react';
import { ArrowUpRight, TrendingUp } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

// Mock data for sparkline
const data = [
    { value: 42000 }, { value: 43500 }, { value: 41000 }, { value: 44000 },
    { value: 45000 }, { value: 43000 }, { value: 46000 }, { value: 47500 },
    { value: 46500 }, { value: 48000 }, { value: 50000 }, { value: 49000 },
    { value: 51000 }, { value: 52500 }, { value: 51500 }, { value: 53000 },
    { value: 55000 }, { value: 54000 }, { value: 56000 }, { value: 57500 },
    { value: 57000 }, { value: 58500 }, { value: 60000 }, { value: 59000 },
    { value: 61000 }, { value: 62500 }, { value: 61500 }, { value: 63000 },
    { value: 65000 }, { value: 64230 },
];

export default function HeroBalanceCard({ balance }: { balance: number }) {
    return (
        <div className="relative overflow-hidden bg-black rounded-[2.5rem] p-8 md:p-12 text-white shadow-2xl">
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-gray-800/20 to-transparent rounded-full -mr-20 -mt-20 blur-3xl" />

            <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-8">
                <div className="space-y-4">
                    <p className="text-gray-400 font-medium flex items-center gap-2">
                        Total Balance <TrendingUp className="w-4 h-4 text-green-400" />
                    </p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-5xl md:text-7xl font-bold tracking-tighter">
                            ${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                        <span className="text-gray-400 font-semibold">USD</span>
                    </div>
                    <div className="flex items-center gap-4 pt-2">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 text-green-400 rounded-full text-sm font-semibold border border-green-500/20">
                            <ArrowUpRight className="w-4 h-4" />
                            +12.5%
                        </div>
                        <p className="text-gray-500 text-sm">vs last month</p>
                    </div>
                </div>

                {/* Sparkline */}
                <div className="w-full md:w-64 h-24">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data}>
                            <Line
                                type="monotone"
                                dataKey="value"
                                stroke="#10B981"
                                strokeWidth={3}
                                dot={false}
                                isAnimationActive={true}
                                animationDuration={2000}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                    <p className="text-center text-[10px] uppercase tracking-widest text-gray-600 font-bold mt-2">
                        30-Day Trend
                    </p>
                </div>
            </div>
        </div>
    );
}
