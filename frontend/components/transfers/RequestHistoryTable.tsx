"use client";
import { motion } from "framer-motion";
import { Handshake, Eye, XCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { PaymentRequest } from "@/lib/api/transfers";

interface RequestHistoryTableProps {
  requests: PaymentRequest[];
  currentUserEmail?: string;
  onViewDetails: (request: PaymentRequest) => void;
  onCancel: (request: PaymentRequest) => void;
  onPay?: (request: PaymentRequest) => void;
}

export default function RequestHistoryTable({
  requests,
  currentUserEmail,
  onViewDetails,
  onCancel,
  onPay
}: RequestHistoryTableProps) {
  if (requests.length === 0) {
    return (
      <div className="p-12 text-center text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
        <Handshake size={48} className="mx-auto mb-4 opacity-20" />
        <p className="text-lg font-medium text-slate-600">No payment requests found.</p>
        <p className="text-sm">Requests involving you will appear here.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-slate-400 uppercase text-[10px] font-black tracking-[0.2em] border-b border-slate-100 bg-slate-50/30">
            <th className="px-6 py-4">Participants</th>
            <th className="px-6 py-4">Purpose</th>
            <th className="px-6 py-4">Amount</th>
            <th className="px-6 py-4 text-center">Status</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {requests.map((r) => {
            const isRequester = currentUserEmail === r.requester_email;
            const isTarget = currentUserEmail === r.target_email;
            const canCancel = isRequester && (r.status === "PENDING" || r.status === "pending_target");
            const canPay = isTarget && (r.status === "PENDING" || r.status === "pending_target");

            return (
              <motion.tr
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                key={r.id}
                className="group hover:bg-slate-50 transition-colors"
              >
                <td className="px-6 py-5">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-800 font-bold text-sm">
                      {isRequester ? "Me" : r.requester_email.split('@')[0]}
                    </span>
                    <ArrowRight size={12} className="text-slate-300" />
                    <span className="text-slate-800 font-bold text-sm">
                      {isTarget ? "Me" : r.target_email.split('@')[0]}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-black uppercase tracking-tighter">
                    REF: #{r.id.toString().slice(-8)}
                  </span>
                </td>
                <td className="px-6 py-5 text-slate-500 font-medium text-xs max-w-[200px] truncate">
                  {r.purpose || "No purpose provided"}
                </td>
                <td className="px-6 py-5">
                  <span className="text-slate-900 font-black text-lg">{formatCurrency(r.amount)}</span>
                </td>
                <td className="px-6 py-5 text-center">
                  <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-widest uppercase border ${
                    r.status === "APPROVED" || r.status === "paid" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : 
                    r.status === "PENDING" || r.status === "pending_target" ? "bg-amber-50 text-amber-600 border-amber-100" :
                    "bg-slate-50 text-slate-400 border-slate-200"
                  }`}>
                    {r.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {canPay && onPay && (
                      <button
                        onClick={() => onPay(r)}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-sm active:scale-95 flex items-center gap-2"
                      >
                        <CheckCircle2 size={14} /> Pay Now
                      </button>
                    )}
                    {canCancel && (
                      <button
                        onClick={() => onCancel(r)}
                        title="Cancel Request"
                        className="p-2.5 hover:bg-rose-50 rounded-xl text-slate-300 hover:text-rose-500 transition-all border border-transparent hover:border-rose-100"
                      >
                        <XCircle size={18} />
                      </button>
                    )}
                    <button
                      onClick={() => onViewDetails(r)}
                      className="p-2.5 hover:bg-slate-100 rounded-xl text-slate-300 hover:text-indigo-600 transition-all group/btn border border-transparent hover:border-slate-200"
                    >
                      <Eye size={18} className="group-hover/btn:scale-110 transition-transform" />
                    </button>
                  </div>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


