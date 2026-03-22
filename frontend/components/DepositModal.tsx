"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle2, AlertCircle, CreditCard, Sparkles, Wand2 } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { formatCurrency } from "@/lib/transactionUtils";
import { createPaymentIntent, fulfillPayment } from "@/lib/api/deposits";

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
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  // Local form state
  const [cardName, setCardName] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [expMonth, setExpMonth] = useState("");
  const [expYear, setExpYear] = useState("");
  const [cvc, setCvc] = useState("");

  useEffect(() => {
    if (isOpen && amount > 0) {
      setLoading(true);
      setInitError(null);
      setStatus("idle");
      createPaymentIntent(amount)
        .then((data) => {
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
      setStatus("idle");
    }
  }, [isOpen, amount, onError]);

  // Handle SSR
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient || !isOpen) {
    return null;
  }

  const handleDeposit = async () => {
    setLoading(true);
    setStatus("idle");
    
    if (amount === 99900) {
      setTimeout(() => {
        setStatus("error");
        setInitError("Your card was declined. (Simulation for $999)");
        onError("Your card was declined. (Simulation for $999)");
        setLoading(false);
      }, 1500);
      return;
    }

    try {
      if (!clientSecret) throw new Error("Missing client secret");
      const intentId = clientSecret.split("_secret_")[0];
      
      await fulfillPayment(intentId);

      setStatus("success");
      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to process deposit.";
      setStatus("error");
      setInitError(message);
      onError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutofill = () => {
    setCardName("Jane Doe");
    setCardNumber("4242 4242 4242 4242");
    setExpMonth("12");
    setExpYear("2030");
    setCvc("123");
  };

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
            {loading && status === "idle" && !clientSecret ? (
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
            ) : initError && status === "idle" ? (
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
            ) : (
              <div className="space-y-8 py-2">
                <div className="flex justify-between items-center">
                   <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex-1 mr-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Sparkles size={14} className="text-indigo-400" />
                        <p className="text-indigo-400 text-[10px] font-bold uppercase tracking-wider">Mock Gateway</p>
                      </div>
                      <p className="text-zinc-500 text-[11px]">System is in testing environment.</p>
                   </div>
                   <button
                    type="button"
                    onClick={handleAutofill}
                    className="flex items-center gap-2 text-xs font-medium text-white hover:bg-zinc-800 bg-zinc-900 px-4 py-2.5 rounded-2xl transition-all border border-zinc-800"
                  >
                    <Wand2 size={14} />
                    Auto-fill
                  </button>
                </div>

                <div className="space-y-5">
                  <div className="space-y-2.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">Cardholder Name</label>
                    <input 
                      type="text" 
                      placeholder="Jane Doe" 
                      value={cardName}
                      onChange={(e) => setCardName(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" 
                    />
                  </div>
                  <div className="space-y-2.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">Card Number</label>
                    <input 
                      type="text" 
                      placeholder="4242 4242 4242 4242" 
                      value={cardNumber}
                      onChange={(e) => setCardNumber(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" 
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">MM</label>
                      <input 
                        type="text" 
                        placeholder="MM" 
                        value={expMonth}
                        onChange={(e) => setExpMonth(e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" 
                      />
                    </div>
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">YYYY</label>
                      <input 
                        type="text" 
                        placeholder="YYYY" 
                        value={expYear}
                        onChange={(e) => setExpYear(e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" 
                      />
                    </div>
                    <div className="space-y-2.5">
                      <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">CVC</label>
                      <input 
                        type="text" 
                        placeholder="123" 
                        value={cvc}
                        onChange={(e) => setCvc(e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" 
                      />
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={loading || !clientSecret}
                  onClick={handleDeposit}
                  className="w-full py-5 px-8 rounded-[1.5rem] bg-white text-black font-extrabold text-xl hover:bg-zinc-200 transition-all shadow-2xl shadow-white/5 active:scale-[0.98] mt-4 flex items-center justify-center gap-3"
                >
                  {loading ? (
                    <div className="w-6 h-6 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  ) : (
                    <>
                      <CreditCard size={20} />
                      Deposit {formatCurrency(amount)}
                    </>
                  )}
                </button>

                {status === "success" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center gap-3"
                  >
                    <div className="w-8 h-8 bg-emerald-500/20 rounded-full flex items-center justify-center">
                      <CheckCircle2 size={16} className="text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-emerald-400 font-medium text-sm">Deposit Successful</p>
                      <p className="text-emerald-400/70 text-xs">Funds available in main account.</p>
                    </div>
                  </motion.div>
                )}

                {status === "error" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-center gap-3"
                  >
                    <div className="w-8 h-8 bg-rose-500/20 rounded-full flex items-center justify-center">
                      <AlertCircle size={16} className="text-rose-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-rose-400 font-medium text-sm">Deposit Declined</p>
                      <p className="text-rose-400/70 text-xs">{initError || "Card was declined"}</p>
                    </div>
                  </motion.div>
                )}
              </div>
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
