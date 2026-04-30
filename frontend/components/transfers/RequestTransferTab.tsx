"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Handshake, ArrowRight } from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import { toCents } from "@/lib/transactionUtils";
import { Contact } from "@/lib/api/contacts";
import { postRequest } from "@/lib/api/transfers";
import ContactSelector from "./ContactSelector";

interface RequestTransferTabProps {
  contacts: Contact[];
  onSuccess: (txId: string) => void;
  onError: (message: string) => void;
}

export default function RequestTransferTab({
  contacts,
  onSuccess,
  onError
}: RequestTransferTabProps) {
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [purpose, setPurpose] = useState("");
  const [loading, setLoading] = useState(false);
  const [isContactOpen, setIsContactOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient.trim() || !amount || parseFloat(amount) <= 0) {
      onError("Please provide a valid email and amount.");
      return;
    }

    setLoading(true);
    try {
      const cleanPurpose = DOMPurify.sanitize(purpose);
      const res = await postRequest({
        target_email: recipient,
        amount: toCents(amount),
        purpose: cleanPurpose || "Payment request",
      });
      onSuccess(res.request_id);
      setRecipient("");
      setAmount("");
      setPurpose("");
    } catch (err: any) {
      onError(err.message || "Failed to create request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <ContactSelector
        contacts={contacts}
        value={recipient}
        onChange={setRecipient}
        isOpen={isContactOpen}
        setIsOpen={setIsContactOpen}
        label="Request From (Email)"
        placeholder="Enter email or select contact"
      />

      <div className="space-y-3">
        <label className="block text-white/60 font-bold text-sm uppercase tracking-wider">Amount to Request (USD)</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 font-bold text-lg">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            className="w-full bg-white/5 border border-white/10 rounded-2xl pl-8 pr-4 py-4 text-white font-bold text-lg placeholder:text-white/10 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all"
            required
          />
        </div>
      </div>

      <div className="space-y-3">
        <label className="block text-white/60 font-bold text-sm uppercase tracking-wider">Purpose <span className="text-white/20 font-normal normal-case">(Optional)</span></label>
        <textarea
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          placeholder="What is this request for?"
          rows={2}
          className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-4 text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all resize-none"
        />
      </div>

      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        className="p-5 bg-white/5 border border-white/10 rounded-[2rem] text-white/60 text-xs font-medium leading-relaxed italic"
      >
        Your request will be sent to the recipient. They will receive a notification to approve or decline the transfer.
      </motion.div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-rose-500 to-orange-600 hover:from-rose-600 hover:to-orange-700 disabled:opacity-50 text-white font-black py-5 rounded-[1.5rem] flex items-center justify-center gap-3 transition-all shadow-lg shadow-rose-500/20 hover:shadow-rose-500/30 uppercase tracking-widest text-sm"
      >
        {loading ? "Sending Request..." : <><Handshake size={20} /> Send Request <ArrowRight size={20} /></>}
      </button>
    </form>
  );
}
