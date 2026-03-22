"use client";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, Trash2, Eye, ExternalLink } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { ScheduledPayment } from "@/lib/api/transfers";

interface ScheduledHistoryTableProps {
  payments: ScheduledPayment[];
  onViewDetails: (payment: ScheduledPayment) => void;
  onCancel: (payment: ScheduledPayment) => void;
}

export default function ScheduledHistoryTable({
  payments,
  onViewDetails,
  onCancel
}: ScheduledHistoryTableProps) {
  if (payments.length === 0) {
    return (
      <div className="p-12 text-center text-white/40 bg-white/5 rounded-2xl border border-dashed border-white/10">
        <Calendar size={48} className="mx-auto mb-4 opacity-20" />
        <p className="text-lg">No scheduled transfers found.</p>
        <p className="text-sm">Active transfers will appear here.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="text-white/40 uppercase text-[10px] font-bold tracking-widest border-b border-white/10">
            <th className="px-6 py-4">Recipient</th>
            <th className="px-6 py-4">Amount</th>
            <th className="px-6 py-4">Frequency</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {payments.map((p) => (
            <motion.tr
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              key={p.id}
              className="group hover:bg-white/5 transition-colors"
            >
              <td className="px-6 py-5">
                <span className="text-white font-medium block group-hover:text-purple-300 transition-colors uppercase tracking-tight">
                  {p.recipient_email}
                </span>
                <span className="text-[10px] text-white/30 truncate block max-w-[150px]">
                  ID: #{p.id.toString().slice(-8)}
                </span>
              </td>
              <td className="px-6 py-5">
                <span className="text-white font-bold">{formatCurrency(p.amount)}</span>
              </td>
              <td className="px-6 py-5">
                <div className="flex items-center gap-2 text-white/60 text-sm">
                  <Calendar size={14} className="text-purple-400" />
                  {p.frequency}
                </div>
              </td>
              <td className="px-6 py-5">
                <span className={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase ${
                  p.status === "ACTIVE" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : 
                  "bg-white/10 text-white/40 border border-white/20"
                }`}>
                  {p.status}
                </span>
              </td>
              <td className="px-6 py-5 text-right">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => onViewDetails(p)}
                    className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-white transition-all flex items-center gap-1 group/btn"
                    title="View Details"
                  >
                    <Eye size={16} className="group-hover/btn:scale-110 transition-transform" />
                  </button>
                  {p.status === "ACTIVE" && (
                    <button
                      onClick={() => onCancel(p)}
                      className="p-2 hover:bg-rose-500/10 rounded-lg text-white/40 hover:text-rose-400 transition-all flex items-center gap-1 group/btn"
                      title="Cancel Subscription"
                    >
                      <Trash2 size={16} className="group-hover/btn:scale-110 transition-transform" />
                    </button>
                  )}
                </div>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
