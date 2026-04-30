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
      return <CheckCircle2 className="text-emerald-500" size={24} />;
    }
    if (status === "cancelled" || status === "rejected") {
      return <AlertCircle className="text-rose-500" size={24} />;
    }
    return <Clock className="text-amber-500" size={24} />;
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
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-lg bg-white rounded-[2.5rem] shadow-2xl overflow-hidden border border-slate-100"
          >
            <div className="p-6 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-xl font-black text-slate-900 flex items-center gap-3">
                <StatusIcon /> {title}
              </h3>
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-8 space-y-8">
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-1">
                  <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Amount</p>
                  <p className="text-3xl font-black text-indigo-600">{formatCurrency(data.amount)}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Status</p>
                  <span className={`inline-flex px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${
                    data.status === "ACTIVE" || data.status === "APPROVED" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : 
                    data.status === "PENDING" ? "bg-amber-50 text-amber-600 border-amber-100" :
                    "bg-slate-50 text-slate-500 border-slate-100"
                  }`}>
                    {data.status}
                  </span>
                </div>
              </div>

              <div className="h-px bg-slate-100" />

              <div className="space-y-6">
                <div className="flex items-center gap-5 group">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                    <User size={24} />
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">{type === 'scheduled' ? 'Recipient' : 'Target User'}</p>
                    <p className="text-slate-900 font-bold text-lg">{data.recipient_email || data.target_email}</p>
                  </div>
                </div>

                {type === "scheduled" && (
                  <>
                    <div className="flex items-center gap-5 group">
                      <div className="w-12 h-12 rounded-2xl bg-purple-50 flex items-center justify-center text-purple-600">
                        <Calendar size={24} />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Frequency</p>
                        <p className="text-slate-900 font-bold text-lg">{data.frequency} (Every {data.frequency_interval})</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-5 group">
                      <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600">
                        <Clock size={24} />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Start Date</p>
                        <p className="text-slate-900 font-bold text-lg">{new Date(data.start_date).toLocaleDateString()}</p>
                      </div>
                    </div>
                  </>
                )}

                {type === "request" && (
                  <div className="flex items-center gap-5 group">
                    <div className="w-12 h-12 rounded-2xl bg-rose-50 flex items-center justify-center text-rose-600">
                      <FileText size={24} />
                    </div>
                    <div>
                      <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Purpose</p>
                      <p className="text-slate-900 font-bold text-lg">{data.purpose || "N/A"}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-5 bg-slate-900 rounded-[2rem] border border-slate-800 space-y-3 shadow-xl">
                <div className="flex items-center gap-2 text-[10px] font-black text-white/40 uppercase tracking-[0.2em]">
                  <ShieldCheck size={14} className="text-indigo-400" /> Transaction Security
                </div>
                <p className="text-xs text-white/60 leading-relaxed font-medium">
                  This transaction is protected by KarinBank's advanced fraud detection. 
                  Reference ID: <span className="text-white font-mono bg-white/10 px-2 py-0.5 rounded">#{data.id?.toString().slice(-8) || 'TRX-DEFAULT'}</span>
                </p>
              </div>
            </div>

            <div className="p-6 bg-slate-50/50 border-t border-slate-50">
              <button
                onClick={onClose}
                className="w-full py-5 bg-white border border-slate-200 text-slate-900 font-black text-xs uppercase tracking-widest rounded-2xl hover:bg-slate-100 transition-all shadow-sm active:scale-95"
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

