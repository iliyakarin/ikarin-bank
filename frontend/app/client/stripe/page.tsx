"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Zap, CheckCircle2, X } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

interface CardDetails {
    card_number: string;
    exp_month: string;
    exp_year: string;
    cvc: string;
    name: string;
}

interface StripeCardResponse {
    last4: string;
    brand: string;
}

interface PaymentMethodResponse {
    id: string;
    object: string;
    type: string;
    card: StripeCardResponse;
}

interface PaymentIntentResponse {
    id: string;
    object: string;
    amount: number;
    currency: string;
    status: string;
    client_secret: string;
}

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
    const [intentId, setIntentId] = useState<string | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [amountCents, setAmountCents] = useState(0);
    const [customAmount, setCustomAmount] = useState("");

    const [cardDetails, setCardDetails] = useState<CardDetails>({
        card_number: "",
        exp_month: "",
        exp_year: "",
        cvc: "",
        name: ""
    });

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
            const response = await fetch("/api/v1/stripe/payment_intents", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ amount, currency: "usd" })
            });

            if (!response.ok) throw new Error("Failed to create intent");
            const data = await response.json() as PaymentIntentResponse;
            setIntentId(data.id);
            setShowModal(true);
        } catch (e) {
            console.error(e);
            alert("Failed to initialize remote checkout");
        } finally {
            setLoading(null);
        }
    };

    const handleMockPayment = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading("confirming");
        try {
            // 1. Create Payment Method
            const pmRes = await fetch("/api/v1/stripe/payment_methods", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(cardDetails)
            });
            if (!pmRes.ok) throw new Error("Failed to create payment method");
            const pmData = await pmRes.json() as PaymentMethodResponse;

            // 2. Confirm Intent
            const confirmRes = await fetch(`/api/v1/stripe/payment_intents/${intentId}/confirm`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "Idempotency-Key": (crypto.randomUUID && crypto.randomUUID()) || `${Date.now()}-${Math.random()}`
                },
                body: JSON.stringify({ payment_method: pmData.id })
            });

            if (!confirmRes.ok) throw new Error("Failed to confirm intent");

            alert("Payment successful!");
            setShowModal(false);
            // Refresh to see new balance or redirect
            router.push("/client");

        } catch (error) {
            console.error(error);
            alert("Payment failed");
        } finally {
            setLoading(null);
        }
    };

    const handleCancelSubscription = async () => {
        if (!confirm("Are you sure you want to cancel your Karin Black subscription?")) return;
        setLoading("cancelling");
        try {
            const res = await fetch("/api/v1/stripe/subscriptions/cancel", {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                alert("Subscription cancelled successfully");
                // Refresh data
                router.refresh();
                window.location.reload();
            } else {
                const data = await res.json();
                alert(data.detail || "Failed to cancel subscription");
            }
        } catch (error) {
            console.error(error);
            alert("Error cancelling subscription");
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
                                        onClick={handleCancelSubscription}
                                        disabled={loading !== null}
                                        className="w-full bg-red-500/10 text-red-500 border border-red-500/20 px-6 py-3 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-red-500/20"
                                    >
                                        {loading === "cancelling" ? "Updating..." : "Cancel Subscription"}
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

                {showModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                        <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                            <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
                                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                                    <CreditCard className="w-5 h-5 text-indigo-500" />
                                    Complete Payment ({amountCents / 100} USD)
                                </h3>
                                <button onClick={() => setShowModal(false)} className="text-zinc-500 hover:text-white transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <form onSubmit={handleMockPayment} className="p-6 space-y-6">
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-zinc-400">Cardholder Name</label>
                                        <input
                                            required
                                            type="text"
                                            placeholder="Jane Doe"
                                            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                                            value={cardDetails.name}
                                            onChange={e => setCardDetails({ ...cardDetails, name: e.target.value })}
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-zinc-400">Card Number</label>
                                        <input
                                            required
                                            type="text"
                                            pattern="[0-9]{16}"
                                            maxLength={16}
                                            placeholder="4242 4242 4242 4242"
                                            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono tracking-widest"
                                            value={cardDetails.card_number}
                                            onChange={e => setCardDetails({ ...cardDetails, card_number: e.target.value.replace(/\D/g, '') })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-zinc-400">Month</label>
                                            <input
                                                required
                                                type="text"
                                                maxLength={2}
                                                placeholder="MM"
                                                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                                                value={cardDetails.exp_month}
                                                onChange={e => setCardDetails({ ...cardDetails, exp_month: e.target.value.replace(/\D/g, '') })}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-zinc-400">Year</label>
                                            <input
                                                required
                                                type="text"
                                                maxLength={4}
                                                placeholder="YYYY"
                                                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                                                value={cardDetails.exp_year}
                                                onChange={e => setCardDetails({ ...cardDetails, exp_year: e.target.value.replace(/\D/g, '') })}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-zinc-400">CVC</label>
                                            <input
                                                required
                                                type="text"
                                                maxLength={4}
                                                placeholder="123"
                                                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                                                value={cardDetails.cvc}
                                                onChange={e => setCardDetails({ ...cardDetails, cvc: e.target.value.replace(/\D/g, '') })}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-2">
                                    <button
                                        type="submit"
                                        disabled={loading === "confirming"}
                                        className="w-full bg-indigo-500 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.2)] flex items-center justify-center gap-2"
                                    >
                                        {loading === "confirming" ? (
                                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        ) : (
                                            `Deposit $${amountCents / 100} to Main Account`
                                        )}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

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
                                                            onClick={handleCancelSubscription}
                                                            disabled={loading !== null}
                                                            className="text-xs text-red-500 hover:text-red-400 font-medium transition-colors"
                                                        >
                                                            Cancel
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
