"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Zap, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

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

    const [loading, setLoading] = useState<string | null>(null);
    const [amountCents, setAmountCents] = useState(0);
    const [customAmount, setCustomAmount] = useState("");

    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [txLoading, setTxLoading] = useState(true);
    const [subscription, setSubscription] = useState<UserSubscription | null>(null);

    useEffect(() => {
        const fetchTransactions = async () => {
            if (!token) return;
            setTxLoading(true);
            try {
                const params = new URLSearchParams();
                params.set("days", "30");
                params.set("tx_type", "incoming");

                const res = await fetch(
                    `/api/transactions?${params.toString()}`,
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
        setLoading(type);
        setAmountCents(amount);
        try {
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
            console.error(e);
            alert("Failed to initialize checkout session");
        } finally {
            setLoading(null);
        }
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
                                <h2 className="text-2xl font-medium tracking-tight text-zinc-100">Deposit Funds</h2>
                                <p className="text-zinc-500 font-light text-sm">
                                    Add liquidity to your internal ledger instantly using any major credit card.
                                </p>
                            </div>

                            <div className="pt-4 flex flex-col gap-4">
                                <div className="flex items-center gap-4">
                                    <button
                                        onClick={() => startCheckout("topup", 1000)}
                                        disabled={loading !== null}
                                        className="bg-white text-black px-6 py-2.5 rounded-full text-sm font-medium transition-transform active:scale-95 disabled:opacity-50 hover:bg-zinc-200"
                                    >
                                        {loading === "topup" ? "Connecting..." : "Add $10.00"}
                                    </button>
                                    <button
                                        onClick={() => startCheckout("topup-100", 10000)}
                                        disabled={loading !== null}
                                        className="bg-zinc-900 border border-zinc-800 text-white px-6 py-2.5 rounded-full text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-zinc-800 hover:border-zinc-700"
                                    >
                                        {loading === "topup-100" ? "Connecting..." : "Add $100.00"}
                                    </button>
                                </div>
                                <div className="flex gap-2">
                                    <input
                                        type="number"
                                        placeholder="Custom Amount ($)"
                                        className="flex-1 bg-zinc-900 border border-zinc-800 text-white px-4 py-2.5 rounded-full text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        value={customAmount}
                                        onChange={(e) => setCustomAmount(e.target.value)}
                                        min="1"
                                    />
                                    <button
                                        onClick={() => startCheckout("topup-custom", Math.round(parseFloat(customAmount) * 100))}
                                        disabled={loading !== null || !customAmount || parseFloat(customAmount) <= 0}
                                        className="bg-zinc-900 border border-zinc-800 text-white px-6 py-2.5 rounded-full text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-zinc-800 hover:border-zinc-700"
                                    >
                                        {loading === "topup-custom" ? "..." : "Add Custom"}
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
                                        onClick={() => startCheckout("subscribe", 4900)}
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
                                                        {tx.amount > 0 ? "+" : "-"}${Math.abs(tx.amount).toFixed(2)}
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
        </div>
    );
}
