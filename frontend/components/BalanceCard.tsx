"use client";

import { motion } from "framer-motion";
import { TrendingUp, Eye, EyeOff, Copy, Check } from "lucide-react";
import { useState, useEffect } from "react";
import { formatCurrency } from "@/lib/transactionUtils";

interface BalanceCardProps {
    balance: number;
    growth: number;
    accountNumber: string;
}

export default function BalanceCard({ balance, growth, accountNumber }: BalanceCardProps) {
    const [showFullAccount, setShowFullAccount] = useState(false);
    const [mounted, setMounted] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(accountNumber);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    useEffect(() => {
        setMounted(true);
    }, []);

    const formattedBalance = mounted
        ? formatCurrency(balance)
        : formatCurrency(balance);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="relative overflow-hidden w-full max-w-md p-8 rounded-[2rem] bg-white/10 backdrop-blur-2xl border border-white/20 shadow-2xl"
        >
            {/* Glossy overlay */}
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />

            <div className="relative z-10 flex flex-col gap-8">
                <div className="flex justify-between items-start">
                    <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium text-white/50 uppercase tracking-widest">Total Balance</span>
                        <h2 className="text-5xl font-bold text-white tracking-tight">
                            ${formattedBalance}
                        </h2>
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
                        <TrendingUp size={14} />
                        <span className="text-xs font-bold">+{growth}%</span>
                    </div>
                </div>

                <div className="flex justify-between items-end">
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] font-medium text-white/30 uppercase tracking-[0.2em]">Karin Platinum Savings</span>
                        <div className="flex items-center gap-3">
                            <span className="font-mono text-sm text-white/60">
                                {showFullAccount ? accountNumber : `**** **** **** ${accountNumber.slice(-4)}`}
                            </span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setShowFullAccount(!showFullAccount)}
                                    className="text-white/40 hover:text-white/80 transition-colors"
                                    aria-label={showFullAccount ? "Hide account number" : "Show account number"}
                                >
                                    {showFullAccount ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                                <button
                                    onClick={handleCopy}
                                    className="text-white/40 hover:text-white/80 transition-colors flex items-center gap-1"
                                    aria-label="Copy account number"
                                >
                                    {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                                    {copied && <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-tighter">Copied</span>}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="w-12 h-12 flex items-center justify-center bg-white/5 rounded-2xl border border-white/10">
                        <div className="w-6 h-6 border-2 border-white/40 rounded-lg transform rotate-12" />
                    </div>
                </div>
            </div>

            {/* Subtle corner light reflection */}
            <div className="absolute -top-10 -right-10 w-24 h-24 bg-white/10 blur-3xl rounded-full" />
        </motion.div>
    );
}
