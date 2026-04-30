"use client";
import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Calendar, 
  Trash2, 
  Eye, 
  Search, 
  ChevronLeft, 
  ChevronRight,
  Hash
} from "lucide-react";
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
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const filteredData = useMemo(() => {
    return payments.filter(p => {
      const matchesSearch = 
        p.recipient_email.toLowerCase().includes(search.toLowerCase()) || 
        p.id.toString().toLowerCase().includes(search.toLowerCase());
      
      const matchesStatus = filterStatus === "ALL" || p.status.toUpperCase() === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [payments, search, filterStatus]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

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
    <div className="w-full flex flex-col h-full">
      {/* Table Controls */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search recipient or ID..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex bg-white border border-slate-200 rounded-xl p-1">
            {["ALL", "ACTIVE", "PAUSED", "CANCELLED"].map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                  filterStatus === status ? "bg-slate-900 text-white shadow-sm" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[650px]">
          <thead>
            <tr className="text-slate-400 uppercase text-[10px] font-black tracking-[0.2em] border-b border-slate-100 bg-slate-50/30">
              <th className="px-6 py-4">Recipient / ID</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4">Frequency</th>
              <th className="px-6 py-4 text-center">Status</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginatedData.map((p) => (
              <motion.tr
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                key={p.id}
                className="group hover:bg-slate-50 transition-colors"
              >
                <td className="px-6 py-5">
                  <span className="text-slate-800 font-bold block leading-tight uppercase tracking-tight text-sm truncate max-w-[200px]">
                    {p.recipient_email}
                  </span>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[9px] text-slate-300 font-mono flex items-center gap-1 uppercase">
                      <Hash size={10} /> {p.id}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <span className="text-slate-900 font-black text-lg">{formatCurrency(p.amount)}</span>
                </td>
                <td className="px-6 py-5">
                  <div className="flex items-center gap-2 text-slate-500 text-[10px] font-black uppercase tracking-widest">
                    <Calendar size={14} className="text-indigo-400" />
                    <span>{p.frequency}</span>
                  </div>
                </td>
                <td className="px-6 py-5 text-center">
                  <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-widest uppercase border ${
                    p.status.toUpperCase() === "ACTIVE" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : 
                    "bg-slate-50 text-slate-400 border-slate-200"
                  }`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-6 py-5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => onViewDetails(p)}
                      className="p-2.5 hover:bg-slate-100 rounded-xl text-slate-300 hover:text-indigo-600 transition-all group/btn border border-transparent hover:border-slate-200"
                      title="View Details"
                    >
                      <Eye size={18} className="group-hover/btn:scale-110 transition-transform" />
                    </button>
                    {(p.status.toUpperCase() === "ACTIVE") && (
                      <button
                        onClick={() => onCancel(p)}
                        className="p-2.5 hover:bg-rose-50 rounded-xl text-slate-300 hover:text-rose-500 transition-all group/btn border border-transparent hover:border-rose-100"
                        title="Cancel Subscription"
                      >
                        <Trash2 size={18} className="group-hover/btn:scale-110 transition-transform" />
                      </button>
                    )}
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <p className="text-xs text-slate-400 font-medium">
            Showing <span className="font-bold text-slate-600">{(currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-bold text-slate-600">{Math.min(currentPage * itemsPerPage, filteredData.length)}</span> of <span className="font-bold text-slate-600">{filteredData.length}</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => p - 1)}
              className="p-2 rounded-xl border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-1">
              {[...Array(totalPages)].map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
                    currentPage === i + 1 ? "bg-indigo-600 text-white shadow-md shadow-indigo-200" : "text-slate-400 hover:text-slate-600 hover:bg-white"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
              className="p-2 rounded-xl border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


