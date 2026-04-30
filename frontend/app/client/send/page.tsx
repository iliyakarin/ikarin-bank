"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Send, 
  Calendar, 
  Handshake, 
  ChevronRight, 
  Info,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { getAccounts, Account } from "@/lib/api/accounts";
import { getContacts, Contact } from "@/lib/api/contacts";
import { 
  getScheduledPayments, 
  getPaymentRequests, 
  cancelScheduledPayment,
  handlePaymentRequestAction,
  ScheduledPayment,
  PaymentRequest 
} from "@/lib/api/transfers";
import { getActivity, ActivityEvent } from "@/lib/api/activity";

// Modular Components
import InstantTransferTab from "@/components/transfers/InstantTransferTab";
import ScheduledTransferTab from "@/components/transfers/ScheduledTransferTab";
import RequestTransferTab from "@/components/transfers/RequestTransferTab";
import ScheduledHistoryTable from "@/components/transfers/ScheduledHistoryTable";
import RequestHistoryTable from "@/components/transfers/RequestHistoryTable";
import RecentTransactionsTable from "@/components/transfers/RecentTransactionsTable";
import DetailModal from "@/components/transfers/DetailModal";

const TABS = [
  { id: "instant", label: "Instant Transfer", icon: Send, color: "from-purple-500 to-indigo-600" },
  { id: "scheduled", label: "Schedule Payment", icon: Calendar, color: "from-indigo-500 to-blue-600" },
  { id: "request", label: "Request Money", icon: Handshake, color: "from-rose-500 to-orange-600" },
];

