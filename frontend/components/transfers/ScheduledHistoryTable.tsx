"use client";
import { motion } from "framer-motion";
import { Calendar, Trash2, Eye } from "lucide-react";
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
      <div className="p-12 text-center text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
        <Calendar size={48} className="mx-auto mb-4 opacity-20" />
        <p className="text-lg font-medium text-slate-600">No scheduled transfers found.</p>
        <p className="text-sm">Active transfers will appear here.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-slate-400 uppercase text-[10px] font-bold tracking-widest border-b border-slate-100 bg-slate-50/30">
            <th className="px-6 py-4">Recipient</th>
            <th className="px-6 py-4">Amount</th>
            <th className="px-6 py-4">Frequency</th>
            <th className="px-6 py-4 text-center">Status</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {payments.map((p) => (
            <motion.tr
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              key={p.id}
              className="group hover:bg-slate-50 transition-colors"
            >
              <td className="px-6 py-5">
                <span className="text-slate-800 font-bold block leading-tight uppercase tracking-tight">
                  {p.recipient_email}
                </span>
                <span className="text-[10px] text-slate-400">
                  ID: #{p.id.toString().slice(-8)}
                </span>
              </td>
              <td className="px-6 py-5">
                <span className="text-slate-900 font-black">{formatCurrency(p.amount)}</span>
              </td>
              <td className="px-6 py-5">
                <div className="flex items-center gap-2 text-slate-500 text-sm font-medium">
                  <Calendar size={14} className="text-indigo-400" />
                  <span className="capitalize">{p.frequency}</span>
                </div>
              </td>
              <td className="px-6 py-5 text-center">
                <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-widest uppercase border ${
                  p.status === "ACTIVE" || p.status === "Active" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : 
                  "bg-slate-50 text-slate-400 border-slate-200"
                }`}>
                  {p.status}
                </span>
              </td>
              <td className="px-6 py-5 text-right">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => onViewDetails(p)}
                    className="p-2 hover:bg-slate-100 rounded-lg text-slate-300 hover:text-indigo-600 transition-all group/btn"
                    title="View Details"
                  >
                    <Eye size={16} className="group-hover/btn:scale-110 transition-transform" />
                  </button>
                  {(p.status === "ACTIVE" || p.status === "Active") && (
                    <button
                      onClick={() => onCancel(p)}
                      className="p-2 hover:bg-rose-50 rounded-lg text-slate-300 hover:text-rose-500 transition-all group/btn"
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

