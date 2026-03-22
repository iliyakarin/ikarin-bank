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
        <label className="block text-white font-semibold">Amount to Request (USD)</label>
        <div className="relative">
          <span className="absolute left-4 top-3 text-white font-semibold text-lg">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-rose-400"
            required
          />
        </div>
      </div>

      <div className="space-y-3">
        <label className="block text-white font-semibold">Purpose <span className="text-white/40 font-normal text-sm">(Optional)</span></label>
        <textarea
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          placeholder="What is this request for?"
          rows={2}
          className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-rose-400 resize-none"
        />
      </div>

      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-200 text-sm italic"
      >
        Your request will be sent to the recipient. They will receive a notification to approve or decline the transfer.
      </motion.div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-rose-500 to-orange-600 hover:from-rose-600 hover:to-orange-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-rose-900/20"
      >
        {loading ? "Sending Request..." : <><Handshake size={20} /> Send Request <ArrowRight size={20} /></>}
      </button>
    </form>
  );
}
