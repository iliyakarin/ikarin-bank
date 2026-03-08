"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, ChevronDown, ChevronUp, Wallet, Settings, Send } from "lucide-react";
import { AccountData } from "@/hooks/useDashboard";
import { useAuth } from "@/lib/AuthContext";
import Link from "next/link";

interface SubAccountManagerProps {
    accounts: AccountData[];
    refresh: () => Promise<void>;
}

export default function SubAccountManager({ accounts, refresh }: SubAccountManagerProps) {
    const { token } = useAuth();
    const [isExpanded, setIsExpanded] = useState(false);
    const [isCreating, setIsCreating] = useState(false);
    const [newName, setNewName] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const mainAccount = accounts.find((a) => a.is_main);
    const subAccounts = accounts.filter((a) => !a.is_main);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
        }).format(amount);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newName.trim()) return;

        setLoading(true);
        setError(null);
        try {
            const authToken = token || localStorage.getItem('bank_token');
            const response = await fetch("/api/api/v1/accounts/sub", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${authToken}`,
                },
                body: JSON.stringify({ name: newName.trim() }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Failed to create sub-account");
            }

            setNewName("");
            setIsCreating(false);
            await refresh();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
            <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                        <Wallet size={24} />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white">Your Accounts</h3>
                        <p className="text-sm text-white/40">{accounts.length} Total Accounts</p>
                    </div>
                </div>
                <button className="text-white/60 hover:text-white transition-colors">
                    {isExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
                </button>
            </div>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="pt-6 space-y-4">
                            {/* Main Account */}
                            {mainAccount && (
                                <Link href={`/client/accounts/${mainAccount.id}`} className="block">
                                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between hover:bg-white/10 transition-colors">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="font-semibold text-white">{mainAccount.name}</span>
                                                <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold bg-emerald-500/20 text-emerald-400 rounded-full">Primary</span>
                                            </div>
                                            <p className="text-sm text-white/50 pt-1">Account: {mainAccount.masked_account_number || `****${mainAccount.id.toString().padStart(4, '0')}`}</p>
                                        </div>
                                        <div className="text-right flex items-center gap-4">
                                            <p className="text-lg font-bold text-white">{formatCurrency(mainAccount.balance)}</p>
                                            <ChevronDown size={16} className="-rotate-90 text-white/40 group-hover:text-white transition-colors" />
                                        </div>
                                    </div>
                                </Link>
                            )}

                            {/* Sub Accounts */}
                            {subAccounts.map((acc) => (
                                <Link key={acc.id} href={`/client/accounts/${acc.id}`} className="block">
                                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between hover:bg-white/10 transition-colors group">
                                        <div>
                                            <span className="font-semibold text-white">{acc.name}</span>
                                            <p className="text-sm text-white/50 pt-1">Account: {acc.masked_account_number || `****${acc.id.toString().padStart(4, '0')}`}</p>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <p className="text-lg font-bold text-white">{formatCurrency(acc.balance)}</p>
                                            </div>
                                            <ChevronDown size={16} className="-rotate-90 text-white/40 group-hover:text-white transition-colors" />
                                        </div>
                                    </div>
                                </Link>
                            ))}

                            {/* Create new sub-account logic */}
                            {subAccounts.length < 10 && !isCreating && (
                                <button
                                    onClick={() => setIsCreating(true)}
                                    className="w-full py-4 rounded-2xl border border-dashed border-white/20 text-white/60 flex items-center justify-center gap-2 hover:bg-white/5 hover:text-white transition-all"
                                >
                                    <Plus size={20} />
                                    <span>Create Sub-Account</span>
                                </button>
                            )}

                            {isCreating && (
                                <form onSubmit={handleCreate} className="p-4 rounded-2xl bg-black/20 border border-white/10 space-y-4">
                                    <div>
                                        <label className="block text-sm text-white/60 mb-1">Sub-Account Name (Letters, numbers, spaces)</label>
                                        <input
                                            type="text"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                            value={newName}
                                            onChange={(e) => setNewName(e.target.value)}
                                            placeholder="e.g. Vacation Fund"
                                            maxLength={30}
                                        />
                                    </div>
                                    {error && <p className="text-rose-400 text-sm">{error}</p>}
                                    <div className="flex gap-2">
                                        <button
                                            type="submit"
                                            disabled={loading || !newName.trim()}
                                            className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-2 rounded-xl transition-colors disabled:opacity-50"
                                        >
                                            {loading ? "Creating..." : "Confirm"}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setIsCreating(false);
                                                setError(null);
                                                setNewName("");
                                            }}
                                            className="flex-1 bg-white/10 hover:bg-white/20 text-white font-semibold py-2 rounded-xl transition-colors"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </form>
                            )}

                            {subAccounts.length >= 10 && (
                                <p className="text-center text-sm text-white/40">You have reached the maximum of 10 sub-accounts.</p>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
