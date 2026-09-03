"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ArrowLeftRight, ArrowRight, Wallet, Sparkles, Plus } from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import { toCents, formatCurrency } from "@/lib/transactionUtils";
import { Account, createSubAccount } from "@/lib/api/accounts";
import { createInternalTransfer } from "@/lib/api/transfers";
import { ApiError } from "@/lib/api/client";

interface BetweenAccountsTabProps {
  accounts: Account[];
  onSuccess: (txId: string) => void;
  onError: (message: string) => void;
  initialFromId?: number;
  initialToId?: number;
  onRefreshAccounts?: () => Promise<void>;
}

export default function BetweenAccountsTab({
  accounts,
  onSuccess,
  onError,
  initialFromId,
  initialToId,
  onRefreshAccounts,
}: BetweenAccountsTabProps) {
  const mainAccount = accounts.find((a) => a.is_main) || accounts[0];
  const subAccounts = accounts.filter((a) => !a.is_main);

  const [fromAccountId, setFromAccountId] = useState<number>(
    initialFromId || mainAccount?.id || 1
  );
  const [toAccountId, setToAccountId] = useState<number>(
    initialToId || subAccounts[0]?.id || 0
  );
  const [amount, setAmount] = useState("");
  const [commentary, setCommentary] = useState("");
  const [loading, setLoading] = useState(false);
  const [creatingSavings, setCreatingSavings] = useState(false);

  // Update default destination when accounts load
  useEffect(() => {
    if (accounts.length > 1) {
      if (!toAccountId || toAccountId === fromAccountId) {
        const otherAccount = accounts.find((a) => a.id !== fromAccountId);
        if (otherAccount) setToAccountId(otherAccount.id);
      }
    }
  }, [accounts, fromAccountId, toAccountId]);

  const fromAccount = accounts.find((a) => a.id === fromAccountId);
  const toAccount = accounts.find((a) => a.id === toAccountId);

  const handleSwap = () => {
    if (!toAccount || !fromAccount) return;
    const oldFrom = fromAccountId;
    setFromAccountId(toAccountId);
    setToAccountId(oldFrom);
  };

  const handleQuickChip = (val: string) => {
    if (val === "max") {
      if (fromAccount) {
        setAmount((fromAccount.balance / 100).toFixed(2));
      }
    } else {
      setAmount(val);
    }
  };

  const handleCreateDefaultSavings = async () => {
    setCreatingSavings(true);
    try {
      await createSubAccount("High Yield Savings");
      if (onRefreshAccounts) {
        await onRefreshAccounts();
      }
    } catch (err: any) {
      onError(err instanceof ApiError ? (err.detail?.detail || "Failed to create savings vault") : err.message);
    } finally {
      setCreatingSavings(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cents = toCents(amount);

    if (cents <= 0) {
      onError("Please specify a valid transfer amount greater than $0.00.");
      return;
    }

    if (!fromAccountId || !toAccountId) {
      onError("Please select both source and destination accounts.");
      return;
    }

    if (fromAccountId === toAccountId) {
      onError("Source and destination accounts must be different.");
      return;
    }

    if (fromAccount && fromAccount.balance < cents) {
      onError(`Insufficient funds in ${fromAccount.name}. Available: ${formatCurrency(fromAccount.balance)}`);
      return;
    }

    setLoading(true);
    try {
      const cleanCommentary = DOMPurify.sanitize(commentary) || "Internal account transfer";
      const res = await createInternalTransfer({
        from_account_id: fromAccountId,
        to_account_id: toAccountId,
        amount: cents,
        commentary: cleanCommentary,
        idempotency_key: `int-transfer-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      });

      onSuccess(res.message || "Internal transfer completed");
      setAmount("");
      setCommentary("");
    } catch (err: any) {
      if (err instanceof ApiError) {
        onError(err.detail?.detail || "Internal transfer failed");
      } else {
        onError(err.message || "Failed to execute internal transfer");
      }
    } finally {
      setLoading(false);
    }
  };

  // If user only has 1 account, offer to spawn High Yield Savings sub-account
  if (accounts.length <= 1) {
    return (
      <div className="py-8 px-4 text-center space-y-6">
        <div className="w-16 h-16 rounded-3xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/30 shadow-xl">
          <Sparkles size={28} />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-black text-white uppercase tracking-tight">
            Enable High-Yield Savings Vault
          </h3>
          <p className="text-sm text-white/60 max-w-md mx-auto">
            You currently have a single checking account. Initialize your Treasury High-Yield Savings Vault (4.85% APY) to move funds seamlessly between accounts.
          </p>
        </div>
        <button
          type="button"
          onClick={handleCreateDefaultSavings}
          disabled={creatingSavings}
          className="px-6 py-3.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold rounded-2xl transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2 mx-auto disabled:opacity-50"
        >
          <Plus size={18} />
          <span>{creatingSavings ? "Creating Vault..." : "Create High-Yield Savings Vault"}</span>
        </button>
      </div>
    );
  }

  const QUICK_AMOUNTS = ["25.00", "100.00", "500.00", "1000.00", "5000.00"];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Account Selectors with Swap */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr] gap-3 items-center">
        {/* Source Account */}
        <div className="space-y-2">
          <label className="block text-white/60 font-bold text-xs uppercase tracking-wider">
            Transfer From
          </label>
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 space-y-2">
            <select
              value={fromAccountId}
              onChange={(e) => setFromAccountId(parseInt(e.target.value, 10))}
              className="w-full bg-transparent text-white font-bold text-sm focus:outline-none cursor-pointer"
            >
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id} className="bg-slate-900 text-white">
                  {acc.name} ({acc.is_main ? "Primary" : "Sub-Account"})
                </option>
              ))}
            </select>
            <div className="flex items-center justify-between text-xs pt-1 border-t border-white/5">
              <span className="text-white/40 font-medium">Available Balance:</span>
              <span className="font-mono font-bold text-emerald-400">
                {fromAccount ? formatCurrency(fromAccount.balance) : "$0.00"}
              </span>
            </div>
          </div>
        </div>

        {/* Swap Direction Button */}
        <div className="flex justify-center pt-5">
          <motion.button
            type="button"
            whileHover={{ scale: 1.1, rotate: 180 }}
            whileTap={{ scale: 0.9 }}
            onClick={handleSwap}
            className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-300 hover:text-white flex items-center justify-center transition-all shadow-lg"
            title="Swap Source & Destination"
          >
            <ArrowLeftRight size={18} />
          </motion.button>
        </div>

        {/* Destination Account */}
        <div className="space-y-2">
          <label className="block text-white/60 font-bold text-xs uppercase tracking-wider">
            Transfer To
          </label>
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 space-y-2">
            <select
              value={toAccountId}
              onChange={(e) => setToAccountId(parseInt(e.target.value, 10))}
              className="w-full bg-transparent text-white font-bold text-sm focus:outline-none cursor-pointer"
            >
              {accounts.map((acc) => (
                <option
                  key={acc.id}
                  value={acc.id}
                  disabled={acc.id === fromAccountId}
                  className="bg-slate-900 text-white"
                >
                  {acc.name} {acc.id === fromAccountId ? "(Source)" : `(${acc.is_main ? "Primary" : "Sub-Account"})`}
                </option>
              ))}
            </select>
            <div className="flex items-center justify-between text-xs pt-1 border-t border-white/5">
              <span className="text-white/40 font-medium">Current Balance:</span>
              <span className="font-mono font-bold text-teal-300">
                {toAccount ? formatCurrency(toAccount.balance) : "$0.00"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Amount Input */}
      <div className="space-y-3">
        <label className="block text-white/60 font-bold text-sm uppercase tracking-wider">
          Amount (USD)
        </label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 font-bold text-xl">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.01"
            min="0.01"
            className="w-full bg-white/5 border border-white/10 rounded-2xl pl-10 pr-4 py-4 text-white font-mono font-bold text-2xl placeholder:text-white/10 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 transition-all"
            required
          />
        </div>

        {/* Quick Amount Chips */}
        <div className="flex items-center gap-2 flex-wrap pt-1">
          {QUICK_AMOUNTS.map((amt) => (
            <button
              key={amt}
              type="button"
              onClick={() => handleQuickChip(amt)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
                amount === amt
                  ? "bg-emerald-500 text-slate-950 shadow-md"
                  : "bg-white/5 hover:bg-white/10 text-white/60 hover:text-white border border-white/10"
              }`}
            >
              ${amt}
            </button>
          ))}
          <button
            type="button"
            onClick={() => handleQuickChip("max")}
            className="px-3 py-1.5 rounded-xl text-xs font-mono font-bold bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 transition-all"
          >
            Max Available
          </button>
        </div>
      </div>

      {/* Optional Memo */}
      <div className="space-y-2">
        <label className="block text-white/60 font-bold text-xs uppercase tracking-wider">
          Commentary / Memo <span className="text-white/30 font-normal normal-case">(Optional)</span>
        </label>
        <input
          type="text"
          value={commentary}
          onChange={(e) => setCommentary(e.target.value)}
          placeholder="e.g. Allocation to High-Yield Savings Vault"
          className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3.5 text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 transition-all text-sm"
        />
      </div>

      {/* Yield note if destination is vault/savings */}
      {toAccount && (toAccount.name.toLowerCase().includes("savings") || toAccount.name.toLowerCase().includes("vault")) && (
        <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <div className="text-xs text-emerald-300">
            Deposited funds automatically accrue <span className="font-bold">4.85% APY</span> compounded daily and backed by KarinBank Treasury.
          </div>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !amount || parseFloat(amount) <= 0}
        className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:opacity-40 text-slate-950 font-black py-5 rounded-[1.5rem] flex items-center justify-center gap-3 transition-all shadow-xl shadow-emerald-500/20 hover:shadow-emerald-500/30 uppercase tracking-widest text-sm"
      >
        {loading ? (
          "Settling Internal Transfer..."
        ) : (
          <>
            <ArrowLeftRight size={20} />
            <span>Transfer {amount ? `$${amount}` : ""} Between Accounts</span>
            <ArrowRight size={20} />
          </>
        )}
      </button>
    </form>
  );
}
