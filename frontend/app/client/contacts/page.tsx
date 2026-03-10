"use client";
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trash2,
  Plus,
  Users,
  Search,
  UserCircle,
  Loader2,
  Edit2,
  Check,
  X,
  Building2,
  Building,
  CreditCard,
  History,
  Info,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

type Contact = {
  id: number;
  contact_name: string;
  contact_email?: string;
  contact_type: "karin" | "merchant" | "bank";
  merchant_id?: string;
  subscriber_id?: string;
  bank_name?: string;
  routing_number?: string;
  account_number?: string;
  created_at: string;
};

type Vendor = {
  id: string;
  name: string;
  category: string;
  email: string;
};

type Bank = {
  name: string;
  routing_number: string;
};

export default function ContactsPage() {
  const { token } = useAuth();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Form selections
  const [activeTab, setActiveTab] = useState<"karin" | "merchant" | "bank">("karin");
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);

  // Add Contact form state
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newMerchantId, setNewMerchantId] = useState("");
  const [newSubscriberId, setNewSubscriberId] = useState("");
  const [newBankName, setNewBankName] = useState("");
  const [newRoutingNumber, setNewRoutingNumber] = useState("");
  const [newAccountNumber, setNewAccountNumber] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Edit Contact state
  const [editingContactId, setEditingContactId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  // Metadata edit could be added but current simplified Edit usually just covers the display name/email

  useEffect(() => {
    if (token) {
      fetchContacts();
      fetchMetadata();
    }
  }, [token]);

  const fetchContacts = async () => {
    try {
      const res = await fetch("/api/v1/contacts", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setContacts(data);
      }
    } catch (err) {
      console.error("Failed to fetch contacts", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetadata = async () => {
    try {
      const [vRes, bRes] = await Promise.all([
        fetch("/api/v1/vendors", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("/api/v1/banks", { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (vRes.ok) {
        const vData = await vRes.json();
        setVendors(vData.vendors || []);
      }
      if (bRes.ok) {
        const bData = await bRes.json();
        setBanks(bData.banks || []);
      }
    } catch (err) {
      console.error("Failed to fetch metadata", err);
    }
  };

  const resetForm = () => {
    setNewName("");
    setNewEmail("");
    setNewMerchantId("");
    setNewSubscriberId("");
    setNewBankName("");
    setNewRoutingNumber("");
    setNewAccountNumber("");
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setActionLoading(true);

    const body: any = {
      contact_name: newName,
      contact_type: activeTab,
    };

    if (activeTab === "karin") {
      body.contact_email = newEmail;
    } else if (activeTab === "merchant") {
      body.merchant_id = newMerchantId;
      body.subscriber_id = newSubscriberId;
      // Auto-set name if not provided manually
      if (!newName.trim()) {
        const v = vendors.find(v => v.id === newMerchantId);
        body.contact_name = v ? v.name : "Merchant";
      }
    } else if (activeTab === "bank") {
      body.bank_name = newBankName;
      body.routing_number = newRoutingNumber;
      body.account_number = newAccountNumber;
    }

    try {
      const res = await fetch("/api/v1/contacts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to add contact");
      }

      setSuccess("Contact added successfully!");
      resetForm();
      fetchContacts();

      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteContact = async (id: number) => {
    if (!confirm("Are you sure you want to delete this contact?")) return;

    try {
      const res = await fetch(`/api/v1/contacts/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        setContacts(contacts.filter((c) => c.id !== id));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to delete contact");
      }
    } catch (err) {
      console.error("Failed to delete contact", err);
      alert("An error occurred");
    }
  };

  const handleStartEdit = (contact: Contact) => {
    setEditingContactId(contact.id);
    setEditName(contact.contact_name);
    setEditEmail(contact.contact_email || "");
    setError(""); // clear errors
  };

  const handleCancelEdit = () => {
    setEditingContactId(null);
    setEditName("");
    setEditEmail("");
  };

  const handleSaveEdit = async (id: number) => {
    if (!editName.trim()) return;
    setActionLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/v1/contacts/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          contact_name: editName,
          contact_email: editEmail,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update contact");
      }
      setContacts(contacts.map((c) => (c.id === id ? data : c)));
      setEditingContactId(null);
      setSuccess("Contact updated successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredContacts = contacts.filter(
    (c) =>
      c.contact_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.contact_email && c.contact_email.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.merchant_id && c.merchant_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.bank_name && c.bank_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">My Address Book</h1>
          <p className="text-white/60">
            Save payees for faster KarinBank, Merchant, or ACH payments.
          </p>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
          <input
            type="text"
            placeholder="Search contacts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
          />
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Add Contact Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 sticky top-8">
            <div className="flex bg-black/40 p-1 rounded-xl mb-6">
              <button
                onClick={() => { setActiveTab("karin"); setError(""); }}
                className={`flex-1 flex flex-col items-center py-2 px-1 rounded-lg text-[10px] font-bold transition-all ${activeTab === "karin" ? "bg-purple-600 text-white" : "text-white/40 hover:text-white"}`}
              >
                <UserCircle size={16} className="mb-1" />
                KARIN
              </button>
              <button
                onClick={() => { setActiveTab("merchant"); setError(""); }}
                className={`flex-1 flex flex-col items-center py-2 px-1 rounded-lg text-[10px] font-bold transition-all ${activeTab === "merchant" ? "bg-indigo-600 text-white" : "text-white/40 hover:text-white"}`}
              >
                <Building2 size={16} className="mb-1" />
                MERCHANT
              </button>
              <button
                onClick={() => { setActiveTab("bank"); setError(""); }}
                className={`flex-1 flex flex-col items-center py-2 px-1 rounded-lg text-[10px] font-bold transition-all ${activeTab === "bank" ? "bg-emerald-600 text-white" : "text-white/40 hover:text-white"}`}
              >
                <Building size={16} className="mb-1" />
                BANK
              </button>
            </div>

            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              {activeTab === "karin" ? "Add New KarinBank Contact" : activeTab === "merchant" ? "Add New Merchant" : "Add External Bank Account"}
            </h2>

            <form onSubmit={handleAddContact} className="space-y-4">
              {activeTab === "karin" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Display Name</label>
                    <input
                      type="text"
                      required
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="e.g. Alice Smith"
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Email Address</label>
                    <input
                      type="email"
                      required
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder="alice@example.com"
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    />
                  </div>
                </>
              )}

              {activeTab === "merchant" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Select Merchant</label>
                    <select
                      required
                      value={newMerchantId}
                      onChange={(e) => setNewMerchantId(e.target.value)}
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
                    >
                      <option value="" disabled className="bg-[#1a1a2e]">Select a company</option>
                      {vendors.map((v) => (
                        <option key={v.id} value={v.id} className="bg-[#1a1a2e] text-xs">
                          {v.name} ({v.category})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Subscriber / Account ID</label>
                    <input
                      type="text"
                      required
                      value={newSubscriberId}
                      onChange={(e) => setNewSubscriberId(e.target.value)}
                      placeholder="e.g. 1002345"
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2 italic text-white/40 font-normal">Nickname (Optional)</label>
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="e.g. My Electric Bill"
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                  </div>
                </>
              )}

              {activeTab === "bank" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Select Target Bank</label>
                    <select
                      required
                      value={newBankName}
                      onChange={(e) => {
                        const bank = banks.find(b => b.name === e.target.value);
                        setNewBankName(e.target.value);
                        if (bank) setNewRoutingNumber(bank.routing_number);
                      }}
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 appearance-none"
                    >
                      <option value="" disabled className="bg-[#1a1a2e]">Select a bank</option>
                      {banks.map((b) => (
                        <option key={b.routing_number} value={b.name} className="bg-[#1a1a2e] text-xs">
                          {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-2 text-xs">Routing Number</label>
                      <input
                        type="text"
                        readOnly
                        value={newRoutingNumber}
                        placeholder="RTN"
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white opacity-50 cursor-not-allowed text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-2 text-xs">Account Number</label>
                      <input
                        type="text"
                        required
                        value={newAccountNumber}
                        onChange={(e) => setNewAccountNumber(e.target.value)}
                        placeholder="Ending in..."
                        className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Recipient Legal Name</label>
                    <input
                      type="text"
                      required
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="e.g. Alice P. Smith"
                      className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                    />
                  </div>
                </>
              )}

              {error && (
                <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400 text-xs shadow-lg">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-xl text-green-400 text-xs shadow-lg">
                  {success}
                </div>
              )}

              <button
                type="submit"
                disabled={actionLoading || !newName.trim()}
                className={`w-full bg-gradient-to-r ${activeTab === "karin" ? "from-purple-600 to-indigo-600 shadow-purple-500/20" :
                    activeTab === "merchant" ? "from-indigo-600 to-blue-600 shadow-indigo-500/20" :
                      "from-emerald-600 to-teal-600 shadow-emerald-500/20"
                  } hover:brightness-110 text-white font-bold py-3.5 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-xl`}
              >
                {actionLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <Plus size={18} />
                    Save {activeTab === "karin" ? "Contact" : activeTab === "merchant" ? "Merchant" : "Account"}
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 flex items-start gap-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
              <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <p className="text-[10px] text-blue-200/70 leading-relaxed">
                {activeTab === "karin" ? "Send instant P2P transfers to any KarinBank user by email." :
                  activeTab === "merchant" ? "Bill pay for top US utilities, telecom, and services via vendor aggregation." :
                    "Transfer funds to external checking/savings accounts via ACH network."}
              </p>
            </div>
          </div>
        </div>

        {/* Contact List */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl">
              <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-4" />
              <p className="text-white/60">Loading address book...</p>
            </div>
          ) : filteredContacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl text-center px-4">
              <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
                <Users className="w-8 h-8 text-white/40" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No payees found</h3>
              <p className="text-white/60 max-w-sm">
                {searchQuery ? "Try adjusting your search query." : "Save your first contact to get started with easy payments."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AnimatePresence>
                {filteredContacts.map((contact) => (
                  <motion.div
                    key={contact.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-white/5 backdrop-blur-xl border border-white/10 p-5 rounded-2xl flex items-center justify-between group hover:bg-white/10 transition-all border-l-4"
                    style={{
                      borderLeftColor: contact.contact_type === "karin" ? "#9333ea" : contact.contact_type === "merchant" ? "#4f46e5" : "#10b981"
                    }}
                  >
                    {editingContactId === contact.id ? (
                      <div className="flex-1 space-y-3 w-full animate-in fade-in zoom-in duration-200">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
                          placeholder="Name"
                        />
                        {contact.contact_type === "karin" && (
                          <input
                            type="email"
                            value={editEmail}
                            onChange={(e) => setEditEmail(e.target.value)}
                            className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
                            placeholder="Email Address"
                          />
                        )}
                        <div className="flex justify-end gap-2 pt-1">
                          <button
                            onClick={handleCancelEdit}
                            disabled={actionLoading}
                            className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-white/70 transition-colors"
                          >
                            <X size={16} />
                          </button>
                          <button
                            onClick={() => handleSaveEdit(contact.id)}
                            disabled={actionLoading}
                            className="p-2 bg-indigo-500/20 hover:bg-indigo-500/40 border border-indigo-500/30 rounded-lg text-indigo-300 transition-colors"
                          >
                            {actionLoading ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Check size={16} />
                            )}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-4 truncate">
                          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${contact.contact_type === "karin" ? "bg-purple-500/10 text-purple-400" :
                              contact.contact_type === "merchant" ? "bg-indigo-500/10 text-indigo-400" :
                                "bg-emerald-500/10 text-emerald-400"
                            }`}>
                            {contact.contact_type === "karin" ? <UserCircle size={22} /> :
                              contact.contact_type === "merchant" ? <Building2 size={22} /> :
                                <Building size={22} />}
                          </div>
                          <div className="truncate">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-white font-bold text-base truncate">{contact.contact_name}</h3>
                              <span className={`px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-tighter ${contact.contact_type === "karin" ? "bg-purple-500/20 text-purple-400" :
                                  contact.contact_type === "merchant" ? "bg-indigo-500/20 text-indigo-400" :
                                    "bg-emerald-500/20 text-emerald-400"
                                }`}>
                                {contact.contact_type === "karin" ? "KarinBank" : contact.contact_type}
                              </span>
                            </div>
                            <div className="text-white/40 text-[10px] flex flex-col">
                              {contact.contact_type === "karin" && <span>{contact.contact_email}</span>}
                              {contact.contact_type === "merchant" && (
                                <>
                                  <span className="truncate">Merchant: {contact.merchant_id}</span>
                                  <span>ID: {contact.subscriber_id}</span>
                                </>
                              )}
                              {contact.contact_type === "bank" && (
                                <>
                                  <span>{contact.bank_name}</span>
                                  <span className="flex items-center gap-1">
                                    <History size={10} /> RTN: {contact.routing_number}
                                  </span>
                                  <span>Account: ****{contact.account_number?.slice(-4)}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity ml-2">
                          <button
                            onClick={() => handleStartEdit(contact)}
                            className="p-2 text-white/40 hover:text-blue-400 hover:bg-blue-400/10 rounded-xl transition-all"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteContact(contact.id)}
                            className="p-2 text-white/40 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
