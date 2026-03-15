"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Wallet, Shield, ArrowRight, CreditCard, ChevronRight, Zap, CheckCircle2 } from 'lucide-react';
import { toCents, formatCurrency } from '@/lib/transactionUtils';
import { useAuth } from "@/lib/AuthContext";
import StripePaymentModal from "@/components/StripePaymentModal";

interface Transaction {
    id: string;
    amount: number;
    category: string;
    merchant?: string;
    timestamp: string;
    status?: string;
}

interface UserSubscription {
    active: boolean;
    plan_name?: string;
    amount?: number;
    current_period_end?: string;
    status?: string;
}

export default function StripePage() {
    const router = useRouter();
    const { token } = useAuth();

    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [subscription, setSubscription] = useState<UserSubscription | null>(null);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
    const [selectedAmount, setSelectedAmount] = useState(0);
    const [loading, setLoading] = useState<string | null>(null);
    const [amountCents, setAmountCents] = useState(0);
    const [customAmount, setCustomAmount] = useState("");
    const [renderCount, setRenderCount] = useState(0);
    const [txLoading, setTxLoading] = useState(true);

    useEffect(() => {
        setRenderCount(prev => prev + 1);
    }, [loading, amountCents, customAmount, transactions, subscription, isPaymentModalOpen, selectedAmount]);

    console.log("StripePage Render:", renderCount, { isPaymentModalOpen, selectedAmount });
    console.log("StripePage State Check:", { isPaymentModalOpen, selectedAmount, loading });

    useEffect(() => {
        console.log("StripePage State Update:", {
            loading,
            amountCents,
            customAmount,
            transactionsCount: transactions.length,
            isPaymentModalOpen,
            selectedAmount
        });
    }, [loading, amountCents, customAmount, transactions.length, isPaymentModalOpen, selectedAmount]);

    useEffect(() => {
        const fetchTransactions = async () => {
            if (!token) return;
            setTxLoading(true);
            try {
                const params = new URLSearchParams();
                params.set("days", "30");
                params.set("tx_type", "incoming");

                const res = await fetch(
                    `/api/v1/dashboard/transactions?${params.toString()}`,
                    {
                        headers: { Authorization: `Bearer ${token}` },
                    },
                );

                if (res.ok) {
                    const data = await res.json();
                    const txs = data.transactions || [];
                    const stripeTxs = txs.filter((t: Transaction) =>
                        t.category === "Top-up" ||
                        t.category === "Subscription" ||
                        (t.merchant && t.merchant.includes("Karin Black")) ||
                        (t.merchant && t.merchant.includes("Stripe"))
                    );
                    setTransactions(stripeTxs);
                } else {
                    console.log("Transactions fetch failed with status:", res.status);
                }
            } catch (error) {
                console.error("Failed to load transactions", error);
            } finally {
                setTxLoading(false);
            }
        };

        const fetchSubscription = async () => {
            if (!token) return;
            try {
                const res = await fetch("/api/v1/stripe/subscriptions/me", {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (res.ok) {
                    const data = await res.json();
                    setSubscription(data);
                }
            } catch (error) {
                console.error("Failed to load subscription", error);
            }
        };

        fetchTransactions();
        fetchSubscription();
    }, [token]);

    const startCheckout = async (type: string, amount: number) => {
        try {
            console.log("startCheckout called with:", { type, amount });
            if (type.startsWith("topup")) {
                console.log("TOPUP BRANCH REACHED. Setting state for modal.");
                setSelectedAmount(amount);
                setIsPaymentModalOpen(true);
                console.log("State set: isPaymentModalOpen=true, selectedAmount=", amount);
                return;
            }

            setLoading(type);
            setAmountCents(amount);
            const response = await fetch("/api/v1/stripe/create-checkout-session", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    amount,
                    currency: "usd",
                    mode: type === "subscribe" ? "subscription" : "payment",
                    success_url: `${window.location.origin}/client`,
                    cancel_url: window.location.href
                })
            });

            if (!response.ok) throw new Error("Failed to create session");
            const data = await response.json() as { id: string, url: string };

            // Redirect to Stripe Checkout
            window.location.href = data.url;
        } catch (e) {
            console.error("CRITICAL ERROR IN startCheckout:", e);
            alert("Failed to initialize checkout session. Check console for details.");
        } finally {
            setLoading(null);
        }
    };

    const handlePaymentSuccess = () => {
        setIsPaymentModalOpen(false);
        // Refresh transactions after success
        // fetchTransactions() could be pulled out if needed, but for now we'll just reload or wait for webhook
        window.location.reload();
    };

    const handleManageSubscription = async () => {
        setLoading("portal");
        try {
            const response = await fetch("/api/v1/stripe/create-portal-session", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    return_url: window.location.href
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to create portal session");
            }
            const data = await response.json() as { url: string };

            // Redirect to Stripe Customer Portal
            window.location.href = data.url;
        } catch (e) {
            console.error(e);
            alert(e instanceof Error ? e.message : "Failed to open billing portal");
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-zinc-800">
            <div className="max-w-4xl mx-auto space-y-12">
                <header className="space-y-4">
                    <h1 className="text-4xl md:text-5xl font-light tracking-tight text-zinc-100">
                        Pay with <span className="font-semibold text-white">Stripe</span>
                    </h1>
                    <p className="text-zinc-500 text-lg max-w-xl font-light">
                        Secure, encrypted, and instantaneous. Elevate your Karin Bank experience with seamless funding and premium features.
                    </p>
                </header>

                <div className="grid md:grid-cols-2 gap-6">
                    {/* Top-Up Card */}
                    <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800">
                        <div className="absolute inset-0 bg-gradient-to-br from-zinc-800/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                        <div className="relative z-10 space-y-6">
                            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800">
                                <CreditCard className="h-5 w-5 text-zinc-400" />
                            </div>
                            <div className="space-y-2">
                                <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Deposit Funds from card</h2>
                                <p className="text-zinc-500 font-light text-sm">
                                    Add liquidity to your internal ledger instantly using any major credit card.
                                </p>
                            </div>

                            <div className="pt-4 flex flex-col gap-6">
                                <div className="flex flex-wrap items-stretch gap-3">
                                    <button
                                        onClick={(e) => { e.preventDefault(); console.log("Starter Button Clicked"); startCheckout("topup_10", 1000); }}
                                        disabled={loading !== null}
                                        className="flex-1 min-w-[120px] py-3 px-4 rounded-xl font-bold transition-all flex flex-col gap-3 group bg-zinc-900 border border-zinc-800 hover:border-indigo-500/50 hover:bg-zinc-800/50"
                                    >
                                        <div className="flex items-center justify-between w-full">
                                            <div className="h-8 w-8 rounded-lg bg-zinc-950 flex items-center justify-center border border-zinc-800 group-hover:border-indigo-500/30 transition-colors">
                                                <CreditCard className="h-4 w-4 text-indigo-500" />
                                            </div>
                                            <ArrowRight className="h-4 w-4 text-zinc-700 group-hover:text-indigo-500 group-hover:translate-x-1 transition-all" />
                                        </div>
                                        <div className="text-left">
                                            <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-bold group-hover:text-zinc-400 transition-colors">Starter</div>
                                            <div className="text-base text-white tracking-tight">$10.00</div>
                                        </div>
                                    </button>

                                    <button
                                        onClick={(e) => { e.preventDefault(); console.log("Popular Button Clicked"); startCheckout("topup_100", 10000); }}
                                        disabled={loading !== null}
                                        className="flex-1 min-w-[120px] py-3 px-4 rounded-xl font-bold transition-all flex flex-col gap-3 group bg-white text-black hover:bg-zinc-200"
                                    >
                                        <div className="flex items-center justify-between w-full">
                                            <div className="h-8 w-8 rounded-lg bg-black/5 flex items-center justify-center border border-black/10">
                                                <Zap className="h-4 w-4 text-indigo-600" />
                                            </div>
                                            <ArrowRight className="h-4 w-4 text-black/30 group-hover:translate-x-1 transition-all" />
                                        </div>
                                        <div className="text-left">
                                            <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-bold">Popular</div>
                                            <div className="text-base text-black font-extrabold tracking-tight">$100.00</div>
                                        </div>
                                    </button>

                                    <button
                                        onClick={(e) => { e.preventDefault(); startCheckout("topup_250", 25000); }}
                                        disabled={loading !== null}
                                        className="flex-1 min-w-[120px] py-3 px-4 rounded-xl font-bold transition-all flex flex-col gap-3 group bg-zinc-900 border border-zinc-800 hover:border-indigo-500/50 hover:bg-zinc-800/50"
                                    >
                                        <div className="flex items-center justify-between w-full">
                                            <div className="h-8 w-8 rounded-lg bg-zinc-950 flex items-center justify-center border border-zinc-800 group-hover:border-indigo-500/30 transition-colors">
                                                <Shield className="h-4 w-4 text-indigo-400" />
                                            </div>
                                            <ArrowRight className="h-4 w-4 text-zinc-700 group-hover:text-indigo-500 group-hover:translate-x-1 transition-all" />
                                        </div>
                                        <div className="text-left">
                                            <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-bold group-hover:text-zinc-400 transition-colors">Pro</div>
                                            <div className="text-base text-white tracking-tight">$250.00</div>
                                        </div>
                                    </button>
                                </div>
                                <div className="flex items-stretch gap-3">
                                    <div className="relative flex-1">
                                        <input
                                            type="number"
                                            placeholder="Custom Amount ($)"
                                            className="w-full h-12 bg-zinc-900 border border-zinc-800 text-white px-5 rounded-xl text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all hover:bg-zinc-800/50"
                                            value={customAmount}
                                            onChange={(e) => setCustomAmount(e.target.value)}
                                            min="1"
                                        />
                                    </div>
                                    <button
                                        onClick={(e) => { e.preventDefault(); startCheckout("topup_custom", toCents(parseFloat(customAmount))); }}
                                        disabled={loading !== null || !customAmount || isNaN(parseFloat(customAmount)) || parseFloat(customAmount) <= 0}
                                        className="h-12 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2 group whitespace-nowrap active:scale-95 shadow-lg shadow-indigo-500/10"
                                    >
                                        {loading === "topup_custom" ? "..." : "Add Funds"}
                                        <ChevronRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Subscription Card */}
                    <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800">
                        <div className="absolute top-0 right-0 p-8">
                            <span className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                <Zap className="h-3 w-3" />
                                Premium
                            </span>
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                        <div className="relative z-10 space-y-6">
                            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800">
                                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                            </div>
                            <div className="space-y-2">
                                <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Karin Black</h2>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-light text-white">$49</span>
                                    <span className="text-zinc-500 text-sm">/month</span>
                                </div>
                                <p className="text-zinc-500 font-light text-sm pt-2">
                                    Unlock zero-fee transfers, priority API routing, and dedicated human support.
                                </p>
                            </div>

                            <div className="pt-4">
                                {subscription?.active ? (
                                    <button
                                        onClick={handleManageSubscription}
                                        disabled={loading !== null}
                                        className="w-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-6 py-3 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-emerald-500/20"
                                    >
                                        {loading === "portal" ? "Connecting..." : "Manage Subscription"}
                                    </button>
                                ) : (
                                    <button
                                        onClick={(e) => { e.preventDefault(); startCheckout("subscribe", 4900); }}
                                        disabled={loading !== null}
                                        className="w-full bg-emerald-500 text-emerald-950 px-6 py-3 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                                    >
                                        {loading === "subscribe" ? "Processing..." : "Upgrade to Black"}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>


                {/* Historical Transactions Table */}
                <div className="group relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-900 p-8 transition-all hover:bg-zinc-900/50 hover:border-zinc-800 mt-8">
                    <div className="absolute inset-0 bg-gradient-to-br from-zinc-800/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10 space-y-6">
                        <div className="space-y-2">
                            <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Recent Deposits</h2>
                            <p className="text-zinc-500 font-light text-sm">
                                View your latest funding transactions and subscription history.
                            </p>
                        </div>

                        {txLoading ? (
                            <div className="py-8 text-center text-zinc-500">Loading history...</div>
                        ) : transactions.length === 0 ? (
                            <div className="py-8 text-center text-zinc-500">No recent deposits found.</div>
                        ) : (
                            <div className="overflow-x-auto pt-4">
                                <table className="w-full text-sm text-left text-zinc-400">
                                    <thead className="text-xs uppercase bg-zinc-900/50 text-zinc-500 border-b border-zinc-800">
                                        <tr>
                                            <th className="px-6 py-4 font-medium">Merchant</th>
                                            <th className="px-6 py-4 font-medium">Date</th>
                                            <th className="px-6 py-4 font-medium">Status</th>
                                            <th className="px-6 py-4 font-medium text-right">Amount</th>
                                            <th className="px-6 py-4 font-medium text-center">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {transactions.map((tx) => (
                                            <tr key={tx.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors">
                                                <td className="px-6 py-4 font-medium text-zinc-300">{tx.merchant || "Stripe"}</td>
                                                <td className="px-6 py-4">
                                                    {new Date((tx.timestamp.includes("Z") ? tx.timestamp : tx.timestamp + "Z")).toLocaleDateString("en-US", {
                                                        year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                                                    })}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                        {tx.status || "Cleared"}
                                                    </span>
                                                </td>
                                                 <td className="px-6 py-4 text-right font-mono font-medium">
                                                    <span className={tx.amount > 0 ? "text-emerald-400" : "text-zinc-400"}>
                                                        {formatCurrency(tx.amount)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    {(tx.category === "Subscription" || tx.merchant === "Karin Black") && subscription?.active ? (
                                                        <button
                                                            onClick={handleManageSubscription}
                                                            disabled={loading !== null}
                                                            className="text-xs text-indigo-500 hover:text-indigo-400 font-medium transition-colors"
                                                        >
                                                            Manage
                                                        </button>
                                                    ) : (
                                                        <span className="text-xs text-zinc-600">—</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <StripePaymentModal
                isOpen={isPaymentModalOpen}
                onClose={() => setIsPaymentModalOpen(false)}
                amount={selectedAmount}
                onSuccess={handlePaymentSuccess}
            />
        </div>
    );
}
