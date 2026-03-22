"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Wallet, Shield, ArrowRight, CreditCard, ChevronRight, Zap, CheckCircle2, AlertCircle, X as XIcon } from 'lucide-react';
import { toCents, formatCurrency } from '@/lib/transactionUtils';
import { useAuth } from "@/lib/AuthContext";
import DepositModal from "@/components/DepositModal";
import { createCheckoutSession, createPortalSession, getSubscriptionStatus, UserSubscription } from "@/lib/api/deposits";
import { getAccountTransactions, Transaction } from "@/lib/api/accounts";

export default function DepositPage() {
    const { token } = useAuth();
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [subscription, setSubscription] = useState<UserSubscription | null>(null);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
    const [selectedAmount, setSelectedAmount] = useState(0);
    const [loading, setLoading] = useState<string | null>(null);
    const [txLoading, setTxLoading] = useState(true);
    const [customAmount, setCustomAmount] = useState("");
    const [toast, setToast] = useState<{ show: boolean, message: string, type: 'success' | 'error' }>({
        show: false,
        message: "",
        type: 'success'
    });

    const refreshData = useCallback(async () => {
        if (!token) return;
        setTxLoading(true);
        try {
            // We use generic transaction fetcher but filter for deposits here or in service
            const data = await getAccountTransactions(0); // 0 or specific account if needed, here we just want recent
            // Actually getRecentTransactions might be better, but DepositPage specifically looked at /api/v1/transactions
            // Let's use getAccountTransactions or add getTransactions to accounts.ts
            // For now, let's keep it simple.
            const depositTxs = data.filter((t: Transaction) =>
                t.category === "Top-up" ||
                t.category === "Subscription" ||
                (t.description && t.description.includes("Karin Black")) ||
                (t.description && t.description.includes("Gateway"))
            );
            setTransactions(depositTxs);
            
            const sub = await getSubscriptionStatus();
            setSubscription(sub);
        } catch (error) {
            console.error("Failed to load deposit data", error);
        } finally {
            setTxLoading(false);
        }
    }, [token]);

    useEffect(() => {
        refreshData();
    }, [refreshData]);

    const startCheckout = async (type: string, amount: number) => {
        try {
            if (type.startsWith("topup")) {
                setSelectedAmount(amount);
                setIsPaymentModalOpen(true);
                return;
            }

            setLoading(type);
            const data = await createCheckoutSession({
                amount,
                currency: "usd",
                mode: type === "subscribe" ? "subscription" : "payment",
                success_url: `${window.location.origin}/client`,
                cancel_url: window.location.href
            });
            window.location.href = data.url;
        } catch (e: any) {
            console.error("Checkout error:", e);
            showToast(e.message || "Failed to initialize checkout session", "error");
        } finally {
            setLoading(null);
        }
    };

    const handleManageSubscription = async () => {
        setLoading("portal");
        try {
            const data = await createPortalSession(window.location.href);
            window.location.href = data.url;
        } catch (e: any) {
            console.error(e);
            showToast(e.message || "Failed to open billing portal", "error");
        } finally {
            setLoading(null);
        }
    };

    const handlePaymentSuccess = () => {
        setIsPaymentModalOpen(false);
        showToast("Deposit successful! Your funds are now available.", "success");
        refreshData();
        window.dispatchEvent(new Event('balanceUpdate'));
    };

    const showToast = (message: string, type: 'success' | 'error') => {
        setToast({ show: true, message, type });
        setTimeout(() => setToast(prev => ({ ...prev, show: false })), 5000);
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-zinc-800 relative">
            {toast.show && (
                <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-[99999] flex items-center gap-3 px-6 py-4 rounded-xl shadow-2xl border-2 ${toast.type === 'success' ? 'bg-emerald-900 border-emerald-500 text-emerald-100' : 'bg-rose-900 border-rose-500 text-rose-100'}`}>
                    <div className="flex-1 font-bold text-center">{toast.message}</div>
                    <button onClick={() => setToast(prev => ({ ...prev, show: false }))} className="p-1 hover:bg-white/10 rounded"><XIcon size={20} /></button>
                </div>
            )}

            <div className="max-w-4xl mx-auto space-y-12">
                <header className="space-y-4">
                    <h1 className="text-4xl md:text-5xl font-light tracking-tight text-zinc-100">Deposit <span className="font-semibold text-white">Funds</span></h1>
                    <p className="text-zinc-500 text-lg max-w-xl font-light">Secure, encrypted, and instantaneous. Elevate your Karin Bank experience with seamless funding and premium features.</p>
                </header>

                <div className="grid md:grid-cols-2 gap-6">
                    <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800">
                        <div className="relative z-10 space-y-6">
                            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800"><CreditCard className="h-5 w-5 text-zinc-400" /></div>
                            <div className="space-y-2">
                                <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Deposit Funds</h2>
                                <p className="text-zinc-500 font-light text-sm">Add liquidity to your internal ledger instantly using any major credit card.</p>
                            </div>
                            <div className="pt-4 flex flex-col gap-6">
                                <div className="flex flex-wrap items-stretch gap-3">
                                    {[10, 100, 250].map((amt) => (
                                        <button key={amt} onClick={() => startCheckout(`topup_${amt}`, amt * 100)} disabled={loading !== null} className={`flex-1 min-w-[120px] py-3 px-4 rounded-xl font-bold transition-all flex flex-col gap-3 group ${amt === 100 ? "bg-white text-black hover:bg-zinc-200" : "bg-zinc-900 border border-zinc-800 hover:border-indigo-500/50 hover:bg-zinc-800/50"}`}>
                                            <div className="flex items-center justify-between w-full">
                                                <div className={`h-8 w-8 rounded-lg flex items-center justify-center border ${amt === 100 ? "bg-black/5 border-black/10" : "bg-zinc-950 border-zinc-800 group-hover:border-indigo-500/30"}`}>
                                                    {amt === 10 ? <CreditCard size={16} className="text-indigo-500" /> : amt === 100 ? <Zap size={16} className="text-indigo-600" /> : <Shield size={16} className="text-indigo-400" />}
                                                </div>
                                                <ArrowRight className={`h-4 w-4 ${amt === 100 ? "text-black/30" : "text-zinc-700 group-hover:text-indigo-500"} transition-all group-hover:translate-x-1`} />
                                            </div>
                                            <div className="text-left">
                                                <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-bold">{amt === 10 ? "Starter" : amt === 100 ? "Popular" : "Pro"}</div>
                                                <div className={`text-base tracking-tight ${amt === 100 ? "text-black font-extrabold" : "text-white"}`}>${amt}.00</div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                                <div className="flex items-stretch gap-3">
                                    <input type="number" placeholder="Custom Amount ($)" className="w-full h-12 bg-zinc-900 border border-zinc-800 text-white px-5 rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all hover:bg-zinc-800/50" value={customAmount} onChange={(e) => setCustomAmount(e.target.value)} />
                                    <button onClick={() => startCheckout("topup_custom", toCents(parseFloat(customAmount)))} disabled={loading !== null || !customAmount || isNaN(parseFloat(customAmount)) || parseFloat(customAmount) <= 0} className="h-12 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2 group active:scale-95 shadow-lg shadow-indigo-500/10">
                                        {loading === "topup_custom" ? "..." : "Add Funds"} <ChevronRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800">
                        <div className="absolute top-0 right-0 p-8">
                            <span className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><Zap size={12} /> Premium</span>
                        </div>
                        <div className="relative z-10 space-y-6">
                            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800"><CheckCircle2 className="h-5 w-5 text-emerald-500" /></div>
                            <div className="space-y-2">
                                <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Karin Black</h2>
                                <div className="flex items-baseline gap-1"><span className="text-3xl font-light text-white">$49</span><span className="text-zinc-500 text-sm">/month</span></div>
                                <p className="text-zinc-500 font-light text-sm pt-2">Unlock zero-fee transfers, priority API routing, and dedicated human support.</p>
                            </div>
                            <div className="pt-4">
                                {subscription?.active ? (
                                    <button onClick={handleManageSubscription} disabled={loading !== null} className="w-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-6 py-3 rounded-xl text-sm font-medium transition-all hover:bg-emerald-500/20 disabled:opacity-50">{loading === "portal" ? "Connecting..." : "Manage Subscription"}</button>
                                ) : (
                                    <button onClick={() => startCheckout("subscribe", 4900)} disabled={loading !== null} className="w-full bg-emerald-500 text-emerald-950 px-6 py-3 rounded-xl text-sm font-medium transition-all hover:bg-emerald-400 disabled:opacity-50 shadow-[0_0_20px_rgba(16,185,129,0.1)]">{loading === "subscribe" ? "Processing..." : "Upgrade to Black"}</button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800 mt-8">
                    <div className="relative z-10 space-y-6">
                        <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Recent Deposits</h2>
                        {txLoading ? <div className="py-8 text-center text-zinc-500">Loading history...</div> : transactions.length === 0 ? <div className="py-8 text-center text-zinc-500">No recent deposits found.</div> : (
                            <div className="overflow-x-auto pt-4">
                                <table className="w-full text-sm text-left text-zinc-400">
                                    <thead className="text-xs uppercase bg-zinc-900/50 text-zinc-500 border-b border-zinc-800">
                                        <tr><th className="px-6 py-4 font-medium">Description</th><th className="px-6 py-4 font-medium">Date</th><th className="px-6 py-4 font-medium">Status</th><th className="px-6 py-4 font-medium text-right">Amount</th></tr>
                                    </thead>
                                    <tbody>
                                        {transactions.map((tx) => (
                                            <tr key={tx.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors">
                                                <td className="px-6 py-4 font-medium text-zinc-300">{tx.description || "Gateway Payment"}</td>
                                                <td className="px-6 py-4">{new Date(tx.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}</td>
                                                <td className="px-6 py-4"><span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Success</span></td>
                                                <td className="px-6 py-4 text-right font-mono font-medium text-emerald-400">{formatCurrency(tx.amount)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <DepositModal isOpen={isPaymentModalOpen} onClose={() => setIsPaymentModalOpen(false)} amount={selectedAmount} onSuccess={handlePaymentSuccess} onError={(msg) => showToast(msg, "error")} />
        </div>
    );
}
