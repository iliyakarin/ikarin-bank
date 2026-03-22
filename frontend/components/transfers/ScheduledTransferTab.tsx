"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, ArrowRight, ChevronDown, Clock } from "lucide-react";
import DatePicker from "@/components/ui/DatePicker";
import { formatCurrency } from "@/lib/transactionUtils";
import { Account } from "@/lib/api/accounts";
import { Contact } from "@/lib/api/contacts";
import { createScheduledTransfer } from "@/lib/api/transfers";
import AccountSelector from "./AccountSelector";

interface ScheduledTransferTabProps {
  accounts: Account[];
  contacts: Contact[];
  vendors: any[];
  onSuccess: (id: string) => void;
  onError: (message: string) => void;
}

export default function ScheduledTransferTab({
  accounts,
  contacts,
  vendors,
  onSuccess,
  onError
}: ScheduledTransferTabProps) {
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState("Monthly");
  const [freqInterval, setFreqInterval] = useState("1");
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [endCondition, setEndCondition] = useState("Until Cancelled");
  const [endDate, setEndDate] = useState("");
  const [targetPayments, setTargetPayments] = useState("");
  const [reserveAmount, setReserveAmount] = useState(false);
  const [sourceAccountId, setSourceAccountId] = useState<number | "">("");
  const [subscriberId, setSubscriberId] = useState("");
  const [isVendor, setIsVendor] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isSourceOpen, setIsSourceOpen] = useState(false);
  const [isVendorDropdownOpen, setIsVendorDropdownOpen] = useState(false);

  useEffect(() => {
    const vendorMatch = vendors.find(v => v.email === recipient);
    setIsVendor(!!vendorMatch);
  }, [recipient, vendors]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(amount);
    if (!recipient.trim() || !amount || amt <= 0) {
      onError("Please provide a valid recipient and amount.");
      return;
    }

    if (amt > 5000) {
      onError("Amount exceeds the maximum scheduled transfer limit of $5000.");
      return;
    }

    setLoading(true);
    try {
      // Map frontend values to API enum values
      const freqMap: Record<string, "daily" | "weekly" | "monthly"> = {
        "Daily": "daily",
        "Weekly": "weekly",
        "Monthly": "monthly",
      };
      
      const condMap: Record<string, "never" | "date" | "occurrences"> = {
        "Until Cancelled": "never",
        "End Date": "date",
        "Number of Payments": "occurrences",
      };

      const payload = {
        recipient_email: recipient,
        amount: Math.round(amt * 100),
        frequency: freqMap[frequency] || "monthly",
        frequency_interval: freqInterval,
        start_date: new Date(startDate).toISOString(),
        end_condition: condMap[endCondition] || "never",
        end_date: endCondition === "End Date" && endDate ? new Date(endDate).toISOString() : null,
        max_occurrences: endCondition === "Number of Payments" && targetPayments ? parseInt(targetPayments) : null,
        reserve_amount: reserveAmount,
        funding_account_id: sourceAccountId || undefined,
        subscriber_id: subscriberId || undefined,
      };

      const res = await createScheduledTransfer(payload as any);
      onSuccess(res.scheduled_payment_id);
      setRecipient("");
      setAmount("");
    } catch (err) {
      onError("Failed to create scheduled transfer.");
    } finally {
      setLoading(false);
    }
  };

  const renderSummary = () => {
    if (!amount || !startDate) return "Fill out the form to see your schedule summary.";
    let text = `Next payment of $${amount} will be sent on ${startDate}. `;
    if (frequency === "One-time") {
      text += "This is a single payment.";
    } else {
      text += `It will repeat ${frequency.toLowerCase()} `;
      if (frequency === "Specific Day of Week") text += `on ${freqInterval} `;
      if (frequency === "Specific Date of Month") text += `on the ${freqInterval}th `;
      if (endCondition === "Until Cancelled") text += "until you cancel it.";
      if (endCondition === "End Date") text += `until ${endDate || "[Date]"}.`;
      if (endCondition === "Number of Payments") text += `for a total of ${targetPayments || "[N]"} payments.`;
    }
    return text;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <AccountSelector
        accounts={accounts}
        selectedId={sourceAccountId}
        onSelect={setSourceAccountId}
        isOpen={isSourceOpen}
        setIsOpen={setIsSourceOpen}
        label="Funding Account"
      />

      <div className="space-y-3 relative">
        <label className="block text-white font-semibold">Recipient or Vendor</label>
        <div className="relative">
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            onFocus={() => setIsVendorDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsVendorDropdownOpen(false), 200)}
            placeholder="Email or select a vendor"
            className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-indigo-400 pr-10"
            required
          />
          <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none" size={20} />
        </div>

        <AnimatePresence>
          {isVendorDropdownOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-50 w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
            >
              <div className="p-2">
                {contacts.filter(c => c.email.toLowerCase().includes(recipient.toLowerCase())).map(c => (
                  <div
                    key={c.id}
                    onClick={() => {
                      setRecipient(c.email);
                      setIsVendorDropdownOpen(false);
                    }}
                    className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer flex justify-between items-center group"
                  >
                    <div>
                      <p className="text-white font-medium group-hover:text-indigo-300">{c.name || c.email}</p>
                      <p className="text-white/50 text-sm">{c.email}</p>
                    </div>
                    <span className="text-[10px] bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded border border-purple-500/30 font-bold uppercase">Contact</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {isVendor && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-3">
          <label className="block text-white font-semibold">Subscriber / Contract ID</label>
          <input
            type="text"
            value={subscriberId}
            onChange={(e) => setSubscriberId(e.target.value)}
            placeholder="Enter your subscriber ID"
            className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-400"
            required
          />
        </motion.div>
      )}

      <div className="space-y-3">
        <label className="block text-white font-semibold flex justify-between">
          Amount (USD) <span className="text-indigo-300 font-normal text-sm">Limit: $5000</span>
        </label>
        <div className="relative">
          <span className="absolute left-4 top-3 text-white font-semibold text-lg">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white focus:outline-none focus:border-indigo-400"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3">
          <label className="block text-white font-semibold">Frequency</label>
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-400"
          >
            <option>One-time</option>
            <option>Daily</option>
            <option>Weekly</option>
            <option>Bi-weekly</option>
            <option>Monthly</option>
            <option>Annually</option>
            <option>Specific Day of Week</option>
            <option>Specific Date of Month</option>
          </select>
        </div>
        <DatePicker label="Start Date" value={startDate} onChange={setStartDate} required />
      </div>

      {frequency !== "One-time" && (
        <div className="space-y-4 p-4 border border-white/10 rounded-xl bg-white/5">
          <label className="block text-white font-semibold">End Condition</label>
          <div className="flex gap-4">
            {["Until Cancelled", "End Date", "Number of Payments"].map(cond => (
              <label key={cond} className="flex items-center gap-2 text-white/80 cursor-pointer">
                <input
                  type="radio"
                  value={cond}
                  checked={endCondition === cond}
                  onChange={(e) => setEndCondition(e.target.value)}
                  className="accent-indigo-500"
                />
                {cond}
              </label>
            ))}
          </div>
          {endCondition === "End Date" && <DatePicker value={endDate} onChange={setEndDate} required />}
          {endCondition === "Number of Payments" && (
            <input
              type="number"
              value={targetPayments}
              onChange={(e) => setTargetPayments(e.target.value)}
              placeholder="E.g. 5"
              className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white"
              required
            />
          )}
        </div>
      )}

      <div className="p-4 border border-indigo-500/30 rounded-xl bg-indigo-500/10 flex items-start gap-4">
        <input
          type="checkbox"
          id="reserveCheck"
          checked={reserveAmount}
          onChange={(e) => setReserveAmount(e.target.checked)}
          className="mt-1 w-5 h-5 accent-indigo-500 rounded"
        />
        <div>
          <label htmlFor="reserveCheck" className="text-white font-semibold block cursor-pointer">Reserve Balance Now</label>
          <p className="text-indigo-200/70 text-sm">Deduct the funds immediately and keep them aside for this transfer.</p>
        </div>
      </div>

      <div className="p-4 bg-black/20 rounded-xl shadow-inner border border-white/5 flex gap-3 text-indigo-100">
        <Clock className="shrink-0 mt-1" size={20} />
        <p className="font-medium text-sm leading-relaxed">{renderSummary()}</p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
      >
        {loading ? "Processing..." : <><Calendar size={20} /> Schedule Transfer <ArrowRight size={20} /></>}
      </button>
    </form>
  );
}
