"use client";
import { motion } from "framer-motion";
import { Handshake, Eye, ShieldCheck } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { PaymentRequest } from "@/lib/api/transfers";

interface RequestHistoryTableProps {
  requests: PaymentRequest[];
  onViewDetails: (request: PaymentRequest) => void;
}

export default function RequestHistoryTable({
  requests,
  onViewDetails
}: RequestHistoryTableProps) {
  if (requests.length === 0) {
    return (
      <div className="p-12 text-center text-white/40 bg-white/5 rounded-2xl border border-dashed border-white/10">
        <Handshake size={48} className="mx-auto mb-4 opacity-20" />
        <p className="text-lg">No payment requests found.</p>
        <p className="text-sm">Requests you've sent will appear here.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="text-white/40 uppercase text-[10px] font-bold tracking-widest border-b border-white/10">
            <th className="px-6 py-4">Requester</th>
            <th className="px-6 py-4">Target</th>
            <th className="px-6 py-4">Amount</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {requests.map((r) => (
            <motion.tr
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              key={r.id}
              className="group hover:bg-white/5 transition-colors"
            >
              <td className="px-6 py-5">
                <span className="text-white font-medium block uppercase tracking-tight">
                  {r.requester_email || "Me"}
                </span>
                <span className="text-[10px] text-white/30">
                  REF: #{r.id.toString().slice(-8)}
                </span>
              </td>
              <td className="px-6 py-5 text-white/60">
                {r.target_email}
              </td>
              <td className="px-6 py-5">
                <span className="text-white font-bold">{formatCurrency(r.amount)}</span>
              </td>
              <td className="px-6 py-5">
                <span className={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase ${
                  r.status === "APPROVED" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : 
                  r.status === "PENDING" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
                  "bg-white/10 text-white/40 border border-white/20"
                }`}>
                  {r.status}
                </span>
              </td>
              <td className="px-6 py-5 text-right">
                <button
                  onClick={() => onViewDetails(r)}
                  className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-white transition-all flex items-center gap-1 group/btn ml-auto"
                >
                  <Eye size={16} className="group-hover/btn:scale-110 transition-transform" />
                  <span className="text-xs font-bold uppercase tracking-tighter hidden sm:inline">Details</span>
                </button>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
