"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Zap, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

export default function StripePage() {
    const router = useRouter();
    const [loading, setLoading] = useState<string | null>(null);
    const { token } = useAuth();

    const startCheckout = async (type: string, amount: number) => {
        setLoading(type);
        try {
            const response = await fetch("/api/stripe/create-checkout-session", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ type, amount })
            });
            const data = await response.json();
            if (data?.url) {
                window.location.href = data.url;
            } else {
                throw new Error("No URL returned from server.");
            }
        } catch (e) {
            console.error(e);
            alert("Failed to start checkout");
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
                                    onClick={() => startCheckout("topup", 10000)}
                                    disabled={loading !== null}
                                    className="bg-zinc-900 border border-zinc-800 text-white px-6 py-2.5 rounded-full text-sm font-medium transition-all active:scale-95 disabled:opacity-50 hover:bg-zinc-800 hover:border-zinc-700"
                                >
                                    Add $100.00
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
            </div>
        </div>
    );
}
