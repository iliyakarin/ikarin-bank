"use client";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { formatCurrency } from "@/lib/transactionUtils";
import { Account } from "@/lib/api/accounts";

interface AccountSelectorProps {
  accounts: Account[];
  selectedId: number | "";
  onSelect: (id: number | "") => void;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isLoading?: boolean;
  label?: string;
}

export default function AccountSelector({
  accounts,
  selectedId,
  onSelect,
  isOpen,
  setIsOpen,
  isLoading,
  label = "Source Account"
}: AccountSelectorProps) {
  const selectedAccount = selectedId === "" 
    ? accounts.find(a => a.is_main) 
    : accounts.find(a => a.id === selectedId);

  return (
    <div className="space-y-3 relative">
      <label className="block text-slate-700 font-bold text-sm uppercase tracking-wider flex justify-between">
        <span>{label}</span>
        {selectedId !== "" && (
          <span
            className="text-[10px] text-indigo-600 cursor-pointer hover:underline font-black tracking-widest"
            onClick={() => onSelect("")}
          >
            Reset to Default
          </span>
        )}
      </label>
      <div className="relative group">
        <div
          onClick={() => isLoading ? null : setIsOpen(!isOpen)}
          className={`w-full bg-slate-50 border ${isOpen ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-slate-200'} rounded-2xl px-4 py-4 text-slate-900 cursor-pointer hover:bg-slate-100 transition-all flex items-center justify-between shadow-sm`}
        >
          <span className="truncate font-bold text-sm">
            {selectedAccount ? (
              `${selectedAccount.name || (selectedAccount.is_main ? 'Main Account' : 'Account')} - ${(selectedAccount.masked_account_number ?? selectedAccount.account_number ?? '****').slice(-4)} - ${formatCurrency(selectedAccount.balance)}`
            ) : "Select an account"}
          </span>
          <ChevronDown
            className={`text-slate-300 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
            size={20}
          />
        </div>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="absolute z-[100] w-full mt-2 bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
            >
              <div className="p-2 space-y-1">
                {accounts.map(acc => (
                  <div
                    key={acc.id}
                    onClick={() => {
                      onSelect(acc.id);
                      setIsOpen(false);
                    }}
                    className={`px-4 py-3 rounded-xl cursor-pointer transition-all ${selectedId === acc.id || (selectedId === "" && acc.is_main) ? 'bg-indigo-50 text-indigo-700 font-bold border border-indigo-100' : 'hover:bg-slate-50 text-slate-600 border border-transparent'}`}
                  >
                    <span className="block truncate text-sm font-bold">{acc.name || (acc.is_main ? 'Main Account' : 'Account')} - {(acc.masked_account_number ?? acc.account_number ?? '****').slice(-4)}</span>
                    <span className="text-[10px] font-black uppercase tracking-widest opacity-60">{formatCurrency(acc.balance)}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

