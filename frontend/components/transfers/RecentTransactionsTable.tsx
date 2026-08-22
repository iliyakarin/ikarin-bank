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
  Hash,
  Send,
  Zap,
  Landmark,
  Clock
} from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { ActivityEvent } from "@/lib/api/activity";
import { formatMerchantName, formatFedRailBadge } from "@/lib/neobank/utils";

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
      <div className="p-12 text-center text-white/20 bg-white/5 rounded-2xl border border-dashed border-white/10">
        <ArrowRightLeft size={48} className="mx-auto mb-4 opacity-10" />
        <p className="text-lg font-medium text-white/60">No recent transfers.</p>
        <p className="text-sm">Your P2P transfers will appear here.</p>
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
            placeholder="Search by details or ID..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all font-sans"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex bg-white/5 border border-white/10 rounded-xl p-1">
            {(["all", "sent", "received"] as const).map((type) => (
              <button
                key={type}
                onClick={() => {
                  setFilterType(type);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                  filterType === type ? "bg-white text-slate-900 shadow-sm" : "text-white/40 hover:text-white/60"
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
            <tr className="text-white/30 uppercase text-[10px] font-black tracking-[0.2em] border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4">Transaction / Event</th>
              <th className="px-6 py-4">Type</th>
              <th className="px-6 py-4 text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {paginatedData.map((tx) => {
              const isDebit = tx.action === 'sent' || tx.title.toLowerCase().includes('sent');
              
              // Extract details safely
              let parsedDetails: any = null;
              try {
                if (tx.details) {
                  parsedDetails = typeof tx.details === 'string' ? JSON.parse(tx.details) : tx.details;
                }
              } catch (e) {}

              // Extract clean amount
              let formattedAmt = '---';
              if (parsedDetails?.amount != null) {
                formattedAmt = formatCurrency(parsedDetails.amount);
              } else {
                const match = tx.title.match(/\$?(\d+(?:\.\d+)?)/);
                if (match) {
                  const num = parseFloat(match[1]);
                  formattedAmt = `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                }
              }

              // Extract counterparty title
              let displayTitle = tx.title;
              if (parsedDetails?.recipient_email) {
                displayTitle = `To ${parsedDetails.recipient_email}`;
              } else if (parsedDetails?.sender_email) {
                displayTitle = `From ${parsedDetails.sender_email}`;
              } else if (parsedDetails?.counterparty) {
                displayTitle = `${isDebit ? 'To' : 'From'} ${parsedDetails.counterparty}`;
              }

              const rawDate = tx.event_time || '';
              const dateObj = new Date(rawDate.endsWith('Z') ? rawDate : rawDate + 'Z');
              const dateFormatted = !isNaN(dateObj.getTime())
                ? dateObj.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
                : 'Recent';

              return (
                <motion.tr
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  key={tx.event_id}
                  className="group hover:bg-white/5 transition-colors"
                >
                  <td className="px-6 py-5 text-white">
                    <div className="flex items-center gap-4">
                      <div className={`p-2.5 rounded-xl ${isDebit ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                        {isDebit ? <ArrowUpRight size={18} /> : <ArrowDownLeft size={18} />}
                      </div>
                      <div className="min-w-0">
                        <span className="font-bold block leading-tight text-sm truncate max-w-[320px]">
                          {displayTitle}
                        </span>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-white/30 font-bold uppercase tracking-wider">
                            {dateFormatted}
                          </span>
                          <span className="text-white/10">•</span>
                          <span className="text-[9px] text-white/30 font-mono flex items-center gap-1">
                            <Hash size={10} /> {tx.event_id.slice(0, 8)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-purple-300 text-[10px] font-bold uppercase tracking-widest bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                      {tx.category || 'P2P'} • {tx.action?.toUpperCase() || 'TRANSFER'}
                    </span>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <span className={`font-mono font-black text-base ${isDebit ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {formattedAmt !== '---' && (isDebit ? '-' : '+')}{formattedAmt}
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
        <div className="p-4 border-t border-white/5 bg-white/5 flex items-center justify-between">
          <p className="text-xs text-white/40 font-medium">
            Showing <span className="font-bold text-white/80">{(currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-bold text-white/80">{Math.min(currentPage * itemsPerPage, filteredData.length)}</span> of <span className="font-bold text-white/80">{filteredData.length}</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => p - 1)}
              className="p-2 rounded-xl border border-white/10 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-1">
              {[...Array(totalPages)].map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 rounded-xl text-xs font-bold font-mono transition-all ${
                    currentPage === i + 1 ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/20' : 'text-white/40 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
              className="p-2 rounded-xl border border-white/10 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
