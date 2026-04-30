"use client";
import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Handshake, 
  Eye, 
  XCircle, 
  CheckCircle2, 
  ArrowRight, 
  Search, 
  ChevronLeft, 
  ChevronRight,
  Hash
} from "lucide-react";
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
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const filteredData = useMemo(() => {
    return requests.filter(r => {
      const matchesSearch = 
        r.requester_email.toLowerCase().includes(search.toLowerCase()) || 
        r.target_email.toLowerCase().includes(search.toLowerCase()) ||
        (r.purpose && r.purpose.toLowerCase().includes(search.toLowerCase())) ||
        r.id.toString().toLowerCase().includes(search.toLowerCase());
      
      const matchesStatus = filterStatus === "ALL" || r.status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [requests, search, filterStatus]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

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
    <div className="w-full flex flex-col h-full">
      {/* Table Controls */}
      <div className="p-4 border-b border-white/5 bg-white/5 flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
          <input 
            type="text" 
            placeholder="Search participants, purpose or ID..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all"
          />
        </div>
        
        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          <div className="flex bg-white/5 border border-white/10 rounded-xl p-1 shrink-0">
            {["ALL", "PENDING", "APPROVED", "DECLINED"].map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                  filterStatus === status ? "bg-white text-slate-900 shadow-sm" : "text-white/40 hover:text-white/60"
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="text-white/20 uppercase text-[10px] font-black tracking-[0.2em] border-b border-white/5 bg-white/5">
              <th className="px-6 py-4">Participants / ID</th>
              <th className="px-6 py-4">Purpose</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4 text-center">Status</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {paginatedData.map((r) => {
              const isRequester = currentUserEmail === r.requester_email;
              const isTarget = currentUserEmail === r.target_email;
              const canCancel = isRequester && (r.status === "PENDING" || r.status === "pending_target");
              const canPay = isTarget && (r.status === "PENDING" || r.status === "pending_target");

              return (
                <motion.tr
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  key={r.id}
                  className="group hover:bg-white/5 transition-colors"
                >
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-white font-bold text-sm">
                        {isRequester ? "Me" : r.requester_email.split('@')[0]}
                      </span>
                      <ArrowRight size={12} className="text-white/20" />
                      <span className="text-white font-bold text-sm">
                        {isTarget ? "Me" : r.target_email.split('@')[0]}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-white/20 font-mono flex items-center gap-1 uppercase">
                        <Hash size={10} /> {r.id}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-5 text-white/40 font-medium text-xs max-w-[200px] truncate">
                    {r.purpose || "No purpose provided"}
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-white font-black text-lg">{formatCurrency(r.amount)}</span>
                  </td>
                  <td className="px-6 py-5 text-center">
                    <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-widest uppercase border ${
                      r.status === "APPROVED" || r.status === "paid" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : 
                      r.status === "PENDING" || r.status === "pending_target" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-white/5 text-white/20 border-white/10"
                    }`}>
                      {r.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {canPay && onPay && (
                        <button
                          onClick={() => onPay(r)}
                          className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-95 flex items-center gap-2"
                        >
                          <CheckCircle2 size={14} /> Pay
                        </button>
                      )}
                      {canCancel && (
                        <button
                          onClick={() => onCancel(r)}
                          title="Cancel Request"
                          className="p-2.5 hover:bg-rose-500/10 rounded-xl text-white/20 hover:text-rose-400 transition-all border border-transparent hover:border-rose-500/20"
                        >
                          <XCircle size={18} />
                        </button>
                      )}
                      <button
                        onClick={() => onViewDetails(r)}
                        className="p-2.5 hover:bg-white/10 rounded-xl text-white/20 hover:text-white transition-all group/btn border border-transparent hover:border-white/10"
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

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-white/5 bg-white/5 flex items-center justify-between">
          <p className="text-xs text-white/20 font-medium">
            Showing <span className="font-bold text-white/60">{(currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-bold text-white/60">{Math.min(currentPage * itemsPerPage, filteredData.length)}</span> of <span className="font-bold text-white/60">{filteredData.length}</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => p - 1)}
              className="p-2 rounded-xl border border-white/10 text-white/20 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-1">
              {[...Array(totalPages)].map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
                    currentPage === i + 1 ? "bg-white text-slate-900 shadow-xl" : "text-white/20 hover:text-white/60 hover:bg-white/5"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
              className="p-2 rounded-xl border border-white/10 text-white/20 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}