export default function SendMoneyPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("instant");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [scheduledPayments, setScheduledPayments] = useState<ScheduledPayment[]>([]);
  const [paymentRequests, setPaymentRequests] = useState<PaymentRequest[]>([]);
  const [transactions, setTransactions] = useState<ActivityEvent[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  // Modal states
  const [selectedDetail, setSelectedDetail] = useState<{ data: any, type: 'scheduled' | 'request' } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [accsResult, contsResult, scheduledResult, requestsResult, activityResult, vendorsResult] = await Promise.allSettled([
        getAccounts(),
        getContacts(),
        getScheduledPayments(),
        getPaymentRequests(),
        getActivity({ category: 'p2p', limit: 50 }),
        fetch("/api/v1/vendors", {
          headers: { Authorization: `Bearer ${localStorage.getItem("bank_token")}` }
        }).then(res => res.json())
      ]);

      if (accsResult.status === 'fulfilled') setAccounts(accsResult.value);
      if (contsResult.status === 'fulfilled') setContacts(contsResult.value);
      if (scheduledResult.status === 'fulfilled') setScheduledPayments(scheduledResult.value);
      if (requestsResult.status === 'fulfilled') setPaymentRequests(requestsResult.value);
      if (activityResult.status === 'fulfilled') setTransactions(activityResult.value.events);
      if (vendorsResult.status === 'fulfilled') setVendors(vendorsResult.value.vendors || []);

      // Only show error toast if ALL requests failed
      const allFailed = [accsResult, contsResult, scheduledResult, requestsResult].every(r => r.status === 'rejected');
      if (allFailed && !silent) showNotification('error', "Failed to load transfer data.");
    } catch (err) {
      if (!silent) showNotification('error', "Failed to load transfer data.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleTransferSuccess = (id: string) => {
    showNotification('success', `Transfer initiated successfully! ID: ${id}`);
    // Polling background refresh to account for varying ClickHouse eventual consistency delays
    setTimeout(() => fetchData(true), 1000);
    setTimeout(() => fetchData(true), 3000);
    setTimeout(() => fetchData(true), 6000);
  };

  const handleCancelScheduled = async (payment: ScheduledPayment) => {
    if (confirm("Are you sure you want to cancel this scheduled transfer?")) {
      try {
        await cancelScheduledPayment(payment.id);
        showNotification('success', "Scheduled transfer cancelled.");
        fetchData();
      } catch (err) {
        showNotification('error', "Failed to cancel transfer.");
      }
    }
  };

  const handleCancelRequest = async (request: PaymentRequest) => {
    if (confirm("Are you sure you want to cancel this payment request?")) {
      try {
        await handlePaymentRequestAction(request.id, 'decline');
        showNotification('success', "Payment request cancelled.");
        fetchData();
      } catch (err) {
        showNotification('error', "Failed to cancel request.");
      }
    }
  };

  if (loading && accounts.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div 
          animate={{ rotate: 360 }} 
          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
          className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-400 rounded-full"
        />
      </div>
    );
  }

  return (
    <div className="py-12 px-4 sm:px-6 lg:px-8">
      {/* Notifications */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className={`fixed top-8 left-1/2 -translate-x-1/2 z-[300] px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 border ${
              notification.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
            } backdrop-blur-xl`}
          >
            {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
            <p className="font-bold">{notification.message}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-2 uppercase">
              Transfer <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Center</span>
            </h1>
            <p className="text-white/60 font-medium">Manage your money moves, scheduled payments, and requests in one place.</p>
          </div>
          
          <div className="flex items-center gap-4 bg-white/5 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${
                    activeTab === tab.id 
                      ? `bg-gradient-to-r ${tab.color} text-white shadow-lg` 
                      : "text-white/40 hover:text-white hover:bg-white/10"
                  }`}
                >
                  <Icon size={18} />
                  <span className="hidden md:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-12">
          {/* Main Form Section */}
          <div className="max-w-3xl mx-auto w-full">
            <motion.div
              layout
              className="bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-8 shadow-2xl relative overflow-hidden group"
            >
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 blur-[100px] pointer-events-none group-hover:bg-white/10 transition-colors" />
              
              <div className="relative space-y-8">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-black text-white uppercase tracking-tighter">
                    New {activeTab === 'instant' ? 'Transfer' : activeTab === 'scheduled' ? 'Schedule' : 'Request'}
                  </h2>
                  <div className="p-2 bg-white/5 rounded-lg text-white/40">
                    <Info size={18} />
                  </div>
                </div>

                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    {activeTab === "instant" && (
                      <InstantTransferTab 
                        accounts={accounts} 
                        contacts={contacts} 
                        vendors={vendors}
                        onSuccess={handleTransferSuccess}
                        onError={(msg) => showNotification('error', msg)}
                      />
                    )}
                    {activeTab === "scheduled" && (
                      <ScheduledTransferTab 
                        accounts={accounts} 
                        contacts={contacts} 
                        vendors={vendors}
                        onSuccess={handleTransferSuccess}
                        onError={(msg) => showNotification('error', msg)}
                      />
                    )}
                    {activeTab === "request" && (
                      <RequestTransferTab 
                        contacts={contacts}
                        onSuccess={handleTransferSuccess}
                        onError={(msg) => showNotification('error', msg)}
                      />
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </motion.div>
          </div>

          {/* History / Management Section - Now Below */}
          <div className="space-y-8">
            <div className="bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl">
              <div className="p-8 border-b border-white/5 flex items-center justify-between bg-white/5">
                <h3 className="text-xl font-black text-white uppercase tracking-tight flex items-center gap-3">
                  {activeTab === 'instant' ? 'Recent History' : activeTab === 'scheduled' ? 'Active Schedules' : 'Pending Requests'}
                  <span className="text-[10px] bg-indigo-500/20 px-2 py-1 rounded text-indigo-400 font-bold tracking-widest uppercase border border-indigo-500/20">Live</span>
                </h3>
                <button 
                  onClick={() => fetchData()}
                  className="p-2 hover:bg-white/10 rounded-xl text-white/40 hover:text-white transition-colors"
                >
                  <ChevronRight size={20} />
                </button>
              </div>

              <div className="min-h-[300px]">
                {activeTab === 'scheduled' ? (
                  <ScheduledHistoryTable 
                    payments={scheduledPayments}
                    onViewDetails={(p) => setSelectedDetail({ data: p, type: 'scheduled' })}
                    onCancel={handleCancelScheduled}
                  />
                ) : activeTab === 'instant' ? (
                  <RecentTransactionsTable
                    transactions={transactions}
                  />
                ) : (
                  <RequestHistoryTable 
                    requests={paymentRequests}
                    currentUserEmail={user?.email}
                    onViewDetails={(r) => setSelectedDetail({ data: r, type: 'request' })}
                    onCancel={handleCancelRequest}
                    onPay={(r) => {
                      // Switch to instant transfer and pre-fill
                      setActiveTab('instant');
                      // We can pass data to InstantTransferTab via props if we want, 
                      // but for now let's just scroll up or notify
                      showNotification('success', `Paying request for ${r.amount/100}`);
                    }}
                  />
                )}
              </div>

            </div>

            {/* Extra info cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-8 bg-white border border-slate-200 rounded-3xl shadow-sm hover:shadow-md transition-shadow">
                <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600 mb-4">
                  <Handshake size={20} />
                </div>
                <h4 className="text-slate-900 font-bold mb-2 uppercase tracking-tight">Zero-Config Requests</h4>
                <p className="text-slate-500 text-sm leading-relaxed">Simply enter an email to request funds. Recipients with KarinBank accounts can approve instantly.</p>
              </div>
              <div className="p-8 bg-white border border-slate-200 rounded-3xl shadow-sm hover:shadow-md transition-shadow">
                <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
                  <Calendar size={20} />
                </div>
                <h4 className="text-slate-900 font-bold mb-2 uppercase tracking-tight">Smart Scheduling</h4>
                <p className="text-slate-500 text-sm leading-relaxed">Set up recurring bills or savings goals. Our engine handles the rest, keeping you updated on every execution.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      <DetailModal 
        isOpen={!!selectedDetail}
        onClose={() => setSelectedDetail(null)}
        title={selectedDetail?.type === 'scheduled' ? "Schedule Details" : "Request Details"}
        data={selectedDetail?.data}
        type={selectedDetail?.type || 'scheduled'}
      />
    </div>
  );
}
