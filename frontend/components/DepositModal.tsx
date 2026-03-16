"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle2, AlertCircle, CreditCard, Sparkles, Wand2 } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { formatCurrency } from "@/lib/transactionUtils";

// Initialize Stripe outside of component to avoid recreation
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "pk_test_mock_stripe_key_12345");

function PaymentForm({
  amount,
  clientSecret,
  onClose,
  onSuccess,
  onError,
}: {
  amount: number;
  clientSecret: string;
  onClose: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) return;

    setLoading(true);
    setErrorMessage(null);

    // requirement: Simulate "Declined" for specific sum: $999 (99900 cents)
    if (amount === 99900) {
      setTimeout(() => {
        setErrorMessage("Your card was declined. (Simulation for $999)");
        setStatus("error");
        onError("Your card was declined. (Simulation for $999)");
        setLoading(false);
      }, 1500);
      return;
    }

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/client/deposit/success`,
      },
      redirect: "if_required",
    });

    if (error) {
      setErrorMessage(error.message || "An unexpected error occurred.");
      setStatus("error");
      onError(error.message || "Payment failed");
    } else {
      setStatus("success");
      setTimeout(() => {
        onSuccess();
      }, 2000);
    }
    setLoading(false);
  };

  const handleAutofill = () => {
    // In a real Payment Element, we can't programmatically fill the iframe fields for security.
    // However, we can provide a UI hint or pre-fill other fields.
    // Stripe test cards: 4242 4242 4242 4242, Exp: Any future date, CVC: Any 3 digits.
    alert("Use test card: 4242 4242 4242 4242 | Exp: 12/30 | CVC: 123");
  };

  if (status === "success") {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-12 space-y-4"
      >
        <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center text-emerald-500">
          <CheckCircle2 size={48} />
        </div>
        <h3 className="text-2xl font-bold">Payment Successful</h3>
        <p className="text-zinc-400 text-center">Your deposit of {formatCurrency(amount)} is being processed.</p>
      </motion.div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-xl font-medium text-white">Complete Deposit</h3>
          <p className="text-sm text-zinc-500">Amount: {formatCurrency(amount)}</p>
        </div>
        <button
          type="button"
          onClick={handleAutofill}
          className="flex items-center gap-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 px-3 py-1.5 rounded-full transition-colors border border-indigo-500/20"
        >
          <Wand2 size={14} />
          Auto-fill Test Card
        </button>
      </div>

      <div className="bg-zinc-900/50 p-4 rounded-xl border border-zinc-800">
        <PaymentElement options={{ layout: "tabs" }} />
      </div>

      {errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-rose-500/10 border border-rose-500/20 p-3 rounded-lg flex items-center gap-3 text-rose-400 text-sm"
        >
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </motion.div>
      )}

      {amount === 99900 && (
          <p className="text-[10px] text-zinc-600 italic mt-1 text-center font-mono">
            * Hint: $999 deposit will trigger a simulated "Declined" state.
          </p>
      )}

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 py-3 px-4 rounded-xl font-bold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors border border-zinc-800"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!stripe || loading}
          className="flex-1 py-3 px-4 rounded-xl font-bold text-black bg-white hover:bg-zinc-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
          ) : (
            <>
              <CreditCard size={18} />
              Pay Now
            </>
          )}
        </button>
      </div>
    </form>
  );
}

export default function DepositModal({
  isOpen,
  onClose,
  amount,
  onSuccess,
  onError,
}: {
  isOpen: boolean;
  onClose: () => void;
  amount: number;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const { token } = useAuth();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  console.log("DepositModal rendered:", { isOpen, amount, hasToken: !!token, hasClientSecret: !!clientSecret, isClient: typeof window !== "undefined" });

  useEffect(() => {
    console.log("DepositModal useEffect triggered", { isOpen, amount, hasToken: !!token });
    if (isOpen && amount > 0) {
      setLoading(true);
      setInitError(null);
      console.log("Fetching PaymentIntent for amount:", amount);
      fetch("/api/v1/deposits/payment_intents", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ amount, currency: "usd" }),
      })
        .then(async (res) => {
          console.log("PaymentIntent response status:", res.status);
          if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`API Error ${res.status}: ${errorText}`);
          }
          return res.json();
        })
        .then((data) => {
          console.log("PaymentIntent data received:", data);
          if (!data.client_secret) {
            throw new Error("No client_secret returned from API");
          }
          setClientSecret(data.client_secret);
        })
        .catch((err) => {
          console.error("Failed to fetch client secret:", err);
          setInitError(err.message || "Failed to initialize payment gateway");
          onError(err.message || "Failed to initialize payment gateway");
        })
        .finally(() => setLoading(false));
    } else {
      setClientSecret(null);
      setInitError(null);
    }
  }, [isOpen, amount, token, onError]);

  // Handle SSR - only render portal on client side
  const [isClient, setIsClient] = useState(false);
  
  useEffect(() => {
    setIsClient(true);
  }, []);

  const isMock = !process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.includes("mock");

  if (!isClient || !isOpen) {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      <div id="deposit-portal-root" className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
        <motion.div
           initial={{ opacity: 0 }}
           animate={{ opacity: 1 }}
           exit={{ opacity: 0 }}
           className="absolute inset-0 bg-black/80 backdrop-blur-md"
           onClick={onClose}
        />
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: "spring", duration: 0.5, bounce: 0.3 }}
          className="relative bg-zinc-950 border border-zinc-800 w-full max-w-lg rounded-[2.5rem] p-10 shadow-2xl overflow-hidden overflow-x-hidden flex flex-col glass-morphism"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50" />
          
          <button
            onClick={onClose}
            className="absolute top-8 right-8 text-zinc-500 hover:text-white transition-colors z-10"
          >
            <X size={24} />
          </button>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-6">
                <div className="relative">
                  <div className="w-16 h-16 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                  <CreditCard className="absolute inset-0 m-auto text-indigo-500/50" size={24} />
                </div>
                <div className="text-center space-y-2">
                  <p className="text-white font-medium">Initializing secure gateway...</p>
                  <p className="text-zinc-500 text-xs font-mono">Connecting to Bank Terminal</p>
                </div>
              </div>
            ) : initError ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="w-16 h-16 bg-rose-500/10 rounded-full flex items-center justify-center text-rose-500">
                  <AlertCircle size={32} />
                </div>
                <h3 className="text-lg font-bold text-white">Initialization Failed</h3>
                <p className="text-zinc-400 text-center text-sm">{initError}</p>
                <button 
                  onClick={onClose}
                  className="mt-4 px-6 py-2 rounded-xl bg-zinc-800 text-white font-medium hover:bg-zinc-700 transition-colors"
                >
                  Close
                </button>
              </div>
            ) : !clientSecret ? (
              <div className="text-center py-20 text-zinc-500 italic">
                Awaiting payment details...
              </div>
            ) : isMock ? (
              <div className="space-y-8 py-2">
                <div className="p-5 bg-indigo-500/10 border border-indigo-500/20 rounded-3xl">
                   <div className="flex items-center gap-3 mb-2">
                     <Sparkles size={16} className="text-indigo-400" />
                     <p className="text-indigo-400 text-xs font-bold uppercase tracking-widest">Secure Mode Active</p>
                   </div>
                   <p className="text-zinc-400 text-sm leading-relaxed">System is in testing environment. Simulated deposit flow is active.</p>
                </div>
                
                <div className="space-y-5">
                  <div className="space-y-2.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">Cardholder Name</label>
                    <input type="text" placeholder="Jane Doe" className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" />
                  </div>
                  <div className="space-y-2.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">Card Number</label>
                    <input type="text" placeholder="4242 4242 4242 4242" className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">MM</label>
                      <input type="text" placeholder="MM" className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" />
                    </div>
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">YYYY</label>
                      <input type="text" placeholder="YYYY" className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" />
                    </div>
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">CVC</label>
                      <input type="text" placeholder="123" className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" />
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={loading}
                  onClick={async () => {
                    setLoading(true);
                    console.log("DEBUG: Modal Deposit Button Clicked", { amount, type: typeof amount });
                    if (amount === 99900) {
                      setTimeout(() => {
                        setLoading(false);
                        setInitError("Your card was declined. (Simulation for $999)");
                        console.log("DEBUG: Modal calling onError for decline");
                        onError("Your card was declined. (Simulation for $999)");
                      }, 1500);
                      return;
                    }
                    try {
                      const intentId = clientSecret.split("_secret_")[0];
                      const res = await fetch("/api/v1/deposits/fulfill-payment", {
                        method: "POST",
                        headers: {
                          "Content-Type": "application/json",
                          Authorization: `Bearer ${token}`
                        },
                        body: JSON.stringify({ id: intentId })
                      });
                      
                      if (!res.ok) throw new Error("Fulfillment failed");
                      
                      console.log("DEBUG: Modal calling onSuccess");
                      onSuccess();
                    } catch (err: any) {
                      console.log("DEBUG: Modal calling onError for catch", err);
                      setInitError("Failed to process mock deposit.");
                      onError(err.message || "Failed to process mock deposit.");
                    } finally {
                      setLoading(false);
                    }
                  }}
                  className="w-full py-5 px-8 rounded-[1.5rem] bg-white text-black font-extrabold text-xl hover:bg-zinc-200 transition-all shadow-2xl shadow-white/5 active:scale-[0.98] mt-4 flex items-center justify-center gap-3"
                >
                  {loading ? (
                    <div className="w-6 h-6 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  ) : (
                    <>
                      <CreditCard size={20} />
                      Deposit ${amount / 100} to Main Account
                    </>
                  )}
                </button>
              </div>
            ) : (
              <Elements
                stripe={stripePromise}
                options={{
                  clientSecret,
                  appearance: {
                    theme: "night",
                    variables: {
                      colorPrimary: "#ffffff",
                      colorBackground: "#09090b",
                      colorText: "#ffffff",
                      colorDanger: "#fb7185",
                      fontFamily: "var(--font-sans), system-ui, sans-serif",
                      borderRadius: "16px",
                    },
                  },
                }}
              >
                <PaymentForm
                  amount={amount}
                  clientSecret={clientSecret}
                  onClose={onClose}
                  onSuccess={onSuccess}
                  onError={onError}
                />
              </Elements>
            )}
            
            <div className="mt-10 flex items-center justify-center gap-2.5 text-[10px] text-zinc-600 tracking-widest font-bold uppercase opacity-60 pb-2">
              <ShieldCheck size={14} className="text-zinc-700" />
              <span>PCI-DSS COMPLIANT | BANK-GRADE SECURITY</span>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>,
    document.body
  );
}

function ShieldCheck({ size, className }: { size?: number; className?: string }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}
