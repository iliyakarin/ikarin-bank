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
}: {
  amount: number;
  clientSecret: string;
  onClose: () => void;
  onSuccess: () => void;
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
        setLoading(false);
      }, 1500);
      return;
    }

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/client/stripe/success`,
      },
      redirect: "if_required",
    });

    if (error) {
      setErrorMessage(error.message || "An unexpected error occurred.");
      setStatus("error");
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

export default function StripePaymentModal({
  isOpen,
  onClose,
  amount,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  amount: number;
  onSuccess: () => void;
}) {
  const { token } = useAuth();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    console.log("StripePaymentModal useEffect triggered", { isOpen, amount, hasToken: !!token });
    if (isOpen && amount > 0) {
      setLoading(true);
      setInitError(null);
      console.log("Fetching PaymentIntent for amount:", amount);
      fetch("/api/v1/stripe/payment_intents", {
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
        })
        .finally(() => setLoading(false));
    } else {
      setClientSecret(null);
      setInitError(null);
    }
  }, [isOpen, amount, token]);

  // Handle SSR - only render portal on client side
  const [isClient, setIsClient] = useState(false);
  
  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return null;
  }

  return (
    <AnimatePresence>
      {isOpen && createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            className="relative bg-zinc-950 border border-zinc-800 w-full max-w-md rounded-[2rem] p-8 shadow-2xl overflow-hidden glass-morphism"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50" />
            
            <button
              onClick={onClose}
              className="absolute top-6 right-6 text-zinc-500 hover:text-white transition-colors"
            >
              <X size={24} />
            </button>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-6">
                <div className="relative">
                  <div className="w-16 h-16 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                  <CreditCard className="absolute inset-0 m-auto text-indigo-500/50" size={24} />
                </div>
                <div className="text-center space-y-2">
                  <p className="text-white font-medium">Initializing secure gateway...</p>
                  <p className="text-zinc-500 text-xs font-mono">Contacting Stripe Test API</p>
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
                      borderRadius: "12px",
                    },
                  },
                }}
              >
                <PaymentForm
                  amount={amount}
                  clientSecret={clientSecret}
                  onClose={onClose}
                  onSuccess={onSuccess}
                />
              </Elements>
            )}
            
            <div className="mt-8 flex items-center justify-center gap-2 text-[10px] text-zinc-600 tracking-wider font-medium uppercase">
              <ShieldCheck size={12} className="text-zinc-700" />
              <span>PCI-DSS COMPLIANT | STRIPE SECURED</span>
            </div>
          </motion.div>
        </div>,
        document.body
      )}
    </AnimatePresence>
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
