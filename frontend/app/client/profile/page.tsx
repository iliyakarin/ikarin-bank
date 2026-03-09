"use client";
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    User,
    Mail,
    Shield,
    Lock,
    CheckCircle,
    AlertCircle,
    Loader2,
    AlertTriangle,
    Star,
    RefreshCw,
    Settings,
    Trash2,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { useBalance } from "@/hooks/useDashboard";

export default function ProfilePage() {
    const { user, token, logout, login, settings, updateSettings } = useAuth();
    const { balance, loading: balanceLoading } = useBalance(false);

    // Backup State
    const [backupEmail, setBackupEmail] = useState("");
    const [backupLoading, setBackupLoading] = useState(false);
    const [backupSuccess, setBackupSuccess] = useState("");
    const [backupError, setBackupError] = useState("");

    // Password State
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [passLoading, setPassLoading] = useState(false);
    const [passSuccess, setPassSuccess] = useState("");
    const [passError, setPassError] = useState("");
    const [showPassConfirm, setShowPassConfirm] = useState(false);

    // Sync State
    const [syncLoading, setSyncLoading] = useState(false);
    const [syncError, setSyncError] = useState("");
    const [syncSuccess, setSyncSuccess] = useState("");

    // Admin User Management
    const [users, setUsers] = useState<any[]>([]);
    const [usersLoading, setUsersLoading] = useState(false);
    const [searchEmail, setSearchEmail] = useState("");
    const [foundUser, setFoundUser] = useState<any>(null);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const [deleteSuccess, setDeleteSuccess] = useState("");
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [confirmEmail, setConfirmEmail] = useState("");

    if (!user) return null;

    const fetchUsers = async () => {
        setUsersLoading(true);
        try {
            const res = await fetch("/api/v1/admin/users", {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (res.ok) setUsers(data);
        } catch (err) {
            console.error("Failed to fetch users", err);
        } finally {
            setUsersLoading(false);
        }
    };

    useEffect(() => {
        if (token && user?.role === "admin") {
            fetchUsers();
        }
    }, [token, user]);

    const handleBackupUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setBackupError("");
        setBackupSuccess("");
        setBackupLoading(true);

        try {
            const res = await fetch("/api/v1/users/me/backup", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ backup_email: backupEmail }),
            });

            const data = await res.json();
            if (!res.ok)
                throw new Error(data.detail || "Failed to update backup email");

            setBackupSuccess(
                "Backup email updated successfully! Please refresh or log back in to see changes globally.",
            );
            setBackupEmail("");
        } catch (err: any) {
            setBackupError(err.message);
        } finally {
            setBackupLoading(false);
        }
    };

    const handlePasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPassError("");
        setPassSuccess("");

        if (newPassword !== confirmPassword) {
            setPassError("New passwords do not match");
            return;
        }

        if (newPassword.length < 8) {
            setPassError("New password must be at least 8 characters long");
            return;
        }

        setShowPassConfirm(true);
    };

    const handlePasswordUpdate = async () => {
        setPassLoading(true);
        setShowPassConfirm(false);

        try {
            const res = await fetch(
                "/api/v1/users/me/password",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword,
                    }),
                },
            );

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to update password");

            setPassSuccess(
                "Password updated successfully! Logging you out in 3 seconds...",
            );
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");

            setTimeout(() => {
                logout();
            }, 3000);
        } catch (err: any) {
            setPassError(err.message);
        } finally {
            setPassLoading(false);
        }
    };

    const handleManualSync = async () => {
        setSyncLoading(true);
        setSyncSuccess("");
        setSyncError("");

        try {
            const res = await fetch(
                "/api/admin/sync-clickhouse",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                },
            );

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
        setShowDeleteConfirm(false);

        try {
            const res = await fetch(`/api/v1/admin/users/${foundUser.id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to delete user");
            }

            setDeleteSuccess(`User ${foundUser.email} and all associated data have been purged.`);
            setFoundUser(null);
            setSearchEmail("");
            setConfirmEmail("");
            fetchUsers(); // Refresh the list
        } catch (err: any) {
            setDeleteError(err.message);
        } finally {
            setDeleteLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
            >
                <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                    <User className="text-purple-400 w-8 h-8" />
                    Profile & Settings
                </h1>
                <p className="text-white/60 text-lg">
                    Manage your account details and security preferences.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* User Details Box */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6 md:col-span-2 flex flex-col sm:flex-row items-center sm:items-start gap-8"
                >
                    <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex flex-shrink-0 items-center justify-center shadow-lg shadow-purple-500/20">
                        <span className="text-white font-black text-4xl">
                            {user.first_name[0]}
                            {user.last_name[0]}
                        </span>
                    </div>
                    <div className="flex-1 space-y-4 w-full">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">
                                    Full Name
                                </p>
                                <p className="text-white font-semibold text-lg">
                                    {user.first_name} {user.last_name}
                                </p>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">
                                    Account Role
                                </p>
                                <div className="flex items-center gap-3">
                                    <p className="text-white font-semibold text-lg capitalize">
                                        {user.role}
                                    </p>

                                    {!balanceLoading &&
                                        user.role === "user" &&
                                        balance !== null &&
                                        balance >= 100000 && (
                                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold leading-none bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30">
                                                <Star className="w-3 h-3 mr-1 fill-amber-400" />
                                                Premium Member
                                            </span>
                                        )}

                                    {user.role === "admin" && (
                                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold leading-none bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                            <Shield className="w-3 h-3 mr-1" />
                                            Administrator
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">
                                    Primary Email
                                </p>
                                <p className="text-white font-semibold text-lg">{user.email}</p>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">
                                    Backup Email
                                </p>
                                <p className="text-white font-semibold text-lg">
                                    {user.backup_email || (
                                        <span className="text-white/30 italic">Not set</span>
                                    )}
                                </p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Preferences Form */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6 md:col-span-2"
                >
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                            <Settings className="text-pink-400 w-6 h-6" />
                            Display Preferences
                        </h3>
                        <p className="text-white/50 text-sm">
                            Customize how information is displayed across the application.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5">
                            <div>
                                <p className="text-white font-medium">Time Format</p>
                                <p className="text-white/50 text-xs">Switch between 12-hour and 24-hour time.</p>
                            </div>
                            <button
                                onClick={() => updateSettings({ use24Hour: !settings.use24Hour })}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${settings.use24Hour ? 'bg-purple-500' : 'bg-white/20'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${settings.use24Hour ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>
                        <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5">
                            <div>
                                <p className="text-white font-medium">Date Format</p>
                                <p className="text-white/50 text-xs">Use European format (DD.MM.YYYY).</p>
                            </div>
                            <button
                                onClick={() => updateSettings({ useEUDates: !settings.useEUDates })}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${settings.useEUDates ? 'bg-purple-500' : 'bg-white/20'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${settings.useEUDates ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>
                    </div>

                    {/* Live Preview */}
                    <div className="mt-4 p-5 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-500/20 rounded-xl">
                        <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-3">
                            Live Preview
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                                <p className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Date</p>
                                <p className="text-white font-mono text-sm">
                                    {new Date().toLocaleDateString(
                                        settings.useEUDates ? "en-GB" : "en-US",
                                        { year: "numeric", month: "2-digit", day: "2-digit" }
                                    )}
                                </p>
                                <p className="text-white/30 text-[10px] mt-1">
                                    {settings.useEUDates ? "DD/MM/YYYY" : "MM/DD/YYYY"}
                                </p>
                            </div>
                            <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                                <p className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Time</p>
                                <p className="text-white font-mono text-sm">
                                    {new Date().toLocaleTimeString(
                                        settings.useEUDates ? "en-GB" : "en-US",
                                        { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: !settings.use24Hour }
                                    )}
                                </p>
                                <p className="text-white/30 text-[10px] mt-1">
                                    {settings.use24Hour ? "24-hour" : "12-hour (AM/PM)"}
                                </p>
                            </div>
                            <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                                <p className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Full Timestamp</p>
                                <p className="text-white font-mono text-sm">
                                    {new Date().toLocaleString(
                                        settings.useEUDates ? "en-GB" : "en-US",
                                        { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: !settings.use24Hour }
                                    )}
                                </p>
                                <p className="text-white/30 text-[10px] mt-1">
                                    As shown across the portal
                                </p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Backup Email Form */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6"
                >
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                            <Mail className="text-indigo-400 w-6 h-6" />
                            Backup Email
                        </h3>
                        <p className="text-white/50 text-sm">
                            Add a backup email address that can be used only to restore access
                            to the banking app.
                        </p>
                    </div>

                    <form onSubmit={handleBackupUpdate} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">
                                New Backup Email
                            </label>
                            <input
                                type="email"
                                value={backupEmail}
                                onChange={(e) => setBackupEmail(e.target.value)}
                                placeholder="backup@example.com"
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                required
                            />
                        </div>

                        {backupError && (
                            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" /> {backupError}
                            </div>
                        )}
                        {backupSuccess && (
                            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" /> {backupSuccess}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={backupLoading || !backupEmail}
                            className="w-full bg-white/10 hover:bg-white/20 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center"
                        >
                            {backupLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                "Update Backup Email"
                            )}
                        </button>
                    </form>
                </motion.div>

                {/* Password Form */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6"
                >
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                            <Lock className="text-purple-400 w-6 h-6" />
                            Change Password
                        </h3>
                        <p className="text-white/50 text-sm">
                            Ensure your account uses a long, random password to stay secure.
                        </p>
                    </div>

                    <form onSubmit={handlePasswordSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">
                                Current Password
                            </label>
                            <input
                                type="password"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">
                                New Password
                            </label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">
                                Confirm New Password
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>

                        {passError && (
                            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" /> {passError}
                            </div>
                        )}
                        {passSuccess && (
                            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" /> {passSuccess}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={
                                passLoading ||
                                !currentPassword ||
                                !newPassword ||
                                !confirmPassword
                            }
                            className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center shadow-lg"
                        >
                            {passLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                "Update Password"
                            )}
                        </button>
                    </form>
                </motion.div>

                {/* Admin Tools */}
                {user.role === "admin" && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="bg-white/5 backdrop-blur-xl border border-indigo-500/30 rounded-3xl p-8 space-y-6 md:col-span-2"
                    >
                        <div>
                            <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                                <Shield className="text-indigo-400 w-6 h-6" />
                                Administrative Controls
                            </h3>
                            <p className="text-white/50 text-sm">
                                Advanced actions available only to administrators.
                            </p>
                        </div>

                        <div className="bg-black/20 border border-white/10 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-6">
                            <div>
                                <h4 className="text-white font-semibold flex items-center gap-2">
                                    <RefreshCw className="w-5 h-5 text-emerald-400" /> ClickHouse Manual Sync
                                </h4>
                                <p className="text-white/50 text-sm mt-1 max-w-md">
                                    Trigger an immediate integrity check between Postgres and ClickHouse. Discrepancies will be automatically repaired via the Kafka outbox.
                                </p>
                                {syncError && <p className="text-red-400 text-sm mt-2">{syncError}</p>}
                                {syncSuccess && <p className="text-emerald-400 text-sm mt-2">{syncSuccess}</p>}
                            </div>

                            <button
                                onClick={handleManualSync}
                                disabled={syncLoading}
                                className="w-full sm:w-auto shrink-0 bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-300 border border-indigo-500/30 font-bold py-3 px-6 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {syncLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" /> Syncing...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw className="w-5 h-5" /> Sync Now
                                    </>
                                )}
                            </button>
                        </div>

                        {/* User Directory */}
                        <div className="bg-black/20 border border-white/5 rounded-2xl p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <h4 className="text-white font-semibold flex items-center gap-2">
                                    <Shield className="w-5 h-5 text-indigo-400" /> User Directory
                                </h4>
                                <button
                                    onClick={fetchUsers}
                                    className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white"
                                    title="Refresh List"
                                >
                                    <RefreshCw className={`w-4 h-4 ${usersLoading ? 'animate-spin' : ''}`} />
                                </button>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-white/5 text-white/40 font-bold uppercase tracking-widest text-[10px]">
                                            <th className="pb-3 pl-2">User</th>
                                            <th className="pb-3">Role</th>
                                            <th className="pb-3">Registered</th>
                                            <th className="pb-3 text-right pr-2">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {usersLoading && users.length === 0 ? (
                                            <tr>
                                                <td colSpan={4} className="py-8 text-center text-white/20">Loading registry...</td>
                                            </tr>
                                        ) : users.length === 0 ? (
                                            <tr>
                                                <td colSpan={4} className="py-8 text-center text-white/20">No users found</td>
                                            </tr>
                                        ) : (
                                            users.slice(0, 10).map((u) => (
                                                <tr key={u.id} className="group hover:bg-white/[0.02] transition-colors">
                                                    <td className="py-3 pl-2">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-indigo-400 group-hover:bg-indigo-500/20 transition-colors">
                                                                {u.first_name[0]}{u.last_name[0]}
                                                            </div>
                                                            <div>
                                                                <p className="text-white font-medium">{u.first_name} {u.last_name}</p>
                                                                <p className="text-white/40 text-xs">{u.email}</p>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="py-3">
                                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${u.role === 'admin' ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' : 'bg-white/5 border-white/10 text-white/40'}`}>
                                                            {u.role.toUpperCase()}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 text-white/40 text-xs">
                                                        {new Date().toLocaleDateString()}
                                                    </td>
                                                    <td className="py-3 text-right pr-2">
                                                        <button
                                                            onClick={() => {
                                                                setFoundUser(u);
                                                                setSearchEmail(u.email);
                                                                window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                                                            }}
                                                            className="p-2 hover:bg-red-500/20 text-white/20 hover:text-red-400 rounded-lg transition-all"
                                                            title="Target for Deletion"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* User Erasure Tool */}
                        <div className="bg-black/20 border border-red-500/20 rounded-2xl p-6 space-y-6">
                            <div>
                                <h4 className="text-white font-semibold flex items-center gap-2">
                                    <Trash2 className="w-5 h-5 text-red-400" /> User Erasure & GDPR Compliance
                                </h4>
                                <p className="text-white/50 text-sm mt-1">
                                    Locate and permanently delete a user account and all associated transaction records from both PostgreSQL and ClickHouse.
                                </p>
                            </div>

                            <form onSubmit={handleSearchUser} className="flex flex-col sm:flex-row gap-3">
                                <input
                                    type="email"
                                    value={searchEmail}
                                    onChange={(e) => setSearchEmail(e.target.value)}
                                    placeholder="Enter user email to search..."
                                    className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-red-500/30"
                                    required
                                />
                                <button
                                    type="submit"
                                    disabled={searchLoading}
                                    className="bg-white/5 hover:bg-white/10 text-white font-bold py-3 px-6 rounded-xl border border-white/10 transition-all flex items-center justify-center gap-2"
                                >
                                    {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify User"}
                                </button>
                            </form>

                            {searchError && (
                                <p className="text-red-400 text-sm">{searchError}</p>
                            )}

                            {deleteSuccess && (
                                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4 flex-shrink-0" /> {deleteSuccess}
                                </div>
                            )}

                            {foundUser && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="p-6 bg-red-500/5 border border-red-500/20 rounded-2xl space-y-4"
                                >
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-white/40 text-[10px] uppercase font-black tracking-widest">Target Account Found</p>
                                            <h5 className="text-white font-bold text-xl">{foundUser.first_name} {foundUser.last_name}</h5>
                                            <p className="text-white/60 text-sm">{foundUser.email}</p>
                                            <div className="flex gap-4 mt-2">
                                                <span className="text-[10px] text-white/40">ID: {foundUser.id}</span>
                                                <span className="text-[10px] text-white/40">ROLE: {foundUser.role}</span>
                                            </div>
                                        </div>
                                        <div className="px-3 py-1 bg-red-500/20 text-red-400 text-[10px] font-bold rounded-full border border-red-500/30 uppercase tracking-tighter">
                                            Permanent Deletion
                                        </div>
                                    </div>

                                    {deleteError && (
                                        <p className="text-red-400 text-sm bg-red-400/10 p-3 rounded-lg border border-red-400/20">{deleteError}</p>
                                    )}

                                    <button
                                        onClick={() => setShowDeleteConfirm(true)}
                                        className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-red-500/20 transition-all flex items-center justify-center gap-2"
                                    >
                                        <Trash2 size={18} /> Purge This Account
                                    </button>
                                </motion.div>
                            )}
                        </div>
                    </motion.div>
                )}
            </div>

            {/* User Deletion Confirmation Modal */}
            <AnimatePresence>
                {showDeleteConfirm && foundUser && (
                    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowDeleteConfirm(false)}
                            className="absolute inset-0 bg-black/80 backdrop-blur-md"
                        />
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 10 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 10 }}
                            className="relative bg-[#1a0f1f] border border-red-500/50 w-full max-w-lg rounded-[2.5rem] p-10 shadow-2xl overflow-hidden"
                        >
                            <div className="space-y-6 text-center">
                                <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-500/50">
                                    <AlertTriangle className="text-red-500 w-10 h-10" />
                                </div>
                                <div>
                                    <h3 className="text-3xl font-bold text-white mb-2">
                                        CRITICAL ACTION
                                    </h3>
                                    <p className="text-white/70">
                                        You are about to permanently delete <span className="text-white font-bold">{foundUser.email}</span>. This action is irreversible and will purge all financial history and PII.
                                    </p>
                                </div>

                                <div className="space-y-4 text-left">
                                    <label className="text-white/50 text-xs font-bold uppercase tracking-widest pl-1">
                                        Type "{foundUser.email}" to confirm
                                    </label>
                                    <input
                                        type="text"
                                        value={confirmEmail}
                                        onChange={(e) => setConfirmEmail(e.target.value)}
                                        placeholder={foundUser.email}
                                        className="w-full bg-black/40 border border-red-500/30 rounded-2xl px-5 py-4 text-white font-mono text-sm focus:outline-none focus:ring-4 focus:ring-red-500/20 transition-all"
                                    />
                                </div>

                                <div className="flex gap-4 pt-4">
                                    <button
                                        onClick={() => {
                                            setShowDeleteConfirm(false);
                                            setConfirmEmail("");
                                        }}
                                        className="flex-1 py-4 px-4 rounded-2xl font-bold text-white/60 hover:text-white hover:bg-white/10 transition-colors border border-white/10"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleDeleteUser}
                                        disabled={deleteLoading || confirmEmail !== foundUser.email}
                                        className="flex-1 py-4 px-4 rounded-2xl font-black text-white bg-gradient-to-r from-red-600 to-red-800 hover:from-red-500 hover:to-red-700 shadow-xl disabled:opacity-30 disabled:grayscale transition-all flex items-center justify-center gap-2"
                                    >
                                        {deleteLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "PURGE USER"}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Password Confirmation Modal */}
            <AnimatePresence>
                {showPassConfirm && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowPassConfirm(false)}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 10 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 10 }}
                            className="relative bg-[#2a1f42] border border-red-500/30 w-full max-w-sm rounded-[2rem] p-8 shadow-2xl shadow-red-500/10 overflow-hidden"
                        >
                            <div className="space-y-6 text-center">
                                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-500/50">
                                    <AlertTriangle className="text-red-400 w-8 h-8" />
                                </div>
                                <h3 className="text-2xl font-bold text-white">
                                    Change Password?
                                </h3>
                                <p className="text-white/70">
                                    Are you sure you want to change your password? You will be
                                    logged out globally upon success.
                                </p>

                                <div className="flex gap-3 pt-4">
                                    <button
                                        onClick={() => setShowPassConfirm(false)}
                                        className="flex-1 py-3 px-4 rounded-xl font-bold text-white/80 hover:text-white hover:bg-white/10 transition-colors border border-white/20"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handlePasswordUpdate}
                                        className="flex-1 py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-red-500 to-pink-600 hover:from-red-600 hover:to-pink-700 shadow-lg"
                                    >
                                        Yes, Change
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
