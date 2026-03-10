"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import { useBalance } from "@/hooks/useDashboard";
import {
  Send,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Calendar,
  CreditCard,
  Clock,
  ChevronDown,
  HandCoins,
} from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import DatePicker from "@/components/ui/DatePicker";

export default function SendMoneyPage() {
  const { token, settings } = useAuth();
  const { accounts, loading: accountsLoading } = useBalance();

  // Global UI State
  const [activeTab, setActiveTab] = useState<
    "instant" | "scheduled" | "request"
  >("instant");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [txId, setTxId] = useState("");

  // One time transfer (formerly Instant Transfer) State
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [commentary, setCommentary] = useState("");
  const [sourceAccountId, setSourceAccountId] = useState<number | "">("");
  const [subscriberId, setSubscriberId] = useState("");
  const [isVendor, setIsVendor] = useState(false);

  // Request Transfer State
  const [requestEmail, setRequestEmail] = useState("");
  const [requestAmount, setRequestAmount] = useState("");
  const [requestPurpose, setRequestPurpose] = useState("");
  const [paymentRequests, setPaymentRequests] = useState<any[]>([]);
  const [isReqContactDropdownOpen, setIsReqContactDropdownOpen] =
    useState(false);

  // Counter Modal State
  const [counterModalOpen, setCounterModalOpen] = useState(false);
  const [counterReqId, setCounterReqId] = useState<number | null>(null);
  const [counterCurrentAmount, setCounterCurrentAmount] = useState<number>(0);
  const [counterNewAmount, setCounterNewAmount] = useState("");

  // Contacts State
  const [contacts, setContacts] = useState<any[]>([]);
  const [isContactDropdownOpen, setIsContactDropdownOpen] = useState(false);

  // Scheduled Transfer State
  const [schedRecipient, setSchedRecipient] = useState("");
  const [schedAmount, setSchedAmount] = useState("");
  const [frequency, setFrequency] = useState("Monthly");
  const [freqInterval, setFreqInterval] = useState("1");
  const [startDate, setStartDate] = useState("");
  const [endCondition, setEndCondition] = useState("Until Cancelled");
  const [endDate, setEndDate] = useState("");
  const [targetPayments, setTargetPayments] = useState("");
  const [reserveAmount, setReserveAmount] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("checking"); // Mock source
  const [schedSubscriberId, setSchedSubscriberId] = useState("");
  const [isSchedVendor, setIsSchedVendor] = useState(false);
  const [isVendorDropdownOpen, setIsVendorDropdownOpen] = useState(false);
  const [isSourceDropdownOpen, setIsSourceDropdownOpen] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showInstantConfirmation, setShowInstantConfirmation] = useState(false);

  // Scheduled History State
  const [scheduledHistory, setScheduledHistory] = useState<any[]>([]);
  const [scheduledHistoryLoading, setScheduledHistoryLoading] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelPaymentId, setCancelPaymentId] = useState<number | null>(null);
  const [cancelVendorName, setCancelVendorName] = useState("");

  // Instant History State
  const [instantHistory, setInstantHistory] = useState<any[]>([]);
  const [instantHistoryLoading, setInstantHistoryLoading] = useState(false);

  // Repeat Transfer State
  const [repeatModalOpen, setRepeatModalOpen] = useState(false);
  const [selectedRepeatTx, setSelectedRepeatTx] = useState<any>(null);
  const [repeatAmount, setRepeatAmount] = useState("");
  const [repeatCommentary, setRepeatCommentary] = useState("");
  const [repeatSourceAccountId, setRepeatSourceAccountId] = useState<number | "">("");
  const [repeatLoading, setRepeatLoading] = useState(false);
  const [isRepeatSourceDropdownOpen, setIsRepeatSourceDropdownOpen] = useState(false);

  // Mock Vendors from Simulator
  const [vendors, setVendors] = useState<any[]>([]);

  // Transaction Details Modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedTxDetails, setSelectedTxDetails] = useState<any>(null);

  useEffect(() => {
    // Check if recipient is a vendor for instant
    const vendorMatch = vendors.find(v => v.email === recipient);
    setIsVendor(!!vendorMatch);
  }, [recipient, vendors]);

  useEffect(() => {
    // Check if recipient is a vendor for scheduled
    const vendorMatch = vendors.find(v => v.email === schedRecipient);
    setIsSchedVendor(!!vendorMatch);
  }, [schedRecipient, vendors]);

  useEffect(() => {
    // Fetch mock vendors from our new simulator service proxy
    fetch("/api/v1/vendors", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.vendors) setVendors(data.vendors);
      })
      .catch((err) => {
        console.error("Failed to load mock vendors", err);
        setVendors([
          {
            id: "fallback",
            name: "Apple Music (Fallback)",
            email: "subscriptions@apple.com",
          },
        ]);
      });

    // Fetch contacts
    if (token) {
      fetch("/api/v1/contacts", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data)) setContacts(data);
        })
        .catch((err) => console.error("Failed to load contacts", err));
    }

    // Set today as default start date
    setStartDate(new Date().toISOString().split("T")[0]);

    fetchRequests();
    if (activeTab === "scheduled") {
      fetchScheduledPayments();
    } else if (activeTab === "instant") {
      fetchInstantHistory();
    }
  }, [activeTab]); // Refetch when tab changes

  const fetchInstantHistory = async () => {
    setInstantHistoryLoading(true);
    try {
      const res = await fetch(
        "/api/transactions?tx_type=transfer&days=30",
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (res.ok) {
        const data = await res.json();
        setInstantHistory(data.transactions || []);
      }
    } catch (err) {
      console.error("Failed to load instant transfer history", err);
    } finally {
      setInstantHistoryLoading(false);
    }
  };

  const fetchScheduledPayments = async () => {
    setScheduledHistoryLoading(true);
    try {
      const res = await fetch(
        "/api/v1/transfers/scheduled",
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (res.ok) {
        const data = await res.json();
        setScheduledHistory(data);
      }
    } catch (err) {
      console.error("Failed to load scheduled payments", err);
    } finally {
      setScheduledHistoryLoading(false);
    }
  };

  const handleCancelScheduled = (pmt: any) => {
    setCancelPaymentId(pmt.id);
    setCancelVendorName(pmt.recipient_email);
    setCancelModalOpen(true);
  };

  const confirmCancelScheduled = async () => {
    if (!cancelPaymentId) return;
    setCancelModalOpen(false);
    try {
      const res = await fetch(
        `/api/v1/transfers/scheduled/${cancelPaymentId}/cancel`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (res.ok) {
        setSuccessMessage(
          `Scheduled Payment to "${cancelVendorName}" was successfully canceled.`,
        );
        setSuccess(true);
        setTimeout(() => {
          setSuccess(false);
          setSuccessMessage("");
        }, 5000);
        fetchScheduledPayments(); // Refresh table
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to cancel");
      }
    } catch (err) {
      setError("Connection error");
    } finally {
      setCancelPaymentId(null);
      setCancelVendorName("");
    }
  };

  const fetchRequests = async () => {
    try {
      const res = await fetch("/api/v1/requests", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPaymentRequests(data);
      }
    } catch (err) {
      console.error("Failed to load payment requests", err);
    }
  };

  const handleConfirmRepeat = async () => {
    if (!selectedRepeatTx) return;
    setRepeatLoading(true);
    setError("");
    setSuccess(false);

    try {
      const isOutgoing = selectedRepeatTx.amount < 0;
      const targetEmail = isOutgoing
        ? selectedRepeatTx.recipient_email
        : selectedRepeatTx.sender_email;

      const cleanCommentary = DOMPurify.sanitize(repeatCommentary);
      const res = await fetch("/api/p2p-transfer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recipient_email: targetEmail,
          amount: parseFloat(repeatAmount),
          commentary: cleanCommentary || null,
          source_account_id: repeatSourceAccountId || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSuccess(true);
        setTxId(data.transaction_id);
        fetchInstantHistory();
        setRepeatModalOpen(false);
        setTimeout(() => setSuccess(false), 5000);
      } else {
        const data = await res.json();
        setError(data.detail || "Transfer failed");
      }
    } catch (err) {
      setError("Connection error. Please try again.");
    } finally {
      setRepeatLoading(false);
    }
  };

  const handleInstantSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (!recipient.trim() || !amount || parseFloat(amount) <= 0) {
      setError("Please provide a valid recipient and an amount greater than 0");
      return;
    }

    setShowInstantConfirmation(true);
  };

  const confirmAndSendInstant = async () => {
    setShowInstantConfirmation(false);
    setLoading(true);
    setError("");
    setSuccess(false);

    try {
      const cleanCommentary = DOMPurify.sanitize(commentary);
      const res = await fetch("/api/p2p-transfer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recipient_email: recipient,
          amount: parseFloat(amount),
          commentary: cleanCommentary || null,
          source_account_id: sourceAccountId || undefined,
          subscriber_id: subscriberId || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSuccess(true);
        setTxId(data.transaction_id);
        setRecipient("");
        setAmount("");
        fetchInstantHistory();
        setTimeout(() => setSuccess(false), 5000);
      } else {
        const data = await res.json();
        setError(data.detail || "Transfer failed");
      }
    } catch (err) {
      setError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleScheduledSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(false);

    const amt = parseFloat(schedAmount);
    if (!schedRecipient.trim() || !schedAmount || amt <= 0) {
      setError("Please provide a valid recipient and an amount greater than 0");
      setLoading(false);
      return;
    }

    // Business Rule: Scheduled Limit (e.g. max $5000)
    if (amt > 5000) {
      setError("Amount exceeds the maximum scheduled transfer limit of $5000.");
      setLoading(false);
      return;
    }

    // Validation: No past dates (local comparison)
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

    if (startDate < todayStr) {
      setError("Start date must be today or in the future.");
      setLoading(false);
      return;
    }

    // Expiration Conflict Check (Mock Expiry: Dec 31, 2028)
    const mockExpiry = new Date("2028-12-31");
    if (endCondition === "End Date" && endDate) {
      if (new Date(endDate) > mockExpiry) {
        setError(
          "The scheduled end date exceeds the expiration date (12/28) of your selected payment method.",
        );
        setLoading(false);
        return;
      }
    } else if (
      endCondition !== "End Date" &&
      (() => {
        const d = new Date(startDate);
        d.setFullYear(d.getFullYear() + 2);
        return d > mockExpiry;
      })()
    ) {
      // Rough heuristic for "Until Cancelled"
      setError(
        "Warning: This recurring payment extends beyond your payment method expiration (12/28). Please update funding source soon.",
      );
    }

    // Show confirmation modal
    setShowConfirmation(true);
  };

  const confirmAndScheduleTransfer = async () => {
    setShowConfirmation(false);
    const amt = parseFloat(schedAmount);

    try {
      const payload = {
        recipient_email: schedRecipient,
        amount: amt,
        frequency: frequency,
        frequency_interval: freqInterval,
        start_date: new Date(startDate).toISOString(),
        end_condition: endCondition,
        end_date:
          endCondition === "End Date" && endDate
            ? new Date(endDate).toISOString()
            : null,
        target_payments:
          endCondition === "Number of Payments" && targetPayments
            ? parseInt(targetPayments)
            : null,
        reserve_amount: reserveAmount,
        funding_account_id: sourceAccountId || undefined,
        subscriber_id: schedSubscriberId || undefined,
      };

      const res = await fetch(
        "/api/v1/transfers/scheduled",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        },
      );
      if (res.ok) {
        const data = await res.json();
        setSuccess(true);
        setTxId(data.scheduled_payment_id);
        setSchedRecipient("");
        setSchedAmount("");
        setTimeout(() => setSuccess(false), 5000);
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to create scheduled transfer");
      }
    } catch (err) {
      setError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(false);

    // Basic validation
    const amt = parseFloat(requestAmount);
    if (
      !requestEmail.trim() ||
      !requestEmail.includes("@") ||
      isNaN(amt) ||
      amt <= 0
    ) {
      setError(
        "Please provide a valid recipient email and an amount greater than 0",
      );
      setLoading(false);
      return;
    }

    try {
      const cleanPurpose = DOMPurify.sanitize(requestPurpose);
      const res = await fetch("/api/v1/requests/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          target_email: requestEmail,
          amount: amt,
          purpose: cleanPurpose || null,
        }),
      });
      if (res.ok) {
        setSuccess(true);
        setRequestEmail("");
        setRequestAmount("");
        setRequestPurpose("");
        setTimeout(() => setSuccess(false), 5000);
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to create request");
      }
    } catch (err) {
      setError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleActionRequest = async (
    action: "pay" | "counter" | "decline",
    requestId: number,
    amount?: number,
  ) => {
    setLoading(true);
    setError("");
    setSuccess(false);
    let endpoint = `/api/v1/requests/${requestId}/${action}`;
    let method = "POST";
    let body: any = {};

    if (action === "pay") {
      // Re-route 'pay' to the standard p2p-transfer endpoint, linking the request
      endpoint = "/api/p2p-transfer";
      // Need the original target email from the request object:
      const reqObj = paymentRequests.find((r) => r.id === requestId);
      if (!reqObj) return;
      body = {
        recipient_email: reqObj.requester_email,
        amount: reqObj.amount,
        commentary: `Payment for Request #${requestId}`,
        payment_request_id: requestId,
      };
    } else if (action === "counter") {
      body = { amount };
    }

    try {
      const res = await fetch(endpoint, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: action === "decline" ? null : JSON.stringify(body),
      });
      if (res.ok) {
        setSuccess(true);
        fetchRequests(); // Refresh table
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const data = await res.json();
        setError(data.detail || `Failed to ${action} request`);
      }
    } catch (err) {
      setError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Derived Summary
  const renderSummary = () => {
    if (!schedAmount || !startDate)
      return "Fill out the form to see your schedule summary.";
    let text = `Next payment of $${schedAmount} will be sent on ${startDate}. `;
    if (frequency === "One-time") {
      text += "This is a single payment.";
    } else {
      text += `It will repeat ${frequency.toLowerCase()} `;
      if (frequency === "Specific Day of Week") text += `on ${freqInterval} `;
      if (frequency === "Specific Date of Month")
        text += `on the ${freqInterval}th `;

      if (endCondition === "Until Cancelled") text += "until you cancel it.";
      if (endCondition === "End Date") text += `until ${endDate || "[Date]"}.`;
      if (endCondition === "Number of Payments")
        text += `for a total of ${targetPayments || "[N]"} payments.`;
    }
    return text;
  };

  return (
    <div className="space-y-8 pb-12 max-w-2xl">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2"
      >
        <h1 className="text-4xl font-black text-white flex items-center gap-3">
          <Send className="text-purple-400" size={32} />
          Payments
        </h1>
        <p className="text-white/60">
          Transfer funds instantly or schedule them for later
        </p>
      </motion.div>

      {/* Tab Navigation */}
      <div className="flex bg-white/10 backdrop-blur-xl rounded-xl p-1 gap-1 flex-col sm:flex-row">
        <button
          onClick={() => {
            setActiveTab("instant");
            setError("");
            setSuccess(false);
          }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-2 rounded-lg font-semibold transition-all ${activeTab === "instant"
            ? "bg-purple-500 text-white shadow-lg"
            : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
        >
          <Send size={18} /> One time transfer
        </button>
        <button
          onClick={() => {
            setActiveTab("scheduled");
            setError("");
            setSuccess(false);
          }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-2 rounded-lg font-semibold transition-all ${activeTab === "scheduled"
            ? "bg-indigo-500 text-white shadow-lg"
            : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
        >
          <Calendar size={18} /> Scheduled
        </button>
        <button
          onClick={() => {
            setActiveTab("request");
            setError("");
            setSuccess(false);
          }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-2 rounded-lg font-semibold transition-all ${activeTab === "request"
            ? "bg-emerald-500 text-white shadow-lg"
            : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
        >
          <HandCoins size={18} /> Request Transfer
        </button>
      </div>

      {/* Success/Error Toast Notifications */}
      <div className="fixed top-6 right-6 z-[200] flex flex-col gap-3 min-w-[320px]">
        <AnimatePresence>
          {success && (
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 50, transition: { duration: 0.2 } }}
              className="bg-[#1a2f26] border border-emerald-500/50 rounded-xl p-4 flex items-start gap-4 shadow-2xl shadow-emerald-500/10 text-emerald-100 font-medium"
            >
              <CheckCircle
                className="text-emerald-400 shrink-0 mt-0.5"
                size={20}
              />
              <div className="flex-1">
                <h4 className="text-emerald-400 font-bold mb-1">Success</h4>
                <p className="text-sm text-emerald-100/80 leading-snug">
                  {successMessage ||
                    (txId
                      ? `Transaction ID: ${txId}`
                      : "Your request has been processed.")}
                </p>
              </div>
            </motion.div>
          )}
          {error && (
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 50, transition: { duration: 0.2 } }}
              className="bg-[#3b1a1a] border border-red-500/50 rounded-xl p-4 flex items-start gap-4 shadow-2xl shadow-red-500/10"
            >
              <AlertCircle className="text-red-400 shrink-0 mt-0.5" size={20} />
              <p className="text-red-200 font-semibold text-sm pt-0.5">
                {error}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Counter Offer Modal */}
      <AnimatePresence>
        {counterModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCounterModalOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              className="relative bg-[#2a1f42] border border-white/10 w-full max-w-sm rounded-[2rem] p-8 shadow-2xl overflow-hidden"
            >
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h3 className="text-2xl font-bold text-white">
                    Counter Offer
                  </h3>
                  <p className="text-white/60">
                    Current offer:{" "}
                    <span className="text-emerald-400 font-bold">
                      ${counterCurrentAmount.toFixed(2)}
                    </span>
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="block text-white font-semibold">
                    New Amount (USD)
                  </label>
                  <div className="relative">
                    <span className="absolute left-4 top-3 text-white font-semibold text-lg">
                      $
                    </span>
                    <input
                      type="number"
                      value={counterNewAmount}
                      onChange={(e) => setCounterNewAmount(e.target.value)}
                      placeholder="0.00"
                      step="0.01"
                      className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-indigo-400"
                      autoFocus
                    />
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setCounterModalOpen(false)}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white/80 hover:text-white hover:bg-white/10 transition-colors border border-white/20"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (
                        counterNewAmount &&
                        parseFloat(counterNewAmount) > 0 &&
                        counterReqId
                      ) {
                        handleActionRequest(
                          "counter",
                          counterReqId,
                          parseFloat(counterNewAmount),
                        );
                        setCounterModalOpen(false);
                      }
                    }}
                    disabled={
                      !counterNewAmount || parseFloat(counterNewAmount) <= 0
                    }
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 shadow-lg disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Cancel Scheduled Payment Confirmation Modal */}
      <AnimatePresence>
        {cancelModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCancelModalOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              className="relative bg-[#2a1f42] border border-white/10 w-full max-w-sm rounded-[2rem] p-8 shadow-2xl overflow-hidden"
            >
              <div className="w-16 h-16 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mb-6 mx-auto">
                <AlertCircle size={32} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2 text-center">
                Cancel Scheduled Payment?
              </h3>
              <p className="text-white/60 mb-8 font-medium text-center leading-relaxed text-sm">
                Are you sure you want to cancel the upcoming scheduled payment
                to{" "}
                <span className="text-white font-bold">
                  "{cancelVendorName}"
                </span>
                ? This action cannot be undone.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => setCancelModalOpen(false)}
                  className="flex-1 py-3 px-4 rounded-xl text-white/70 hover:bg-white/10 font-bold transition-colors"
                >
                  Keep Active
                </button>
                <button
                  onClick={confirmCancelScheduled}
                  disabled={loading}
                  className="flex-1 bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 disabled:opacity-50 text-white font-bold py-3 px-4 rounded-xl shadow-lg transition-all"
                >
                  Yes, Cancel
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Custom Confirmation Modal */}
      <AnimatePresence>
        {showConfirmation && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setShowConfirmation(false);
                setLoading(false);
              }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              className="relative bg-[#2a1f42] border border-white/10 w-full max-w-md rounded-[2rem] p-8 shadow-2xl overflow-hidden"
            >
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h3 className="text-2xl font-bold text-white">
                    Confirm Transfer
                  </h3>
                  <p className="text-white/60">
                    Please review your scheduled transfer details below.
                  </p>
                </div>

                <div className="bg-white/5 rounded-xl border border-white/10 p-5 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Recipient</span>
                    <span className="text-white font-medium text-right break-all ml-4">
                      {schedRecipient}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Amount</span>
                    <span className="text-white font-bold text-lg text-emerald-400">
                      ${parseFloat(schedAmount || "0").toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Frequency</span>
                    <span className="text-white font-medium">{frequency}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Starts</span>
                    <span className="text-white font-medium">{startDate}</span>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => {
                      setShowConfirmation(false);
                      setLoading(false);
                    }}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white/80 hover:text-white hover:bg-white/10 transition-colors border border-white/20"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmAndScheduleTransfer}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 shadow-lg"
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Instant Transfer Confirmation Modal */}
      <AnimatePresence>
        {showInstantConfirmation && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setShowInstantConfirmation(false);
              }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              className="relative bg-[#2a1f42] border border-white/10 w-full max-w-md rounded-[2rem] p-8 shadow-2xl overflow-hidden"
            >
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h3 className="text-2xl font-bold text-white">
                    Confirm Instant Transfer
                  </h3>
                  <p className="text-white/60">
                    Please review your transfer details below.
                  </p>
                </div>

                <div className="bg-white/5 rounded-xl border border-white/10 p-5 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Recipient</span>
                    <span className="text-white font-medium text-right break-all ml-4">
                      {recipient}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/60 text-sm">Amount</span>
                    <span className="text-white font-bold text-lg text-emerald-400">
                      ${parseFloat(amount || "0").toFixed(2)}
                    </span>
                  </div>
                  {commentary && (
                    <div className="flex justify-between items-start">
                      <span className="text-white/60 text-sm">Comment</span>
                      <span className="text-white font-medium text-right ml-4 italic text-sm">
                        "{commentary}"
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => {
                      setShowInstantConfirmation(false);
                    }}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white/80 hover:text-white hover:bg-white/10 transition-colors border border-white/20"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmAndSendInstant}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 shadow-lg"
                  >
                    Send Now
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Repeat Transaction Modal */}
      <AnimatePresence>
        {repeatModalOpen && selectedRepeatTx && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setRepeatModalOpen(false);
                setRepeatLoading(false);
              }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              className="relative bg-[#2a1f42] border border-white/10 w-full max-w-md rounded-[2rem] p-8 shadow-2xl overflow-visible"
            >
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h3 className="text-2xl font-bold text-white">Repeat Transfer</h3>
                  <p className="text-white/60">
                    To: <span className="text-white font-medium">{selectedRepeatTx.amount < 0 ? selectedRepeatTx.recipient_email : selectedRepeatTx.sender_email}</span>
                  </p>
                </div>

                <div className="bg-white/5 rounded-xl border border-white/10 p-5 space-y-4">
                  <div className="space-y-3 relative">
                    <label className="block text-white/60 text-sm">Source Account</label>
                    <div className="relative">
                      <div
                        onClick={() => accountsLoading ? null : setIsRepeatSourceDropdownOpen(!isRepeatSourceDropdownOpen)}
                        className={`w-full bg-white/5 border ${isRepeatSourceDropdownOpen ? 'border-purple-400' : 'border-white/10'} rounded-xl px-4 py-3 text-white cursor-pointer transition-colors flex items-center justify-between shadow-inner`}
                      >
                        <span className="truncate">
                          {repeatSourceAccountId === "" ? (
                            `Main Account - ${accounts.find(a => a.is_main)?.masked_account_number || ''} - $${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}`
                          ) : (
                            `${accounts.find(a => a.id === repeatSourceAccountId)?.name} - ${accounts.find(a => a.id === repeatSourceAccountId)?.masked_account_number || ''} - $${accounts.find(a => a.id === repeatSourceAccountId)?.balance.toFixed(2) || '0.00'}`
                          )}
                        </span>
                        <ChevronDown className={`text-white/40 transition-transform ${isRepeatSourceDropdownOpen ? 'rotate-180' : ''}`} size={20} />
                      </div>

                      <AnimatePresence>
                        {isRepeatSourceDropdownOpen && (
                          <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="absolute z-[110] w-full mt-2 bg-[#1a1132] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-48 overflow-y-auto"
                          >
                            <div className="p-2 space-y-1">
                              <div
                                onClick={() => { setRepeatSourceAccountId(""); setIsRepeatSourceDropdownOpen(false); }}
                                className={`px-4 py-2 hover:bg-white/10 rounded-lg cursor-pointer ${repeatSourceAccountId === "" ? "bg-purple-500/20 text-purple-300 font-bold" : "text-white"}`}
                              >
                                Main Account - {accounts.find(a => a.is_main)?.masked_account_number || ''} - ${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}
                              </div>
                              {accounts.filter(acc => !acc.is_main).map(acc => (
                                <div
                                  key={acc.id}
                                  onClick={() => { setRepeatSourceAccountId(acc.id); setIsRepeatSourceDropdownOpen(false); }}
                                  className={`px-4 py-2 hover:bg-white/10 rounded-lg cursor-pointer ${repeatSourceAccountId === acc.id ? "bg-purple-500/20 text-purple-300 font-bold" : "text-white"}`}
                                >
                                  {acc.name} - {acc.masked_account_number || ''} - ${acc.balance.toFixed(2)}
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="block text-white/60 text-sm">Amount (USD)</label>
                    <div className="relative">
                      <span className="absolute left-4 top-3 text-white font-semibold">$</span>
                      <input
                        type="number"
                        value={repeatAmount}
                        onChange={(e) => setRepeatAmount(e.target.value)}
                        placeholder="0.00"
                        step="0.01"
                        className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white focus:outline-none focus:border-purple-400"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="block text-white/60 text-sm">Commentary (Optional)</label>
                    <input
                      type="text"
                      value={repeatCommentary}
                      onChange={(e) => setRepeatCommentary(e.target.value)}
                      placeholder="What is this for?"
                      className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-400"
                    />
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => {
                      setRepeatModalOpen(false);
                      setRepeatLoading(false);
                    }}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white/80 hover:text-white hover:bg-white/10 transition-colors border border-white/20"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmRepeat}
                    disabled={repeatLoading || !repeatAmount || parseFloat(repeatAmount) <= 0}
                    className="flex-1 py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 shadow-lg disabled:opacity-50"
                  >
                    {repeatLoading ? "Processing..." : "Confirm Send"}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Form Container */}
      <motion.div
        key={activeTab} // re-animate on tab switch
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {activeTab === "instant" && (
          // SEND TO CONTACT FORM
          <form onSubmit={handleInstantSubmit} className="space-y-6">
            <div className="space-y-3 relative">
              <label className="block text-white font-semibold flex justify-between">
                <span>Source Account</span>
                {sourceAccountId !== "" && (
                  <span
                    className="text-xs text-purple-400 cursor-pointer hover:underline"
                    onClick={() => setSourceAccountId("")}
                  >
                    Reset to Default
                  </span>
                )}
              </label>
              <div className="relative">
                <div
                  onClick={() => accountsLoading ? null : setIsSourceDropdownOpen(!isSourceDropdownOpen)}
                  className={`w-full bg-white/5 border ${isSourceDropdownOpen ? 'border-purple-400' : 'border-white/10'} rounded-xl px-4 py-3 text-white cursor-pointer hover:bg-white/10 transition-colors flex items-center justify-between shadow-inner`}
                >
                  <span className="truncate">
                    {sourceAccountId === "" ? (
                      `Main Account - ${accounts.find(a => a.is_main)?.masked_account_number || ''} - $${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}`
                    ) : (
                      (() => {
                        const acc = accounts.find(a => a.id === sourceAccountId);
                        return `${acc?.name} - ${acc?.masked_account_number || ''} - $${acc?.balance.toFixed(2) || '0.00'}`;
                      })()
                    )}
                  </span>
                  <ChevronDown
                    className={`text-white/40 transition-transform duration-200 ${isSourceDropdownOpen ? 'rotate-180' : ''}`}
                    size={20}
                  />
                </div>

                <AnimatePresence>
                  {isSourceDropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.15 }}
                      className="absolute z-[100] w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
                    >
                      <div className="p-2 space-y-1">
                        <div
                          onClick={() => {
                            setSourceAccountId("");
                            setIsSourceDropdownOpen(false);
                          }}
                          className={`px-4 py-3 rounded-lg cursor-pointer transition-colors ${sourceAccountId === "" ? 'bg-purple-500/20 text-purple-300 font-bold' : 'hover:bg-white/10 text-white'}`}
                        >
                          <span className="block truncate">Main Account - {accounts.find(a => a.is_main)?.masked_account_number || ''}</span>
                          <span className="text-xs opacity-70">${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}</span>
                        </div>
                        {accounts.filter(acc => !acc.is_main).map(acc => (
                          <div
                            key={acc.id}
                            onClick={() => {
                              setSourceAccountId(acc.id);
                              setIsSourceDropdownOpen(false);
                            }}
                            className={`px-4 py-3 rounded-lg cursor-pointer transition-colors ${sourceAccountId === acc.id ? 'bg-purple-500/20 text-purple-300 font-bold' : 'hover:bg-white/10 text-white'}`}
                          >
                            <span className="block truncate">{acc.name} - {acc.masked_account_number || ''}</span>
                            <span className="text-xs opacity-70">${acc.balance.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="space-y-3 relative">
              <label className="block text-white font-semibold">
                Recipient Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  onFocus={() => setIsContactDropdownOpen(true)}
                  onBlur={() =>
                    setTimeout(() => setIsContactDropdownOpen(false), 200)
                  }
                  placeholder="user@example.com"
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400 pr-10"
                  required
                />
                <ChevronDown
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
                  size={20}
                />
              </div>

              {/* Recipient Dropdown */}
              <AnimatePresence>
                {isContactDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.15 }}
                    className="absolute z-50 w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
                  >
                    <div className="p-2">
                      {(() => {
                        const term = recipient.toLowerCase();
                        const matchedContacts = contacts.filter(c =>
                          c.contact_name.toLowerCase().includes(term) ||
                          c.contact_email.toLowerCase().includes(term)
                        );
                        const matchedVendors = vendors.filter(v =>
                          v.name.toLowerCase().includes(term) ||
                          v.email.toLowerCase().includes(term)
                        );

                        if (matchedContacts.length === 0 && matchedVendors.length === 0) {
                          return (
                            <div className="px-4 py-3 text-white/50 text-sm">
                              Use "{recipient}" as custom email
                            </div>
                          );
                        }

                        return (
                          <>
                            {matchedContacts.map(c => (
                              <div
                                key={c.id}
                                onClick={() => {
                                  if (c.contact_type === "merchant" && c.merchant_id) {
                                    const v = vendors.find(vend => vend.id === c.merchant_id);
                                    if (v) setRecipient(v.email);
                                    if (c.subscriber_id) setSubscriberId(c.subscriber_id);
                                  } else {
                                    setRecipient(c.contact_email || "");
                                  }
                                  setIsContactDropdownOpen(false);
                                }}
                                className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors flex justify-between items-center group"
                              >
                                <div>
                                  <p className="text-white font-medium group-hover:text-purple-300 transition-colors">
                                    {c.contact_name}
                                  </p>
                                  <p className="text-white/50 text-sm">
                                    {c.contact_type === "merchant" ? `Merchant: ${c.merchant_id}` : c.contact_email}
                                  </p>
                                </div>
                                <span className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold tracking-wider ${c.contact_type === "karin" ? "bg-purple-500/20 text-purple-400 border-purple-500/30" :
                                    c.contact_type === "merchant" ? "bg-indigo-500/20 text-indigo-400 border-indigo-500/30" :
                                      "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                  }`}>
                                  {c.contact_type === "karin" ? "Karin" : c.contact_type}
                                </span>
                              </div>
                            ))}
                            {matchedVendors.map(v => (
                              <div
                                key={v.id}
                                onClick={() => {
                                  setRecipient(v.email);
                                  setIsContactDropdownOpen(false);
                                }}
                                className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors flex justify-between items-center group border-t border-white/5"
                              >
                                <div>
                                  <p className="text-white font-medium group-hover:text-purple-300 transition-colors">
                                    {v.name}
                                  </p>
                                  <p className="text-white/50 text-sm">
                                    {v.email}
                                  </p>
                                </div>
                                <span className="text-[10px] bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded border border-slate-500/30 uppercase font-bold tracking-wider">Public Merchant</span>
                              </div>
                            ))}
                          </>
                        );
                      })()}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <div className="space-y-3">
              <label className="block text-white font-semibold">
                Amount (USD)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-3 text-white font-semibold text-lg">
                  $
                </span>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400"
                  required
                />
              </div>
            </div>
            <div className="space-y-3">
              <label className="block text-white font-semibold">
                Commentary{" "}
                <span className="text-white/40 font-normal text-sm">
                  (Optional)
                </span>
              </label>
              <textarea
                value={commentary}
                onChange={(e) => setCommentary(e.target.value)}
                placeholder="What is this for?"
                rows={2}
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400 resize-none"
              />
            </div>

            {isVendor && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="space-y-3"
              >
                <label className="block text-white font-semibold">
                  Subscriber / Contract ID
                </label>
                <input
                  type="text"
                  value={subscriberId}
                  onChange={(e) => setSubscriberId(e.target.value)}
                  placeholder="Enter your subscriber ID"
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400"
                  required
                />
              </motion.div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
            >
              {loading ? (
                "Processing..."
              ) : (
                <>
                  <Send size={20} /> Send Instantly <ArrowRight size={20} />
                </>
              )}
            </button>
          </form>
        )}
        {/* Instant History Table */}
        {activeTab === "instant" && (
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8 mt-8">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Clock className="text-purple-400" size={24} />
              Recent Transfers
            </h3>

            {instantHistoryLoading ? (
              <div className="py-8 text-center text-white/50 animate-pulse font-medium">
                Loading history...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 text-white/50 text-sm">
                      <th className="pb-3 font-medium">Date</th>
                      <th className="pb-3 font-medium">From / To</th>
                      <th className="pb-3 font-medium text-right">Amount</th>
                      <th className="pb-3 font-medium px-4">Status</th>
                      <th className="pb-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {instantHistory.map((tx) => {
                      const isOutgoing = tx.amount < 0;
                      return (
                        <tr
                          key={tx.id}
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        >
                          <td className="py-4 text-white/70 text-sm">
                            {new Date(tx.timestamp + (tx.timestamp.endsWith('Z') ? '' : 'Z')).toLocaleString(settings.useEUDates ? 'en-GB' : 'en-US', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              hour12: !settings.use24Hour
                            })}
                          </td>
                          <td className="py-4">
                            <div className="text-white font-medium">
                              {isOutgoing ? `To: ${tx.recipient_email}` : `From: ${tx.sender_email}`}
                            </div>
                            <div className="text-white/40 text-xs flex items-center gap-1">
                              {isOutgoing ? 'Sent from' : 'Received into'}
                              <span className="bg-white/10 px-1.5 py-0.5 rounded font-mono">
                                *{tx.internal_account_last_4 || '????'}
                              </span>
                            </div>
                          </td>
                          <td
                            className={`py-4 text-right font-bold ${isOutgoing ? "text-red-400" : "text-emerald-400"}`}
                          >
                            {isOutgoing ? "-" : "+"}$
                            {Math.abs(tx.amount).toFixed(2)}
                          </td>
                          <td className="py-4 px-4">
                            <span className={`px-2 py-1 rounded-full text-[10px] uppercase font-bold tracking-wider ${tx.status === 'cleared' || tx.status === 'Completed' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                              tx.status === 'pending' || tx.status === 'Pending' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                                tx.status === 'processing' || tx.status === 'Processing' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                                  tx.status === 'failed' || tx.status === 'Failed' || tx.status === 'Declined' || tx.status === 'Rejected' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                    'bg-white/10 text-white/50'
                              }`}>
                              {tx.status === 'cleared' ? 'Completed' :
                                tx.status === 'pending' ? 'Pending' :
                                  tx.status === 'processing' ? 'Processing' :
                                    tx.status === 'failed' ? 'Failed / Declined / Rejected' :
                                      (tx.status || 'Processing')}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => {
                                  setSelectedRepeatTx(tx);
                                  setRepeatAmount(Math.abs(tx.amount).toString());
                                  setRepeatCommentary("");
                                  setRepeatSourceAccountId("");
                                  setRepeatModalOpen(true);
                                }}
                                className="text-xs bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 px-3 py-1.5 rounded-lg border border-purple-500/30 transition-all font-bold"
                              >
                                Repeat
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedTxDetails(tx);
                                  setDetailsModalOpen(true);
                                }}
                                className="text-xs bg-white/5 hover:bg-white/10 text-white/50 hover:text-white px-3 py-1.5 rounded-lg border border-white/10 transition-all font-bold"
                              >
                                Details
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {instantHistory.length === 0 && (
                  <p className="text-white/50 text-center py-6">
                    No recent transfers found.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "scheduled" && (
          // SCHEDULED TRANSFER FORM
          <form onSubmit={handleScheduledSubmit} className="space-y-6">
            <div className="space-y-3 relative">
              <label className="block text-white font-semibold flex justify-between">
                <span>Funding Account</span>
                {sourceAccountId !== "" && (
                  <span
                    className="text-xs text-indigo-400 cursor-pointer hover:underline"
                    onClick={() => setSourceAccountId("")}
                  >
                    Reset to Default
                  </span>
                )}
              </label>
              <div className="relative">
                <div
                  onClick={() => accountsLoading ? null : setIsSourceDropdownOpen(!isSourceDropdownOpen)}
                  className={`w-full bg-[#3b2d59] border ${isSourceDropdownOpen ? 'border-indigo-400' : 'border-white/20'} rounded-xl px-4 py-3 text-white cursor-pointer hover:bg-[#4a3a70] transition-colors flex items-center justify-between shadow-inner`}
                >
                  <span className="truncate">
                    {sourceAccountId === "" ? (
                      `Main Account - ${accounts.find(a => a.is_main)?.masked_account_number || ''} - $${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}`
                    ) : (
                      (() => {
                        const acc = accounts.find(a => a.id === sourceAccountId);
                        return `${acc?.name} - ${acc?.masked_account_number || ''} - $${acc?.balance.toFixed(2) || '0.00'}`;
                      })()
                    )}
                  </span>
                  <ChevronDown
                    className={`text-white/40 transition-transform duration-200 ${isSourceDropdownOpen ? 'rotate-180' : ''}`}
                    size={20}
                  />
                </div>

                <AnimatePresence>
                  {isSourceDropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.15 }}
                      className="absolute z-[100] w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
                    >
                      <div className="p-2 space-y-1">
                        <div
                          onClick={() => {
                            setSourceAccountId("");
                            setIsSourceDropdownOpen(false);
                          }}
                          className={`px-4 py-3 rounded-lg cursor-pointer transition-colors ${sourceAccountId === "" ? 'bg-indigo-500/20 text-indigo-300 font-bold' : 'hover:bg-white/10 text-white'}`}
                        >
                          <span className="block truncate">Main Account - {accounts.find(a => a.is_main)?.masked_account_number || ''}</span>
                          <span className="text-xs opacity-70">${accounts.find(a => a.is_main)?.balance.toFixed(2) || '0.00'}</span>
                        </div>
                        {accounts.filter(acc => !acc.is_main).map(acc => (
                          <div
                            key={acc.id}
                            onClick={() => {
                              setSourceAccountId(acc.id);
                              setIsSourceDropdownOpen(false);
                            }}
                            className={`px-4 py-3 rounded-lg cursor-pointer transition-colors ${sourceAccountId === acc.id ? 'bg-indigo-500/20 text-indigo-300 font-bold' : 'hover:bg-white/10 text-white'}`}
                          >
                            <span className="block truncate">{acc.name} - {acc.masked_account_number || ''}</span>
                            <span className="text-xs opacity-70">${acc.balance.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Recipient Input (Combobox style support) */}
            <div className="space-y-3 relative">
              <label className="block text-white font-semibold">
                Recipient or Vendor
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={schedRecipient}
                  onChange={(e) => setSchedRecipient(e.target.value)}
                  onFocus={() => setIsVendorDropdownOpen(true)}
                  // Slight delay to allow onClick on dropdown items to fire
                  onBlur={() =>
                    setTimeout(() => setIsVendorDropdownOpen(false), 200)
                  }
                  placeholder="Email or select a vendor"
                  className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-indigo-400 pr-10"
                  required
                />
                <ChevronDown
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
                  size={20}
                />
              </div>

              {/* Custom Styled Dropdown */}
              <AnimatePresence>
                {isVendorDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.15 }}
                    className="absolute z-50 w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
                  >
                    <div className="p-2">
                      {(() => {
                        const term = schedRecipient.toLowerCase();
                        const matchedContacts = contacts.filter(c =>
                          c.contact_name.toLowerCase().includes(term) ||
                          c.contact_email.toLowerCase().includes(term)
                        );
                        const matchedVendors = vendors.filter(v =>
                          v.name.toLowerCase().includes(term) ||
                          v.email.toLowerCase().includes(term)
                        );

                        if (matchedContacts.length === 0 && matchedVendors.length === 0) {
                          return (
                            <div className="px-4 py-3 text-white/50 text-sm">
                              Use "{schedRecipient}" as custom email
                            </div>
                          );
                        }

                        return (
                          <>
                            {matchedContacts.map(c => (
                              <div
                                key={c.id}
                                onClick={() => {
                                  setSchedRecipient(c.contact_email);
                                  setIsVendorDropdownOpen(false);
                                }}
                                className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors flex justify-between items-center group"
                              >
                                <div>
                                  <p className="text-white font-medium group-hover:text-indigo-300 transition-colors">
                                    {c.contact_name}
                                  </p>
                                  <p className="text-white/50 text-sm">
                                    {c.contact_email}
                                  </p>
                                </div>
                                <span className="text-[10px] bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded border border-purple-500/30 uppercase font-bold tracking-wider">Contact</span>
                              </div>
                            ))}
                            {matchedVendors.map(v => (
                              <div
                                key={v.id}
                                onClick={() => {
                                  setSchedRecipient(v.email);
                                  setIsVendorDropdownOpen(false);
                                }}
                                className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors flex justify-between items-center group border-t border-white/5"
                              >
                                <div>
                                  <p className="text-white font-medium group-hover:text-indigo-300 transition-colors">
                                    {v.name}
                                  </p>
                                  <p className="text-white/50 text-sm">
                                    {v.email}
                                  </p>
                                </div>
                                <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded border border-indigo-500/30 uppercase font-bold tracking-wider">Merchant</span>
                              </div>
                            ))}
                          </>
                        );
                      })()}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {isSchedVendor && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="space-y-3"
              >
                <label className="block text-white font-semibold">
                  Subscriber / Contract ID
                </label>
                <input
                  type="text"
                  value={schedSubscriberId}
                  onChange={(e) => setSchedSubscriberId(e.target.value)}
                  placeholder="Enter your subscriber ID"
                  className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-indigo-400"
                  required
                />
              </motion.div>
            )}

            <div className="space-y-3">
              <label className="block text-white font-semibold flex justify-between">
                Amount (USD){" "}
                <span className="text-indigo-300 font-normal text-sm">
                  Limit: $5000
                </span>
              </label>
              <div className="relative">
                <span className="absolute left-4 top-3 text-white font-semibold text-lg">
                  $
                </span>
                <input
                  type="number"
                  value={schedAmount}
                  onChange={(e) => setSchedAmount(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  max="5000"
                  className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-indigo-400"
                  required
                />
              </div>
            </div>

            {/* Scheduling Core Options */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-3">
                <label className="block text-white font-semibold">
                  Frequency
                </label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                  className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-400"
                >
                  <option>One-time</option>
                  <option>Daily</option>
                  <option>Weekly</option>
                  <option>Bi-weekly</option>
                  <option>Monthly</option>
                  <option>Annually</option>
                  <option>Specific Day of Week</option>
                  <option>Specific Date of Month</option>
                </select>
              </div>
              <DatePicker
                label="Start Date"
                value={startDate}
                onChange={(date) => setStartDate(date)}
                required
              />
            </div>

            {/* Conditional Intervals */}
            {frequency === "Specific Day of Week" && (
              <div className="space-y-3">
                <label className="block text-white font-semibold">
                  Which Day?
                </label>
                <select
                  value={freqInterval}
                  onChange={(e) => setFreqInterval(e.target.value)}
                  className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-4 py-3 text-white"
                >
                  <option>Monday</option>
                  <option>Tuesday</option>
                  <option>Wednesday</option>
                  <option>Thursday</option>
                  <option>Friday</option>
                  <option>Saturday</option>
                  <option>Sunday</option>
                </select>
              </div>
            )}
            {frequency === "Specific Date of Month" && (
              <div className="space-y-3">
                <label className="block text-white font-semibold">
                  Day of the Month (1-31)
                </label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={freqInterval}
                  onChange={(e) => setFreqInterval(e.target.value)}
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white"
                />
              </div>
            )}

            {/* End Conditions (Only if not one-time) */}
            {frequency !== "One-time" && (
              <div className="space-y-4 p-4 border border-white/10 rounded-xl bg-white/5">
                <label className="block text-white font-semibold">
                  End Condition
                </label>
                <div className="flex gap-4">
                  {["Until Cancelled", "End Date", "Number of Payments"].map(
                    (cond) => (
                      <label
                        key={cond}
                        className="flex items-center gap-2 text-white/80 cursor-pointer"
                      >
                        <input
                          type="radio"
                          value={cond}
                          checked={endCondition === cond}
                          onChange={(e) => setEndCondition(e.target.value)}
                          className="accent-indigo-500"
                        />
                        {cond}
                      </label>
                    ),
                  )}
                </div>
                {endCondition === "End Date" && (
                  <DatePicker
                    value={endDate}
                    onChange={(date) => setEndDate(date)}
                    required
                  />
                )}
                {endCondition === "Number of Payments" && (
                  <input
                    type="number"
                    value={targetPayments}
                    onChange={(e) => setTargetPayments(e.target.value)}
                    placeholder="E.g. 5"
                    className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white"
                    required
                  />
                )}
              </div>
            )}

            {/* Reserve Amount Box */}
            <div className="p-4 border border-indigo-500/30 rounded-xl bg-indigo-500/10 flex items-start gap-4">
              <input
                type="checkbox"
                id="reserveCheck"
                checked={reserveAmount}
                onChange={(e) => setReserveAmount(e.target.checked)}
                className="mt-1 w-5 h-5 accent-indigo-500 rounded"
              />
              <div>
                <label
                  htmlFor="reserveCheck"
                  className="text-white font-semibold block cursor-pointer"
                >
                  Reserve Balance Now
                </label>
                <p className="text-indigo-200/70 text-sm">
                  Deduct the funds from your available balance immediately and
                  keep them aside for this transfer.
                </p>
              </div>
            </div>

            {/* Dynamic Summary */}
            <div className="p-4 bg-black/20 rounded-xl shadow-inner border border-white/5 flex gap-3 text-indigo-100">
              <Clock className="shrink-0 mt-1" size={20} />
              <p className="font-medium text-sm leading-relaxed">
                {renderSummary()}
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
            >
              {loading ? (
                "Processing..."
              ) : (
                <>
                  <Calendar size={20} /> Schedule Transfer{" "}
                  <ArrowRight size={20} />
                </>
              )}
            </button>
          </form>
        )}
        {activeTab === "scheduled" && (
          <div className="mt-12 space-y-4">
            <h3 className="text-xl font-bold text-white mb-4">
              Scheduled Payments History
            </h3>
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden">
              {scheduledHistoryLoading ? (
                <div className="p-8 text-center text-white/50">
                  Loading scheduled payments...
                </div>
              ) : scheduledHistory.length === 0 ? (
                <div className="p-8 text-center text-white/50">
                  No scheduled payments found.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-white/5 border-b border-white/10 text-white/70 text-sm">
                        <th className="p-4 font-medium">To</th>
                        <th className="p-4 font-medium">Amount</th>
                        <th className="p-4 font-medium">Frequency</th>
                        <th className="p-4 font-medium">Next Run</th>
                        <th className="p-4 font-medium">Status</th>
                        <th className="p-4 font-medium text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scheduledHistory.map((pmt) => (
                        <tr
                          key={pmt.id}
                          className="border-b border-white/5 hover:bg-white-[0.02] text-sm group"
                        >
                          <td className="p-4">
                            <div className="text-white font-medium">
                              {pmt.recipient_email}
                            </div>
                            <div className="text-white/40 text-xs flex items-center gap-1">
                              Sent from
                              <span className="bg-white/10 px-1.5 py-0.5 rounded font-mono">
                                *{(() => {
                                  const acc = accounts.find(a => a.id === pmt.funding_account_id);
                                  return acc?.masked_account_number || accounts.find(a => a.is_main)?.masked_account_number || '????';
                                })()}
                              </span>
                            </div>
                          </td>
                          <td className="p-4 text-white font-semibold">
                            ${parseFloat(pmt.amount).toFixed(2)}
                          </td>
                          <td className="p-4 text-white/70">
                            {pmt.frequency}
                            {pmt.frequency_interval &&
                              ` (${pmt.frequency_interval})`}
                          </td>
                          <td className="p-4 text-white/70">
                            {pmt.next_run_at
                              ? new Date(
                                pmt.next_run_at + "Z",
                              ).toLocaleDateString(settings.useEUDates ? 'en-GB' : 'en-US')
                              : "N/A"}
                          </td>
                          <td className="p-4">
                            <span
                              className={`px-2 py-1 rounded text-xs font-semibold ${pmt.status === "Active"
                                ? "bg-indigo-500/20 text-indigo-300"
                                : pmt.status === "Cancelled"
                                  ? "bg-red-500/20 text-red-300"
                                  : "bg-white/10 text-white/70"
                                }`}
                            >
                              {pmt.status}
                            </span>
                          </td>
                          <td className="p-4 text-right">
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => {
                                  setSelectedTxDetails({
                                    ...pmt,
                                    recipient_email: pmt.recipient_email,
                                    amount: -pmt.amount,
                                    status: pmt.status,
                                    is_scheduled: true
                                  });
                                  setDetailsModalOpen(true);
                                }}
                                className="text-xs bg-white/5 hover:bg-white/10 text-white/50 hover:text-white px-3 py-1.5 rounded-lg border border-white/10 transition-all font-bold"
                              >
                                Details
                              </button>

                              {pmt.status === "Active" && (
                                <button
                                  onClick={() => handleCancelScheduled(pmt)}
                                  className="px-3 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors border border-red-500/30 text-xs font-bold"
                                >
                                  Cancel
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
        {activeTab === "request" && (
          // REQUEST TRANSFER FORM
          <form onSubmit={handleRequestSubmit} className="space-y-6">
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 mb-4">
              <h4 className="text-emerald-300 font-semibold flex items-center gap-2 mb-2">
                <HandCoins size={18} /> How Requesting Works
              </h4>
              <p className="text-emerald-100/70 text-sm leading-relaxed">
                Enter the email of the person you'd like to request money from.
                They will receive your request and can choose to Pay, Counter
                Offer, or Decline. Once they pay, the money will instantly
                arrive in your account!
              </p>
            </div>
            <div className="space-y-3 relative">
              <label className="block text-white font-semibold">
                Recipient Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={requestEmail}
                  onChange={(e) => setRequestEmail(e.target.value)}
                  onFocus={() => setIsReqContactDropdownOpen(true)}
                  onBlur={() =>
                    setTimeout(() => setIsReqContactDropdownOpen(false), 200)
                  }
                  placeholder="payer@example.com"
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-emerald-400 pr-10"
                  required
                />
                <ChevronDown
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
                  size={20}
                />
              </div>

              {/* Contact Dropdown for Request */}
              <AnimatePresence>
                {isReqContactDropdownOpen && contacts.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.15 }}
                    className="absolute z-50 w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
                  >
                    <div className="p-2">
                      {contacts.filter(
                        (c) =>
                          c.contact_name
                            .toLowerCase()
                            .includes(requestEmail.toLowerCase()) ||
                          c.contact_email
                            .toLowerCase()
                            .includes(requestEmail.toLowerCase()),
                      ).length > 0 ? (
                        contacts
                          .filter(
                            (c) =>
                              c.contact_name
                                .toLowerCase()
                                .includes(requestEmail.toLowerCase()) ||
                              c.contact_email
                                .toLowerCase()
                                .includes(requestEmail.toLowerCase()),
                          )
                          .map((c) => (
                            <div
                              key={c.id}
                              onClick={() => {
                                setRequestEmail(c.contact_email);
                                setIsReqContactDropdownOpen(false);
                              }}
                              className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors flex justify-between items-center"
                            >
                              <div>
                                <p className="text-white font-medium">
                                  {c.contact_name}
                                </p>
                                <p className="text-white/50 text-sm">
                                  {c.contact_email}
                                </p>
                              </div>
                            </div>
                          ))
                      ) : (
                        <div className="px-4 py-3 text-white/50 text-sm">
                          Use "{requestEmail}" as custom email
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <div className="space-y-3">
              <label className="block text-white font-semibold">
                Amount to Request (USD)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-3 text-white font-semibold text-lg">
                  $
                </span>
                <input
                  type="number"
                  value={requestAmount}
                  onChange={(e) => setRequestAmount(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="w-full bg-white/10 border border-white/20 rounded-xl pl-8 pr-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-emerald-400"
                  required
                />
              </div>
            </div>
            <div className="space-y-3">
              <label className="block text-white font-semibold">
                What is this for?{" "}
                <span className="text-white/40 font-normal text-sm">
                  (Optional)
                </span>
              </label>
              <textarea
                value={requestPurpose}
                onChange={(e) => setRequestPurpose(e.target.value)}
                placeholder="E.g. Dinner last night"
                rows={2}
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-emerald-400 resize-none"
              />
            </div>
            <button
              type="submit"
              disabled={
                loading ||
                !requestEmail.includes("@") ||
                !requestAmount ||
                parseFloat(requestAmount) <= 0
              }
              className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
            >
              {loading ? (
                "Processing..."
              ) : (
                <>
                  <HandCoins size={20} /> Send Request <ArrowRight size={20} />
                </>
              )}
            </button>
          </form>
        )}
      </motion.div>

      {/* Request History & Negotiation Table */}
      {activeTab === "request" && paymentRequests.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8"
        >
          <h3 className="text-xl font-bold text-white mb-6">Request History</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-white/50 text-sm">
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">From / To</th>
                  <th className="pb-3 font-medium">Amount</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {paymentRequests.map((req) => {
                  const isTarget =
                    token &&
                    JSON.parse(atob(token.split(".")[1])).sub ===
                    req.target_email;
                  const isRequester = !isTarget;
                  const isMyTurn =
                    (isTarget && req.status === "pending_target") ||
                    (isRequester && req.status === "pending_requester");

                  return (
                    <tr
                      key={req.id}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-4 text-white/70 text-sm">
                        {new Date(req.created_at + "Z").toLocaleDateString(settings.useEUDates ? 'en-GB' : 'en-US')}
                      </td>
                      <td className="py-4">
                        <div className="text-white font-medium">
                          {isRequester ? req.target_email : req.requester_name}
                        </div>
                        <div className="text-white/50 text-xs">
                          {isRequester ? "Sent Request" : "Received Request"}
                        </div>
                      </td>
                      <td className="py-4 font-bold text-emerald-400">
                        ${req.amount.toFixed(2)}
                      </td>
                      <td className="py-4">
                        <span
                          className={`px-2 py-1 rounded text-xs font-semibold ${req.status === "paid"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : req.status === "declined"
                              ? "bg-red-500/20 text-red-300"
                              : "bg-amber-500/20 text-amber-300"
                            }`}
                        >
                          {req.status.replace("_", " ").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-4 text-right space-x-2">
                        {isMyTurn &&
                          req.status !== "paid" &&
                          req.status !== "declined" && (
                            <>
                              {isTarget && (
                                <button
                                  onClick={() =>
                                    handleActionRequest("pay", req.id)
                                  }
                                  className="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-1 rounded text-sm font-semibold transition"
                                >
                                  Pay
                                </button>
                              )}
                              {!isTarget && (
                                <button
                                  onClick={() =>
                                    handleActionRequest(
                                      "counter",
                                      req.id,
                                      req.amount,
                                    )
                                  }
                                  className="bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1 rounded text-sm font-semibold transition"
                                >
                                  Accept
                                </button>
                              )}
                              <button
                                onClick={() => {
                                  setCounterReqId(req.id);
                                  setCounterCurrentAmount(req.amount);
                                  setCounterNewAmount("");
                                  setCounterModalOpen(true);
                                }}
                                className="bg-white/10 hover:bg-white/20 text-white px-3 py-1 rounded text-sm font-semibold transition"
                              >
                                Counter
                              </button>

                              <button
                                onClick={() =>
                                  handleActionRequest("decline", req.id)
                                }
                                className="bg-red-500/20 hover:bg-red-500/40 text-red-300 px-3 py-1 rounded text-sm font-semibold transition"
                              >
                                Decline
                              </button>
                            </>
                          )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {paymentRequests.length === 0 && (
              <p className="text-white/50 text-center py-6">
                No request history found.
              </p>
            )}
          </div>
        </motion.div>
      )}
      {/* Transaction Details Modal */}
      <AnimatePresence>
        {detailsModalOpen && selectedTxDetails && (
          <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#1a1228] border border-white/10 rounded-3xl w-full max-w-md overflow-hidden shadow-2xl"
            >
              <div className="bg-gradient-to-r from-purple-600 to-indigo-700 p-6 text-white">
                <div className="flex justify-between items-center">
                  <h3 className="text-xl font-bold">Transaction Details</h3>
                  <button
                    onClick={() => setDetailsModalOpen(false)}
                    className="text-white/60 hover:text-white transition-colors"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                <div className="flex flex-col items-center py-4 bg-white/5 rounded-2xl border border-white/5">
                  <span className={`text-3xl font-bold ${selectedTxDetails.amount < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {selectedTxDetails.amount < 0 ? '-' : '+'}${Math.abs(selectedTxDetails.amount).toFixed(2)}
                  </span>
                  <span className="text-white/50 text-sm mt-1 uppercase tracking-widest font-semibold">
                    {selectedTxDetails.transaction_side || (selectedTxDetails.amount < 0 ? 'Debit' : 'Credit')}
                  </span>
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-white/40 text-sm">Recipient</span>
                    <span className="text-white font-medium prose-sm max-w-[200px] truncate">{selectedTxDetails.recipient_email}</span>
                  </div>

                  {selectedTxDetails.merchant && (
                    <div className="flex justify-between border-b border-white/5 pb-2">
                      <span className="text-white/40 text-sm">Merchant</span>
                      <span className="text-white font-medium">{selectedTxDetails.merchant}</span>
                    </div>
                  )}

                  {selectedTxDetails.subscriber_id && (
                    <div className="flex justify-between border-b border-white/5 pb-2">
                      <span className="text-white/40 text-sm">Subscriber ID</span>
                      <span className="text-indigo-300 font-mono text-sm">{selectedTxDetails.subscriber_id}</span>
                    </div>
                  )}

                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-white/40 text-sm">Status</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${selectedTxDetails.status === 'cleared' || selectedTxDetails.status === 'Active'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : selectedTxDetails.status === 'failed' || selectedTxDetails.status === 'Failed'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                      {selectedTxDetails.status}
                    </span>
                  </div>

                  {selectedTxDetails.failure_reason && (
                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                      <span className="text-red-400 text-xs font-bold uppercase block mb-1">Failure Reason</span>
                      <p className="text-red-100 text-sm leading-relaxed">{selectedTxDetails.failure_reason}</p>
                    </div>
                  )}

                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-white/40 text-sm">Date</span>
                    <span className="text-white/70 text-sm">
                      {new Date(selectedTxDetails.timestamp || selectedTxDetails.next_run_at || new Date()).toLocaleString()}
                    </span>
                  </div>

                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-white/40 text-sm">Trace / TX ID</span>
                    <span className="text-white/40 font-mono text-[10px] max-w-[200px] truncate">{selectedTxDetails.id}</span>
                  </div>
                </div>

                <button
                  onClick={() => setDetailsModalOpen(false)}
                  className="w-full bg-white/10 hover:bg-white/20 text-white font-bold py-3 rounded-xl transition-all border border-white/10"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
