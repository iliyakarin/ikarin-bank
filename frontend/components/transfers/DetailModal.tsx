"use client";
import { motion, AnimatePresence } from "framer-motion";
import { X, Calendar, User, DollarSign, Clock, HelpCircle, FileText, CheckCircle2, ShieldCheck, AlertCircle } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";

interface DetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: any;
  type: "scheduled" | "request";
}

export default function DetailModal({
  isOpen,
  onClose,
  title,
  data,
  type
}: DetailModalProps) {
  if (!data) return null;

  const StatusIcon = () => {
    const status = data.status?.toLowerCase() || "";
    if (status === "active" || status === "completed" || status === "approved") {
      return <CheckCircle2 className="text-emerald-400" size={24} />;
    }
    if (status === "cancelled" || status === "rejected") {
      return <AlertCircle className="text-rose-400" size={24} />;
    }
    return <Clock className="text-amber-400" size={24} />;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-[#0f0a1ea0] backdrop-blur-md"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-lg bg-[#2a1f42] border border-white/10 rounded-3xl shadow-2xl overflow-hidden"
          >
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/5">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <StatusIcon /> {title}
              </h3>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/10 rounded-full text-white/40 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-8 space-y-6">
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Amount</p>
                  <p className="text-2xl font-black text-white">{formatCurrency(data.amount)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Status</p>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                    data.status === "ACTIVE" || data.status === "APPROVED" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : 
                    data.status === "PENDING" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
                    "bg-white/10 text-white/60 border border-white/20"
                  }`}>
                    {data.status}
                  </span>
                </div>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

              <div className="space-y-4">
                <div className="flex items-center gap-4 group">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400">
                    <User size={20} />
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">{type === 'scheduled' ? 'Recipient' : 'Target'}</p>
                    <p className="text-white font-medium">{data.recipient_email || data.target_email}</p>
                  </div>
                </div>

                {type === "scheduled" && (
                  <>
                    <div className="flex items-center gap-4 group">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                        <Calendar size={20} />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Frequency</p>
                        <p className="text-white font-medium">{data.frequency} (Every {data.frequency_interval})</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 group">
                      <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400">
                        <Clock size={20} />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Start Date</p>
                        <p className="text-white font-medium">{new Date(data.start_date).toLocaleDateString()}</p>
                      </div>
                    </div>
                  </>
                )}

                {type === "request" && (
                  <div className="flex items-center gap-4 group">
                    <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-400">
                      <FileText size={20} />
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Purpose</p>
                      <p className="text-white font-medium">{data.purpose || "N/A"}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 bg-white/5 rounded-2xl border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-[10px] font-bold text-white/30 uppercase tracking-widest">
                  <ShieldCheck size={12} /> Transaction Security
                </div>
                <p className="text-xs text-white/50 leading-relaxed italic">
                  This transaction is protected by KarinBank's advanced fraud detection. 
                  Reference ID: <span className="text-white/80 font-mono">#{data.id?.toString().slice(-8) || 'TRX-DEFAULT'}</span>
                </p>
              </div>
            </div>

            <div className="p-6 bg-white/5 border-t border-white/10">
              <button
                onClick={onClose}
                className="w-full py-3 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl transition-all border border-white/10"
              >
                Close Details
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
