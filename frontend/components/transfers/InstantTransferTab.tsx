"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, ArrowRight, ChevronDown } from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import { toCents } from "@/lib/transactionUtils";
import { Account } from "@/lib/api/accounts";
import { Contact } from "@/lib/api/contacts";
import AccountSelector from "./AccountSelector";

interface InstantTransferTabProps {
  accounts: Account[];
  contacts: Contact[];
  vendors: any[];
  onSuccess: (txId: string) => void;
  onError: (message: string) => void;
}

export default function InstantTransferTab({
  accounts,
  contacts,
  vendors,
  onSuccess,
  onError
}: InstantTransferTabProps) {
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [commentary, setCommentary] = useState("");
  const [sourceAccountId, setSourceAccountId] = useState<number | "">("");
  const [subscriberId, setSubscriberId] = useState("");
  const [isVendor, setIsVendor] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isSourceOpen, setIsSourceOpen] = useState(false);
  const [isContactOpen, setIsContactOpen] = useState(false);

  useEffect(() => {
    const vendorMatch = vendors.find(v => v.email === recipient);
    setIsVendor(!!vendorMatch);
  }, [recipient, vendors]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient.trim() || !amount || parseFloat(amount) <= 0) {
      onError("Please provide a valid recipient and amount.");
      return;
    }

    setLoading(true);
    try {
      const cleanCommentary = DOMPurify.sanitize(commentary);
      const res = await fetch("/api/v1/p2p-transfer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bank_token")}`,
        },
        body: JSON.stringify({
          recipient_email: recipient,
          amount: toCents(amount),
          commentary: cleanCommentary || null,
          source_account_id: sourceAccountId || undefined,
          subscriber_id: subscriberId || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        onSuccess(data.transaction_id);
        setRecipient("");
        setAmount("");
        setCommentary("");
      } else {
        const data = await res.json();
        onError(data.detail || "Transfer failed");
      }
    } catch (err) {
      onError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <AccountSelector
        accounts={accounts}
        selectedId={sourceAccountId}
        onSelect={setSourceAccountId}
        isOpen={isSourceOpen}
        setIsOpen={setIsSourceOpen}
      />

      <div className="space-y-3 relative">
        <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Recipient Email</label>
        <div className="relative group">
          <input
            type="email"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            onFocus={() => setIsContactOpen(true)}
            onBlur={() => setTimeout(() => setIsContactOpen(false), 200)}
            placeholder="user@example.com"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all pr-10"
            required
          />
          <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-indigo-500 pointer-events-none transition-colors" size={20} />
        </div>

        <AnimatePresence>
          {isContactOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-50 w-full mt-2 bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
            >
              <div className="p-2">
                {contacts.filter(c => c.email.toLowerCase().includes(recipient.toLowerCase())).length > 0 ? (
                  contacts.filter(c => c.email.toLowerCase().includes(recipient.toLowerCase())).map(c => (
                    <div
                      key={c.id}
                      onClick={() => {
                        setRecipient(c.email);
                        if (c.subscriber_id) setSubscriberId(c.subscriber_id);
                        setIsContactOpen(false);
                      }}
                      className="px-4 py-3 hover:bg-slate-50 rounded-xl cursor-pointer flex justify-between items-center group/item transition-colors"
                    >
                      <div>
                        <p className="text-slate-900 font-bold group-hover/item:text-indigo-600">{c.name || c.email}</p>
                        <p className="text-slate-400 text-xs font-medium">{c.email}</p>
                      </div>
                      <ArrowRight size={14} className="text-slate-200 group-hover/item:text-indigo-400 group-hover/item:translate-x-1 transition-all" />
                    </div>
                  ))
                ) : (
                  <div className="px-4 py-3 text-slate-400 text-sm text-center">No contacts found</div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="space-y-3">
        <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Amount (USD)</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-lg">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl pl-8 pr-4 py-4 text-slate-900 font-bold text-lg placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            required
          />
        </div>
      </div>

      <div className="space-y-3">
        <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Commentary <span className="text-slate-400 font-normal normal-case">(Optional)</span></label>
        <textarea
          value={commentary}
          onChange={(e) => setCommentary(e.target.value)}
          placeholder="What is this for?"
          rows={2}
          className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none"
        />
      </div>

      {isVendor && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-3">
          <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Subscriber / Contract ID</label>
          <input
            type="text"
            value={subscriberId}
            onChange={(e) => setSubscriberId(e.target.value)}
            placeholder="Enter your subscriber ID"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            required
          />
        </motion.div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 text-white font-black py-5 rounded-[1.5rem] flex items-center justify-center gap-3 transition-all shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 uppercase tracking-widest text-sm"
      >
        {loading ? "Processing..." : <><Send size={20} /> Send Instantly <ArrowRight size={20} /></>}
      </button>
    </form>
  );
}
