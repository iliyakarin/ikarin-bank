"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, ArrowRight, ChevronDown, Clock, Search } from "lucide-react";
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
        <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Recipient or Vendor</label>
        <div className="relative group">
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            onFocus={() => setIsVendorDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsVendorDropdownOpen(false), 200)}
            placeholder="Email or select a vendor"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all pr-10"
            required
          />
          <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-indigo-500 pointer-events-none transition-colors" size={20} />
        </div>

        <AnimatePresence>
          {isVendorDropdownOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-50 w-full mt-2 bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
            >
              <div className="p-2">
                {/* Vendors Section */}
                {vendors.length > 0 && (
                  <div className="mb-2">
                    <p className="px-4 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-50">Authorized Merchants</p>
                    {vendors.filter(v => v.name.toLowerCase().includes(recipient.toLowerCase()) || v.email.toLowerCase().includes(recipient.toLowerCase())).map(v => (
                      <div
                        key={v.id}
                        onClick={() => {
                          setRecipient(v.email);
                          setIsVendorDropdownOpen(false);
                        }}
                        className="px-4 py-3 hover:bg-slate-50 rounded-xl cursor-pointer flex justify-between items-center group/item transition-colors"
                      >
                        <div>
                          <p className="text-slate-900 font-bold group-hover/item:text-indigo-600">{v.name}</p>
                          <p className="text-slate-400 text-xs font-medium">{v.email}</p>
                        </div>
                        <span className="text-[9px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded border border-indigo-100 font-black uppercase tracking-tighter">Merchant</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Contacts Section */}
                <div>
                  <p className="px-4 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-50">Frequent Contacts</p>
                  {contacts.filter(c => (c.name && c.name.toLowerCase().includes(recipient.toLowerCase())) || c.email.toLowerCase().includes(recipient.toLowerCase())).map(c => (
                    <div
                      key={c.id}
                      onClick={() => {
                        setRecipient(c.email);
                        setIsVendorDropdownOpen(false);
                      }}
                      className="px-4 py-3 hover:bg-slate-50 rounded-xl cursor-pointer flex justify-between items-center group/item transition-colors"
                    >
                      <div>
                        <p className="text-slate-900 font-bold group-hover/item:text-indigo-600">{c.name || c.email}</p>
                        <p className="text-slate-400 text-xs font-medium">{c.email}</p>
                      </div>
                      <span className="text-[9px] bg-slate-50 text-slate-400 px-2 py-0.5 rounded border border-slate-200 font-black uppercase tracking-tighter">Contact</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
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

      <div className="space-y-3">
        <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider flex justify-between">
          Amount (USD) <span className="text-indigo-600 font-black text-[10px] uppercase tracking-widest">Limit: $5000</span>
        </label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-lg">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl pl-8 pr-4 py-4 text-slate-900 font-bold text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3">
          <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Frequency</label>
          <div className="relative group">
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all appearance-none"
            >
              <option>One-time</option>
              <option>Daily</option>
              <option>Weekly</option>
              <option>Bi-weekly</option>
              <option>Monthly</option>
              <option>Annually</option>
            </select>
            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 pointer-events-none group-focus-within:text-indigo-500" size={18} />
          </div>
        </div>
        <div className="space-y-3">
          <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">Start Date</label>
          <DatePicker value={startDate} onChange={setStartDate} required />
        </div>
      </div>

      {frequency !== "One-time" && (
        <div className="space-y-4 p-6 border border-slate-100 rounded-2xl bg-slate-50/50">
          <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider">End Condition</label>
          <div className="flex flex-wrap gap-6">
            {["Until Cancelled", "End Date", "Number of Payments"].map(cond => (
              <label key={cond} className="flex items-center gap-2 text-slate-600 font-bold text-xs cursor-pointer group">
                <input
                  type="radio"
                  value={cond}
                  checked={endCondition === cond}
                  onChange={(e) => setEndCondition(e.target.value)}
                  className="w-4 h-4 accent-indigo-600"
                />
                <span className="group-hover:text-indigo-600 transition-colors">{cond}</span>
              </label>
            ))}
          </div>
          <div className="mt-4">
            {endCondition === "End Date" && <DatePicker label="Finish Date" value={endDate} onChange={setEndDate} required />}
            {endCondition === "Number of Payments" && (
              <input
                type="number"
                value={targetPayments}
                onChange={(e) => setTargetPayments(e.target.value)}
                placeholder="Total number of payments (e.g. 12)"
                className="w-full bg-white border border-slate-200 rounded-2xl px-4 py-4 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                required
              />
            )}
          </div>
        </div>
      )}

      <div className="p-5 border border-indigo-100 rounded-2xl bg-indigo-50/30 flex items-start gap-4">
        <input
          type="checkbox"
          id="reserveCheck"
          checked={reserveAmount}
          onChange={(e) => setReserveAmount(e.target.checked)}
          className="mt-1 w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
        />
        <div>
          <label htmlFor="reserveCheck" className="text-slate-900 font-black text-sm uppercase tracking-tight block cursor-pointer">Reserve Balance Now</label>
          <p className="text-slate-500 text-xs font-medium leading-relaxed">Funds will be immediately set aside to ensure the schedule executes successfully even if your balance drops.</p>
        </div>
      </div>

      <div className="p-5 bg-slate-900 rounded-[2rem] shadow-xl flex gap-4 text-white border border-slate-800">
        <div className="p-2 bg-white/10 rounded-xl h-fit">
          <Clock className="text-indigo-400" size={20} />
        </div>
        <div>
          <p className="text-[10px] font-black text-white/40 uppercase tracking-[0.2em] mb-1">Schedule Summary</p>
          <p className="font-bold text-sm leading-relaxed">{renderSummary()}</p>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 text-white font-black py-5 rounded-[1.5rem] flex items-center justify-center gap-3 transition-all shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 uppercase tracking-widest text-sm"
      >
        {loading ? "Processing..." : <><Calendar size={20} /> Create Schedule <ArrowRight size={20} /></>}
      </button>
    </form>
);
}

