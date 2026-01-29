"use client";

import { motion } from "framer-motion";
import BalanceCard from "@/components/BalanceCard";
import { ArrowUpRight, ArrowDownLeft, Plus, Wallet, ShieldCheck, Zap } from "lucide-react";

export default function DashboardPage() {
    return (
        <div className="space-y-12 pb-12">
            {/* Header section */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 overflow-hidden">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-white mb-2">
                        Good morning, <span className="text-white/40">Alex</span>
                    </h1>
                    <p className="text-white/40 font-medium">Your financial health is at its peak this month.</p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center gap-3 p-2 bg-white/5 rounded-2xl border border-white/10"
                >
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <ShieldCheck size={20} />
                    </div>
                    <div className="pr-4">
                        <p className="text-[10px] uppercase font-black text-white/30 tracking-widest">Security Status</p>
                        <p className="text-sm font-bold text-white">Advanced Protection</p>
                    </div>
                </motion.div>
            </header>

            {/* Main Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
                {/* Left Column: Balance & Quick Actions */}
                <div className="xl:col-span-5 space-y-10">
                    <BalanceCard
                        balance={12450.85}
                        growth={2.5}
                        accountNumber="5542 8890 1223 4567"
                    />

                    <div className="flex gap-4">
                        <button className="flex-1 h-16 rounded-3xl bg-white text-black font-bold flex items-center justify-center gap-3 hover:bg-white/90 transition-all active:scale-95 shadow-xl shadow-white/5">
                            <Plus size={20} />
                            <span>Add Money</span>
                        </button>
                        <button className="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-white hover:bg-white/10 transition-all active:scale-95">
                            <Zap size={20} />
                        </button>
                    </div>
                </div>

                {/* Right Column: Statistics & Activity */}
                <div className="xl:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="glass-panel p-8 rounded-[2rem] space-y-6">
                        <div className="w-10 h-10 rounded-2xl bg-primary-500/20 text-primary-400 flex items-center justify-center">
                            <ArrowUpRight size={20} />
                        </div>
                        <div>
                            <p className="text-white/40 text-sm font-medium mb-1">Monthly Spending</p>
                            <p className="text-3xl font-bold text-white">$3,120.00</p>
                        </div>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full w-2/3 bg-primary-500 rounded-full" />
                        </div>
                    </div>

                    <div className="glass-panel p-8 rounded-[2rem] space-y-6">
                        <div className="w-10 h-10 rounded-2xl bg-orange-500/20 text-orange-400 flex items-center justify-center">
                            <ArrowDownLeft size={20} />
                        </div>
                        <div>
                            <p className="text-white/40 text-sm font-medium mb-1">Total Savings</p>
                            <p className="text-3xl font-bold text-white">$8,450.12</p>
                        </div>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full w-1/3 bg-orange-500 rounded-full" />
                        </div>
                    </div>

                    <div className="md:col-span-2 glass-panel p-8 rounded-[2.5rem] space-y-8">
                        <div className="flex justify-between items-center">
                            <h3 className="text-xl font-bold text-white">Recent Movements</h3>
                            <button className="text-white/40 text-sm font-bold hover:text-white transition-colors">View All</button>
                        </div>

                        <div className="space-y-6">
                            {[
                                { name: 'Apple Inc.', category: 'Technology', amount: -199.00, icon: '🍎' },
                                { name: 'Starbucks Coffee', category: 'Food & Drinks', amount: -12.50, icon: '☕' },
                                { name: 'Monthly Salary', category: 'Income', amount: 5400.00, icon: '💼' }
                            ].map((tx, i) => (
                                <div key={i} className="flex items-center justify-between group cursor-pointer">
                                    <div className="flex items-center gap-4">
                                        <div className="w-14 h-14 rounded-3xl bg-white/5 flex items-center justify-center text-2xl border border-white/5 group-hover:border-white/20 transition-all">
                                            {tx.icon}
                                        </div>
                                        <div>
                                            <p className="font-bold text-white">{tx.name}</p>
                                            <p className="text-xs text-white/30 font-medium tracking-wide uppercase">{tx.category}</p>
                                        </div>
                                    </div>
                                    <p className={`text-lg font-mono font-bold ${tx.amount > 0 ? 'text-emerald-400' : 'text-white'}`}>
                                        {tx.amount > 0 ? '+' : ''}{tx.amount.toFixed(2)}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
