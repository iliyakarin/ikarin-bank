"use client";
import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ArrowRightLeft, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  Hash
} from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { ActivityEvent } from "@/lib/api/activity";

interface RecentTransactionsTableProps {
  transactions: ActivityEvent[];
}

export default function RecentTransactionsTable({
  transactions,
}: RecentTransactionsTableProps) {
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"all" | "sent" | "received">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const filteredData = useMemo(() => {
    return transactions.filter(tx => {
      const matchesSearch = tx.title.toLowerCase().includes(search.toLowerCase()) || 
                            tx.event_id.toLowerCase().includes(search.toLowerCase());
      const isDebit = tx.action === 'sent' || tx.title.toLowerCase().includes('sent');
      const matchesType = filterType === "all" || (filterType === "sent" ? isDebit : !isDebit);
      return matchesSearch && matchesType;
    });
  }, [transactions, search, filterType]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  if (transactions.length === 0) {
    return (
      <div className="p-12 text-center text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
        <ArrowRightLeft size={48} className="mx-auto mb-4 opacity-20" />
        <p className="text-lg font-medium text-slate-600">No recent transfers.</p>
        <p className="text-sm">Your P2P transfers will appear here.</p>
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
            placeholder="Search by details or ID..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex bg-white border border-slate-200 rounded-xl p-1">
            {(["all", "sent", "received"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                  filterType === type ? "bg-slate-900 text-white shadow-sm" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="text-slate-400 uppercase text-[10px] font-black tracking-[0.2em] border-b border-slate-100 bg-slate-50/30">
              <th className="px-6 py-4">Transaction / Event</th>
              <th className="px-6 py-4">Type</th>
              <th className="px-6 py-4 text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginatedData.map((tx) => {
              const isDebit = tx.action === 'sent' || tx.title.toLowerCase().includes('sent');
              const amountMatch = tx.title.match(/\$(\d+\.\d+)/);
              const amountStr = amountMatch ? amountMatch[0] : '---';

              return (
                <motion.tr
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  key={tx.event_id}
                  className="group hover:bg-slate-50 transition-colors"
                >
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-4">
                      <div className={`p-2.5 rounded-xl ${isDebit ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}>
                        {isDebit ? <ArrowUpRight size={18} /> : <ArrowDownLeft size={18} />}
                      </div>
                      <div className="min-w-0">
                        <span className="text-slate-900 font-bold block leading-tight text-sm truncate max-w-[300px]">
                          {tx.title}
                        </span>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider">
                            {new Date(tx.event_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                          </span>
                          <span className="text-slate-300">•</span>
                          <span className="text-[9px] text-slate-300 font-mono flex items-center gap-1">
                            <Hash size={10} /> {tx.event_id}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest bg-slate-100 px-2 py-0.5 rounded w-fit">
                      {tx.category} • {tx.action}
                    </p>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <span className={`font-black text-lg ${isDebit ? 'text-rose-500' : 'text-emerald-600'}`}>
                       {isDebit ? '-' : '+'}{amountStr}
                    </span>
                  </td>
                </motion.tr>
              );
            })}
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


