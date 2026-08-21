"use client";
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Building2, 
  Zap, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  Layers, 
  Landmark,
  BadgeCheck,
  Clock,
  Search
} from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import { toCents } from "@/lib/transactionUtils";
import { Account } from "@/lib/api/accounts";
import { 
  createWireTransfer, 
  createFedNowTransfer, 
  createACHTransfer,
  lookupFedRouting
} from "@/lib/api/transfers";
import { validateRoutingNumber } from "@/lib/routingUtils";
import { ApiError } from "@/lib/api/client";
import AccountSelector from "./AccountSelector";

interface FedTransferTabProps {
  accounts: Account[];
  onSuccess: (txId: string, message?: string) => void;
  onError: (message: string) => void;
}

type FedRail = "wire" | "fednow" | "ach";

export default function FedTransferTab({
  accounts,
  onSuccess,
  onError,
}: FedTransferTabProps) {
  const [rail, setRail] = useState<FedRail>("fednow");
  const [routingNumber, setRoutingNumber] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [sourceAccountId, setSourceAccountId] = useState<number | "">("");
  const [isSourceOpen, setIsSourceOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Live Fed Directory Info
  const [lookupLoading, setLookupLoading] = useState(false);
  const [directoryInfo, setDirectoryInfo] = useState<any | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Auto-validate and lookup routing number when 9 digits entered
  useEffect(() => {
    const cleanRtn = routingNumber.replace(/\D/g, "");
    if (cleanRtn.length === 9) {
      const localVal = validateRoutingNumber(cleanRtn);
      if (!localVal.valid) {
        setValidationError(localVal.errors[0] || "Invalid ABA Routing Checksum");
        setDirectoryInfo(null);
        return;
      }

      setValidationError(null);
      setLookupLoading(true);
      lookupFedRouting(cleanRtn)
        .then((res) => {
          if (res.valid && res.institution) {
            setDirectoryInfo({
              institution: res.institution,
              district: res.district,
            });
            setValidationError(null);
          } else {
            setDirectoryInfo(null);
            setValidationError(res.errors?.[0] || "Routing number not found in Federal Reserve Directory");
          }
        })
        .catch(() => {
          setDirectoryInfo(null);
        })
        .finally(() => {
          setLookupLoading(false);
        });
    } else {
      setDirectoryInfo(null);
      if (cleanRtn.length > 0 && cleanRtn.length < 9) {
        setValidationError(`Entering routing number (${cleanRtn.length}/9 digits)`);
      } else {
        setValidationError(null);
      }
    }
  }, [routingNumber]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cents = toCents(amount);
    const cleanRtn = routingNumber.replace(/\D/g, "");
    const cleanAcct = accountNumber.trim();
    const cleanName = recipientName.trim();
    const cleanRef = DOMPurify.sanitize(reference.trim());

    if (!cleanRtn || cleanRtn.length !== 9) {
      onError("Please enter a valid 9-digit ABA routing number.");
      return;
    }
    if (!cleanAcct) {
      onError("Please provide a beneficiary account number.");
      return;
    }
    if (!cleanName) {
      onError("Please enter the recipient or company name.");
      return;
    }
    if (!amount || cents <= 0) {
      onError("Please provide a valid transfer amount.");
      return;
    }

    const selectedAccount = accounts.find((a) => a.id === sourceAccountId) || accounts[0];
    if (!selectedAccount) {
      onError("No funding account available.");
      return;
    }

    setLoading(true);
    try {
      if (rail === "wire") {
        const res = await createWireTransfer({
          account_id: selectedAccount.id,
          amount: cents,
          receiver_routing: cleanRtn,
          receiver_name: cleanName,
          receiver_account: cleanAcct,
          payment_reference: cleanRef || "Fedwire Transfer",
        });
        onSuccess(
          res.transaction_id,
          `Fedwire RTGS settled! IMAD: ${res.imad || "Generated"} | OMAD: ${res.omad || "Generated"}`
        );
      } else if (rail === "fednow") {
        const res = await createFedNowTransfer({
          account_id: selectedAccount.id,
          amount: cents,
          creditor_routing: cleanRtn,
          creditor_name: cleanName,
          creditor_account: cleanAcct,
          remittance_info: cleanRef || "Instant Payment",
        });
        onSuccess(
          res.transaction_id,
          `FedNow 24/7 instant payment cleared! End-to-End ID: ${res.end_to_end_id}`
        );
      } else {
        const res = await createACHTransfer({
          account_id: selectedAccount.id,
          amount: cents,
          receiver_routing: cleanRtn,
          receiver_name: cleanName,
          receiver_account: cleanAcct,
          payment_description: cleanRef || "FedACH Transfer",
        });
        onSuccess(
          res.transaction_id,
          `FedACH origination submitted! Trace: ${res.trace_number}`
        );
      }

      setAmount("");
      setReference("");
      setAccountNumber("");
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail?.detail || err.message || "Federal Reserve transfer failed";
        onError(typeof detail === "string" ? detail : JSON.stringify(detail));
      } else {
        onError("Network connection error. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      {/* Rail Selector Tabs */}
      <div className="grid grid-cols-3 gap-3 p-1.5 bg-black/40 rounded-2xl border border-white/5 backdrop-blur-md">
        <button
          type="button"
          onClick={() => setRail("fednow")}
          className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-xs md:text-sm transition-all duration-300 ${
            rail === "fednow"
              ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-300 border border-emerald-500/40 shadow-lg shadow-emerald-500/10"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
          }`}
        >
          <Zap className={`w-4 h-4 ${rail === "fednow" ? "text-emerald-400 animate-pulse" : ""}`} />
          <span>FedNow® Instant</span>
          <span className="hidden md:inline px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300">24/7</span>
        </button>

        <button
          type="button"
          onClick={() => setRail("wire")}
          className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-xs md:text-sm transition-all duration-300 ${
            rail === "wire"
              ? "bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-300 border border-blue-500/40 shadow-lg shadow-blue-500/10"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
          }`}
        >
          <Landmark className="w-4 h-4 text-blue-400" />
          <span>Fedwire® RTGS</span>
          <span className="hidden md:inline px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300">High Value</span>
        </button>

        <button
          type="button"
          onClick={() => setRail("ach")}
          className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-xs md:text-sm transition-all duration-300 ${
            rail === "ach"
              ? "bg-gradient-to-r from-purple-500/20 to-indigo-500/20 text-purple-300 border border-purple-500/40 shadow-lg shadow-purple-500/10"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
          }`}
        >
          <Layers className="w-4 h-4 text-purple-400" />
          <span>FedACH®</span>
          <span className="hidden md:inline px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300">Direct</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Source Account */}
        <div>
          <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
            Funding Account
          </label>
          <AccountSelector
            accounts={accounts}
            selectedId={sourceAccountId}
            isOpen={isSourceOpen}
            setIsOpen={setIsSourceOpen}
            onSelect={(id) => {
              setSourceAccountId(id);
              setIsSourceOpen(false);
            }}
          />
        </div>

        {/* Recipient Bank Routing Lookup */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Recipient ABA Routing Number (9 Digits)
          </label>
          <div className="relative">
            <input
              type="text"
              maxLength={9}
              value={routingNumber}
              onChange={(e) => setRoutingNumber(e.target.value.replace(/\D/g, "").slice(0, 9))}
              placeholder="e.g. 021000021 (Chase) or 111000012 (BofA)"
              className="w-full bg-zinc-900/80 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 font-mono tracking-wider transition-all"
            />
            <div className="absolute right-3 top-3 flex items-center gap-2">
              {lookupLoading && (
                <div className="w-5 h-5 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
              )}
              {directoryInfo && !lookupLoading && (
                <BadgeCheck className="w-5 h-5 text-emerald-400" />
              )}
            </div>
          </div>

          {/* Validation or Directory Preview */}
          <AnimatePresence mode="wait">
            {directoryInfo && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="p-3.5 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex items-start gap-3"
              >
                <Building2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="flex-1 text-xs">
                  <div className="font-semibold text-emerald-200 text-sm">
                    {directoryInfo.institution.name}
                  </div>
                  <div className="text-zinc-400 flex items-center gap-2 mt-0.5">
                    <span>{directoryInfo.institution.city}, {directoryInfo.institution.state}</span>
                    <span>•</span>
                    <span>{directoryInfo.district?.name || "Federal Reserve System"}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {directoryInfo.institution.fednow_participant && (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-medium text-[10px]">
                        FedNow 24/7
                      </span>
                    )}
                    {directoryInfo.institution.fedwire_participant && (
                      <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium text-[10px]">
                        Fedwire RTGS
                      </span>
                    )}
                    {directoryInfo.institution.fedach_participant && (
                      <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-medium text-[10px]">
                        FedACH Participant
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {validationError && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                className="text-xs text-amber-400/90 flex items-center gap-1.5 px-1"
              >
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{validationError}</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Beneficiary Account & Name */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Beneficiary Name
            </label>
            <input
              type="text"
              value={recipientName}
              onChange={(e) => setRecipientName(e.target.value)}
              placeholder="e.g. Acme Industrial Corp"
              className="w-full bg-zinc-900/80 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/50 transition-all text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Beneficiary Account Number
            </label>
            <input
              type="text"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              placeholder="e.g. 9876543210"
              className="w-full bg-zinc-900/80 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/50 font-mono transition-all text-sm"
            />
          </div>
        </div>

        {/* Amount & Reference */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Amount (USD)
            </label>
            <div className="relative">
              <span className="absolute left-4 top-3 text-zinc-400 font-semibold">$</span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full bg-zinc-900/80 border border-white/10 rounded-xl pl-8 pr-4 py-3 text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/50 font-semibold text-base transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              {rail === "wire" ? "Payment Reference (IMAD/OMAD Ref)" : "Remittance Memo"}
            </label>
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder={rail === "wire" ? "e.g. INVOICE #8920 / ESCROW" : "e.g. Dinner reimbursement"}
              className="w-full bg-zinc-900/80 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/50 text-sm transition-all"
            />
          </div>
        </div>

        {/* Rail Speed & Security Notice */}
        <div className="p-3.5 bg-white/[0.02] border border-white/5 rounded-xl flex items-center justify-between text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-zinc-500" />
            <span>
              {rail === "fednow" && "Settlement Speed: Immediate (< 1 second, 24/7/365)"}
              {rail === "wire" && "Settlement Speed: Same-Day Real-Time Gross Settlement (RTGS)"}
              {rail === "ach" && "Settlement Speed: Same-Day / Next-Day FedACH Window"}
            </span>
          </div>
          <div className="flex items-center gap-1 text-zinc-500">
            <ShieldCheck className="w-4 h-4 text-emerald-400/80" />
            <span>Fed Verified</span>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-4 rounded-xl font-semibold text-white shadow-lg transition-all duration-300 flex items-center justify-center gap-2 ${
            rail === "fednow"
              ? "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-emerald-500/20"
              : rail === "wire"
              ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-500/20"
              : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-purple-500/20"
          } ${loading ? "opacity-60 cursor-not-allowed" : ""}`}
        >
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Transmitting to Federal Reserve System...</span>
            </div>
          ) : (
            <>
              <span>
                {rail === "fednow" && "Send Instant FedNow® Transfer"}
                {rail === "wire" && "Originate Fedwire® RTGS Transfer"}
                {rail === "ach" && "Submit FedACH® Direct Origination"}
              </span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>
    </motion.div>
  );
}
