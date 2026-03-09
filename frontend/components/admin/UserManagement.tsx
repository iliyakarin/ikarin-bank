"use client";
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useAuth } from '@/lib/AuthContext';

import { motion, AnimatePresence } from 'framer-motion';
import {
    User,
    Search,
    Trash2,
    RefreshCw,
    Shield,
    AlertTriangle,
    CheckCircle,
    AlertCircle,
    Loader2,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';

interface UserManagementProps {
    token: string;
}

export default function UserManagement({ token }: UserManagementProps) {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchEmail, setSearchEmail] = useState("");
    const [foundUser, setFoundUser] = useState<any>(null);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const [deleteSuccess, setDeleteSuccess] = useState("");
    const [deleteStep, setDeleteStep] = useState<0 | 1 | 2>(0); // 0: hidden, 1: first awareness, 2: email confirm
    const [confirmEmail, setConfirmEmail] = useState("");


    // Quick Search & Pagination State
    const [searchTerm, setSearchTerm] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 10;

    const erasureMenuRef = useRef<HTMLDivElement>(null);

    // Sync State
    const [syncLoading, setSyncLoading] = useState(false);
    const [syncError, setSyncError] = useState("");
    const [syncSuccess, setSyncSuccess] = useState("");

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/v1/admin/users?limit=1000", { // Fetch more for frontend filtering/pagination
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (res.ok) setUsers(data);
        } catch (err) {
            console.error("Failed to fetch users", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) {
            fetchUsers();
        }
    }, [token]);

    const handleManualSync = async () => {
        setSyncLoading(true);
        setSyncSuccess("");
        setSyncError("");

        try {
            const res = await fetch("/api/v1/admin/sync-clickhouse", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to trigger sync");

            setSyncSuccess("Sync successfully triggered in the background.");
            setTimeout(() => setSyncSuccess(""), 5000);
        } catch (err: any) {
            setSyncError(err.message);
        } finally {
            setSyncLoading(false);
        }
    };

    const handleSearchUser = async (e: React.FormEvent) => {
        e.preventDefault();
        setSearchError("");
        setFoundUser(null);
        setSearchLoading(true);
        setDeleteSuccess("");

        try {
            const res = await fetch(`/api/v1/admin/users/search?email=${encodeURIComponent(searchEmail)}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "User not found");
            setFoundUser(data);

            // Scroll to find user area
            setTimeout(() => {
                erasureMenuRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        } catch (err: any) {
            setSearchError(err.message);
        } finally {
            setSearchLoading(false);
        }
    };

    const handleDeleteUser = async () => {
        if (confirmEmail !== foundUser.email) {
            setDeleteError("Confirmation email does not match");
            return;
        }

        setDeleteLoading(true);
        setDeleteError("");
        setDeleteStep(0);

        try {
            const res = await fetch(`/api/v1/admin/users/${foundUser.id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to delete user");
            }

            setDeleteSuccess(`User ${foundUser.email} has been purged.`);
            setFoundUser(null);
            setSearchEmail("");
            setConfirmEmail("");
            setDeleteStep(0);
            fetchUsers();
        } catch (err: any) {
            setDeleteError(err.message);
        } finally {
            setDeleteLoading(false);
        }
    };


    // Filtered and Paginated Users
    const filteredUsers = useMemo(() => {
        if (!searchTerm) return users;
        const term = searchTerm.toLowerCase();
        return users.filter(u =>
            u.first_name.toLowerCase().includes(term) ||
            u.last_name.toLowerCase().includes(term) ||
            u.email.toLowerCase().includes(term)
        );
    }, [users, searchTerm]);

    const totalPages = Math.ceil(filteredUsers.length / pageSize);
    const paginatedUsers = useMemo(() => {
        const start = (currentPage - 1) * pageSize;
        return filteredUsers.slice(start, start + pageSize);
    }, [filteredUsers, currentPage]);

    // Reset pagination when search changes
    useEffect(() => {
        setCurrentPage(1);
    }, [searchTerm]);

    return (
        <div className="space-y-8">
            {/* ClickHouse Manual Sync */}
            <div className="glass-panel rounded-[2rem] p-8 space-y-6">
                <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                        <RefreshCw className="text-emerald-400 w-6 h-6" />
                        ClickHouse Data Integrity
                    </h3>
                    <p className="text-white/50 text-sm">
                        Trigger an immediate integrity check between Postgres and ClickHouse.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-6 bg-black/20 rounded-2xl border border-white/5">
                    <div className="flex-1">
                        <p className="text-white/70 text-sm">
                            This process will verify all transaction records and repair any discrepancies via the Kafka outbox.
                        </p>
                        {syncError && <p className="text-red-400 text-xs mt-2">{syncError}</p>}
                        {syncSuccess && <p className="text-emerald-400 text-xs mt-2">{syncSuccess}</p>}
                    </div>

                    <button
                        onClick={handleManualSync}
                        disabled={syncLoading}
                        className="w-full sm:w-auto px-8 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 group"
                    >
                        {syncLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
                        )}
                        {syncLoading ? "Syncing..." : "Sync Now"}
                    </button>
                </div>
            </div>

            {/* User Registry */}
            <div className="glass-panel rounded-[2rem] p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-6">
                        <h3 className="text-xl font-bold text-white flex items-center gap-2">
                            <Shield className="text-indigo-400 w-6 h-6" />
                            User Registry
                        </h3>
                        <div className="hidden md:flex items-center gap-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 w-4 h-4" />
                                <input
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    placeholder="Quick search..."
                                    className="bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-indigo-500/30 transition-all w-64"
                                />
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="md:hidden relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 w-4 h-4" />
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search..."
                                className="bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder:text-white/20 focus:outline-none transition-all w-full"
                            />
                        </div>
                        <button
                            onClick={fetchUsers}
                            className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>


                <div className="relative">
                    <div className="overflow-x-auto rounded-2xl border border-white/5 bg-black/20">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-white/5 text-white/40 font-black uppercase tracking-[0.2em] text-[10px]">
                                    <th className="px-6 py-4">User</th>
                                    <th className="px-6 py-4">Role</th>
                                    <th className="px-6 py-4">Status</th>
                                    <th className="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {loading && users.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-white/20">
                                            <div className="flex flex-col items-center gap-3">
                                                <Loader2 className="w-6 h-6 animate-spin" />
                                                <span className="font-black uppercase tracking-[0.2em] text-[10px]">Accessing Vault...</span>
                                            </div>
                                        </td>
                                    </tr>
                                ) : filteredUsers.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-white/20 font-black uppercase tracking-[0.2em] text-[10px]">No subjects found</td>
                                    </tr>
                                ) : (
                                    paginatedUsers.map((u) => (
                                        <tr key={u.id} className="group hover:bg-white/[0.02] transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center font-black text-indigo-400 border border-indigo-500/10">
                                                        {u.first_name[0]}{u.last_name[0]}
                                                    </div>
                                                    <div>
                                                        <p className="text-white font-bold">{u.first_name} {u.last_name}</p>
                                                        <p className="text-white/30 text-[10px] font-mono">{u.email}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full border uppercase tracking-tighter ${u.role === 'admin' ? 'bg-purple-500/10 border-purple-500/30 text-purple-400' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'}`}>
                                                    {u.role}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2 text-emerald-400/60 text-[10px] font-black uppercase tracking-widest">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                                    Active
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                {currentUser?.id === u.id ? (
                                                    <span className="text-[10px] font-black text-white/20 uppercase tracking-widest px-2">You</span>
                                                ) : (
                                                    <button
                                                        onClick={() => {
                                                            setFoundUser(u);
                                                            setSearchEmail(u.email);
                                                            setTimeout(() => {
                                                                erasureMenuRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                                            }, 100);
                                                        }}
                                                        className="p-2 hover:bg-red-500/10 text-white/10 hover:text-red-400 rounded-lg transition-all"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                            </td>

                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                        <p className="text-[10px] font-black text-white/20 uppercase tracking-[0.2em]">
                            Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, filteredUsers.length)} of {filteredUsers.length}
                        </p>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                disabled={currentPage === 1}
                                className="p-2 rounded-lg border border-white/5 bg-white/5 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <div className="flex items-center gap-1">
                                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                    // Logic to show a window of pages
                                    let pageNum = i + 1;
                                    if (totalPages > 5 && currentPage > 3) {
                                        pageNum = currentPage - 2 + i;
                                        if (pageNum > totalPages) pageNum = totalPages - (4 - i);
                                    }
                                    return (
                                        <button
                                            key={pageNum}
                                            onClick={() => setCurrentPage(pageNum)}
                                            className={`w-8 h-8 rounded-lg text-[10px] font-black transition-all border ${currentPage === pageNum
                                                ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-400'
                                                : 'border-white/5 bg-white/5 text-white/40 hover:bg-white/10'}`}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                            </div>
                            <button
                                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                disabled={currentPage === totalPages}
                                className="p-2 rounded-lg border border-white/5 bg-white/5 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* User Search & Deletion */}
            <div
                ref={erasureMenuRef}
                className="glass-panel rounded-[2rem] p-8 space-y-6 border border-white/5 focus-within:border-red-500/20 transition-all"
            >
                <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                        <Trash2 className="text-red-400 w-6 h-6" />
                        Account Erasure
                    </h3>
                    <p className="text-white/50 text-sm">
                        Permanently delete user accounts and all associated metadata.
                    </p>
                </div>

                <form onSubmit={handleSearchUser} className="flex gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 w-4 h-4" />
                        <input
                            type="email"
                            value={searchEmail}
                            onChange={(e) => setSearchEmail(e.target.value)}
                            placeholder="Search by email..."
                            className="w-full bg-black/20 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-red-500/30 font-mono text-sm transition-all"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={searchLoading}
                        className="px-6 py-3 bg-white/5 hover:bg-white/10 text-white font-black uppercase tracking-widest text-xs border border-white/10 rounded-xl transition-all disabled:opacity-50"
                    >
                        {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
                    </button>
                </form>

                {searchError && (
                    <div className="p-4 bg-red-400/10 border border-red-400/20 rounded-xl text-red-400 text-xs flex items-center gap-3">
                        <AlertCircle className="w-4 h-4" /> {searchError}
                    </div>
                )}

                {deleteSuccess && (
                    <div className="p-4 bg-emerald-400/10 border border-emerald-400/20 rounded-xl text-emerald-400 text-xs flex items-center gap-3">
                        <CheckCircle className="w-4 h-4" /> {deleteSuccess}
                    </div>
                )}

                <AnimatePresence>
                    {foundUser && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            className="p-6 bg-red-500/5 border border-red-500/20 rounded-[1.5rem] space-y-6"
                        >
                            <div className="flex justify-between items-start">
                                <div>
                                    <p className="text-red-400/60 text-[10px] uppercase font-black tracking-[0.2em] mb-1">Target Identified</p>
                                    <h4 className="text-white font-black text-2xl tracking-tight">{foundUser.first_name} {foundUser.last_name}</h4>
                                    <p className="text-white/40 font-mono text-sm">{foundUser.email}</p>
                                </div>
                                <div className="px-3 py-1 bg-red-500/20 text-red-400 text-[10px] font-black rounded-full border border-red-500/30 uppercase tracking-widest">
                                    High Priority
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 bg-black/20 rounded-xl border border-white/5">
                                    <p className="text-white/30 text-[10px] font-black uppercase tracking-widest mb-1">Internal UID</p>
                                    <p className="text-white font-mono text-xs">{foundUser.id}</p>
                                </div>
                                <div className="p-3 bg-black/20 rounded-xl border border-white/5">
                                    <p className="text-white/30 text-[10px] font-black uppercase tracking-widest mb-1">Authorization</p>
                                    <p className="text-white font-mono text-xs capitalize">{foundUser.role}</p>
                                </div>
                            </div>

                            <button
                                onClick={() => setDeleteStep(1)}
                                className="w-full py-4 bg-red-500 hover:bg-red-600 text-white font-black uppercase tracking-[0.2em] text-xs rounded-xl shadow-lg shadow-red-500/20 transition-all flex items-center justify-center gap-3 group"
                            >
                                <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
                                Initiate Account Purge
                            </button>

                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Deletion Dialog - Double Confirmation */}
            <AnimatePresence>
                {deleteStep > 0 && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-slate-950/80 backdrop-blur-xl"
                            onClick={() => setDeleteStep(0)}
                        />
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.9, opacity: 0, y: 20 }}
                            className="relative w-full max-w-lg bg-[#0a0a0b] border border-red-500/30 rounded-[2.5rem] p-10 shadow-2xl"
                        >
                            <div className="text-center space-y-6">
                                <div className="w-20 h-20 bg-red-500/10 border border-red-500/30 rounded-full flex items-center justify-center mx-auto">
                                    <AlertTriangle className="text-red-500 w-10 h-10" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-white font-black text-3xl tracking-tight uppercase">
                                        {deleteStep === 1 ? "Confirm Action" : "Critical Verification"}
                                    </h3>
                                    <p className="text-white/40 text-sm leading-relaxed">
                                        {deleteStep === 1 
                                            ? `You are about to initiate the purge sequence for ${foundUser?.email}. This will delete all associated data.`
                                            : `LAST WARNING: This is IRREVERSIBLE. Purging ${foundUser?.email} will erase all ledger records and transaction history.`
                                        }
                                    </p>
                                </div>

                                <div className="space-y-4">
                                    {deleteStep === 1 ? (
                                        <div className="flex gap-3 pt-2">
                                            <button
                                                onClick={() => setDeleteStep(0)}
                                                className="flex-1 py-4 bg-white/5 hover:bg-white/10 text-white/60 font-black uppercase tracking-widest text-[10px] rounded-2xl transition-all border border-white/5"
                                            >
                                                Abort
                                            </button>
                                            <button
                                                onClick={() => setDeleteStep(2)}
                                                className="flex-[2] px-8 py-4 bg-red-500/20 hover:bg-red-500/30 text-red-500 font-black uppercase tracking-widest text-[10px] rounded-2xl border border-red-500/30 transition-all"
                                            >
                                                I Understand, Proceed
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="space-y-4">
                                            <div className="space-y-2 text-left">
                                                <label className="text-[10px] font-black text-white/30 uppercase tracking-widest pl-1">Final Authorization: Type User Email</label>
                                                <input
                                                    type="email"
                                                    value={confirmEmail}
                                                    onChange={(e) => setConfirmEmail(e.target.value)}
                                                    placeholder="owner@karin.bank"
                                                    className="w-full bg-black/40 border border-red-500/10 rounded-2xl px-5 py-4 text-white placeholder:text-white/10 focus:outline-none focus:border-red-500/40 font-mono text-sm transition-all"
                                                />
                                            </div>

                                            <div className="flex gap-3 pt-2">
                                                <button
                                                    onClick={() => setDeleteStep(0)}
                                                    className="flex-1 py-4 bg-white/5 hover:bg-white/10 text-white/60 font-black uppercase tracking-widest text-[10px] rounded-2xl transition-all border border-white/5"
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    disabled={confirmEmail.toLowerCase() !== foundUser?.email.toLowerCase() || deleteLoading}
                                                    onClick={handleDeleteUser}
                                                    className="flex-[2] px-8 py-4 bg-red-600 hover:bg-red-700 text-white font-black uppercase tracking-widest text-[10px] rounded-2xl shadow-lg shadow-red-500/20 transition-all disabled:opacity-20 disabled:grayscale"
                                                >
                                                    {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "EXECUTE PERMANENT PURGE"}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

        </div>
    );
}
