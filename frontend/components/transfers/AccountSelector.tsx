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
      <label className="block text-white font-semibold flex justify-between">
        <span>{label}</span>
        {selectedId !== "" && (
          <span
            className="text-xs text-purple-400 cursor-pointer hover:underline"
            onClick={() => onSelect("")}
          >
            Reset to Default
          </span>
        )}
      </label>
      <div className="relative">
        <div
          onClick={() => isLoading ? null : setIsOpen(!isOpen)}
          className={`w-full bg-white/5 border ${isOpen ? 'border-purple-400' : 'border-white/10'} rounded-xl px-4 py-3 text-white cursor-pointer hover:bg-white/10 transition-colors flex items-center justify-between shadow-inner`}
        >
          <span className="truncate">
            {selectedAccount ? (
              `${selectedAccount.name || (selectedAccount.is_main ? 'Main Account' : 'Account')} - ${(selectedAccount.masked_account_number ?? selectedAccount.account_number ?? '****').slice(-4)} - ${formatCurrency(selectedAccount.balance)}`
            ) : "Select an account"}
          </span>
          <ChevronDown
            className={`text-white/40 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            size={20}
          />
        </div>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
              className="absolute z-[100] w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
            >
              <div className="p-2 space-y-1">
                {accounts.map(acc => (
                  <div
                    key={acc.id}
                    onClick={() => {
                      onSelect(acc.id);
                      setIsOpen(false);
                    }}
                    className={`px-4 py-3 rounded-lg cursor-pointer transition-colors ${selectedId === acc.id || (selectedId === "" && acc.is_main) ? 'bg-purple-500/20 text-purple-300 font-bold' : 'hover:bg-white/10 text-white'}`}
                  >
                    <span className="block truncate">{acc.name || (acc.is_main ? 'Main Account' : 'Account')} - {(acc.masked_account_number ?? acc.account_number ?? '****').slice(-4)}</span>
                    <span className="text-xs opacity-70">{formatCurrency(acc.balance)}</span>
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
