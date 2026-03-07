"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { useBalance, useTransactions, AccountData } from "@/hooks/useDashboard";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowDownRight, ArrowUpRight, Wallet, AlertCircle, Eye, EyeOff } from "lucide-react";
import TransactionList from "@/components/TransactionList";

export default function SubAccountDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();

    const accountId = parseInt(id as string, 10);

    const { accounts, refresh: refreshBalance, loading: balanceLoading } = useBalance(true);

    const [account, setAccount] = useState<AccountData | null>(null);
    const [transactions, setTransactions] = useState([]);
    const [txLoading, setTxLoading] = useState(true);

    const [showTransfer, setShowTransfer] = useState(false);
    const [transferAmount, setTransferAmount] = useState("");
    const [transferType, setTransferType] = useState<"add" | "withdraw">("add");
    const [transferError, setTransferError] = useState("");
    const [transferLoading, setTransferLoading] = useState(false);
    const [isIdVisible, setIsIdVisible] = useState(false);

    useEffect(() => {
        if (accounts.length > 0) {
            const found = accounts.find(a => a.id === accountId);
            if (found) {
                setAccount(found);
            } else {
                // Redirect if account not found (or access denied)
                router.push("/client");
            }
        }
    }, [accounts, accountId, router]);

    useEffect(() => {
        const fetchCustomTransactions = async () => {
            setTxLoading(true);
            try {
                const authToken = token || localStorage.getItem("bank_token");
                const res = await fetch(`http://localhost:8000/transactions?account_id=${accountId}&days=30`, {
                    headers: { Authorization: `Bearer ${authToken}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setTransactions(data.transactions || []);
                }
            } catch (err) {
                console.error("Error fetching transactions", err);
            } finally {
                setTxLoading(false);
            }
        };
        if (token && accountId) fetchCustomTransactions();
    }, [token, accountId]);

    const handleTransfer = async (e: React.FormEvent) => {
        e.preventDefault();
        setTransferError("");
        const amount = parseFloat(transferAmount);
        if (!amount || amount <= 0) {
            setTransferError("Please enter a valid amount");
            return;
        }

        const mainAccount = accounts.find(a => a.is_main);
        if (!mainAccount) {
            setTransferError("Main account not found");
            return;
        }

        let payload = {
            from_account_id: transferType === "add" ? mainAccount.id : accountId,
            to_account_id: transferType === "add" ? accountId : mainAccount.id,
            amount: amount,
            commentary: transferType === "add" ? "Top Up" : "Withdrawal"
        };

        setTransferLoading(true);
        try {
            const authToken = token || localStorage.getItem('bank_token');
            const res = await fetch("http://localhost:8000/api/v1/accounts/transfer/internal", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${authToken}`
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || "Transfer failed");
            }

            setShowTransfer(false);
            setTransferAmount("");
            refreshBalance();
            // Reload txs
            const fetchTx = await fetch(`http://localhost:8000/transactions?account_id=${accountId}&days=30`, {
                headers: { Authorization: `Bearer ${authToken}` }
            });
            const txData = await fetchTx.json();
            setTransactions(txData.transactions || []);

        } catch (err: any) {
            setTransferError(err.message);
        } finally {
            setTransferLoading(false);
        }
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
        }).format(amount);
    };

    if (!account) return <div className="p-8 text-white/50">Loading account details...</div>;

    return (
        <div className="space-y-8 pb-12">
            <button
                onClick={() => router.push("/client")}
                className="flex items-center gap-2 text-white/60 hover:text-white transition-colors"
            >
                <ArrowLeft size={20} />
                Back to Dashboard
            </button>

            {/* Hero Card */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-gradient-to-br from-indigo-500/40 via-purple-500/30 to-indigo-600/40 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl relative overflow-hidden"
            >
                <div className="flex justify-between items-start relative z-10">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
                                <Wallet size={20} className="text-white" />
                            </div>
                            <p className="text-white/60 font-medium tracking-wide uppercase">{account.name}</p>
                            {account.is_main && (
                                <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold bg-emerald-500/20 text-emerald-400 rounded-full">Primary</span>
                            )}
                        </div>
                        <h1 className="text-5xl md:text-6xl font-black text-white">
                            {formatCurrency(account.balance)}
                        </h1>
                        <div className="flex items-center gap-2 mt-4 text-white/60 font-medium">
                            <span className="text-sm font-mono tracking-wider">
                                Acc ID: {isIdVisible ? account.id.toString().padStart(8, '0') : `****${account.id.toString().slice(-4).padStart(4, '0')}`}
                            </span>
                            <button
                                onClick={() => setIsIdVisible(!isIdVisible)}
                                className="p-1 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-all"
                                title={isIdVisible ? "Hide Account ID" : "Show Account ID"}
                            >
                                {isIdVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={() => { setTransferType("add"); setShowTransfer(true); }}
                            className="px-6 py-3 bg-white text-indigo-900 font-bold rounded-xl hover:bg-white/90 transition-colors flex items-center gap-2"
                        >
                            <ArrowDownRight size={18} />
                            Add Funds
                        </button>
                        {!account.is_main && (
                            <button
                                onClick={() => { setTransferType("withdraw"); setShowTransfer(true); }}
                                className="px-6 py-3 bg-white/10 border border-white/20 text-white font-bold rounded-xl hover:bg-white/20 transition-colors flex items-center gap-2"
                            >
                                <ArrowUpRight size={18} />
                                Withdraw
                            </button>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Internal Transfer Modal/Form */}
            {showTransfer && (
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-black/40 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 relative"
                >
                    <h2 className="text-2xl font-bold text-white mb-4">
                        {transferType === "add" ? `Top up ${account.name}` : `Withdraw from ${account.name}`}
                    </h2>
                    <p className="text-white/60 mb-6">
                        {transferType === "add"
                            ? "Funds will be moved from your Main Account."
                            : "Funds will be moved to your Main Account."}
                    </p>

                    <form onSubmit={handleTransfer} className="space-y-4 max-w-md">
                        <div>
                            <label className="block text-sm text-white/60 mb-1">Amount</label>
                            <div className="relative">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/50">$</span>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-8 pr-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                    value={transferAmount}
                                    onChange={(e) => setTransferAmount(e.target.value)}
                                    placeholder="0.00"
                                />
                            </div>
                        </div>

                        {transferError && (
                            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-300">
                                <AlertCircle size={16} />
                                <span className="text-sm">{transferError}</span>
                            </div>
                        )}

                        <div className="flex gap-3 pt-2">
                            <button
                                type="submit"
                                disabled={transferLoading || !transferAmount}
                                className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-3 rounded-xl transition-colors disabled:opacity-50"
                            >
                                {transferLoading ? "Processing..." : "Confirm Transfer"}
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowTransfer(false);
                                    setTransferError("");
                                    setTransferAmount("");
                                }}
                                className="px-6 bg-white/10 hover:bg-white/20 text-white font-bold py-3 rounded-xl transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </motion.div>
            )}

            {/* Specific Transaction History */}
            <div>
                <h2 className="text-2xl font-bold text-white mb-6">Account History</h2>
                <TransactionList
                    transactions={transactions}
                    loading={txLoading}
                />
            </div>

        </div>
    );
}
