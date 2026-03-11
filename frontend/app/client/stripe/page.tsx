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

export default function StripePage() {
    const router = useRouter();
    const { token } = useAuth();

    const [loading, setLoading] = useState<string | null>(null);
    const [intentId, setIntentId] = useState<string | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [amountCents, setAmountCents] = useState(0);

    const [cardDetails, setCardDetails] = useState<CardDetails>({
        card_number: "",
        exp_month: "",
        exp_year: "",
        cvc: "",
        name: ""
    });

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
            router.push("/client/dashboard");

        } catch (error) {
            console.error(error);
            alert("Payment failed");
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

                            <div className="pt-4 flex items-center gap-4">
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
                                <button
                                    onClick={() => startCheckout("subscribe", 4900)}
                                    disabled={loading !== null}
                                    className="w-full bg-emerald-500 text-emerald-950 px-6 py-3 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                                >
                                    {loading === "subscribe" ? "Processing..." : "Upgrade to Black"}
                                </button>
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
                                            `Pay $${amountCents / 100}`
                                        )}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
