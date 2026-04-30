"use client";
import { motion } from "framer-motion";
import { ArrowRightLeft, User, DollarSign, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { ActivityEvent } from "@/lib/api/activity";

interface RecentTransactionsTableProps {
  transactions: ActivityEvent[];
}

export default function RecentTransactionsTable({
  transactions,
}: RecentTransactionsTableProps) {
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
    <div className="w-full">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-slate-400 uppercase text-[10px] font-black tracking-[0.2em] border-b border-slate-100 bg-slate-50/30">
            <th className="px-6 py-4">Event</th>
            <th className="px-6 py-4">Transaction Details</th>
            <th className="px-6 py-4 text-right">Amount</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {transactions.map((tx) => {
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
                    <div>
                      <span className="text-slate-900 font-bold block leading-tight text-sm">
                        {tx.title}
                      </span>
                      <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider">
                        {new Date(tx.event_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <p className="text-slate-500 text-xs font-medium">
                    {tx.category.toUpperCase()} • {tx.action.toUpperCase()}
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
  );
}

