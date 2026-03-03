'use client';
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Mail, Shield, Lock, CheckCircle, AlertCircle, Loader2, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

export default function ProfilePage() {
    const { user, token, logout, login } = useAuth();

    // Backup State
    const [backupEmail, setBackupEmail] = useState('');
    const [backupLoading, setBackupLoading] = useState(false);
    const [backupSuccess, setBackupSuccess] = useState('');
    const [backupError, setBackupError] = useState('');

    // Password State
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passLoading, setPassLoading] = useState(false);
    const [passSuccess, setPassSuccess] = useState('');
    const [passError, setPassError] = useState('');
    const [showPassConfirm, setShowPassConfirm] = useState(false);

    if (!user) return null;

    const handleBackupUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setBackupError('');
        setBackupSuccess('');
        setBackupLoading(true);

        try {
            const res = await fetch('http://localhost:8000/api/v1/users/me/backup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ backup_email: backupEmail })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to update backup email');

            setBackupSuccess('Backup email updated successfully! Please refresh or log back in to see changes globally.');
            setBackupEmail('');
        } catch (err: any) {
            setBackupError(err.message);
        } finally {
            setBackupLoading(false);
        }
    };

    const handlePasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPassError('');
        setPassSuccess('');

        if (newPassword !== confirmPassword) {
            setPassError('New passwords do not match');
            return;
        }

        if (newPassword.length < 8) {
            setPassError('New password must be at least 8 characters long');
            return;
        }

        setShowPassConfirm(true);
    };

    const handlePasswordUpdate = async () => {
        setPassLoading(true);
        setShowPassConfirm(false);

        try {
            const res = await fetch('http://localhost:8000/api/v1/users/me/password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to update password');

            setPassSuccess('Password updated successfully! Logging you out in 3 seconds...');
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');

            setTimeout(() => {
                logout();
            }, 3000);

        } catch (err: any) {
            setPassError(err.message);
        } finally {
            setPassLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
                <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                    <User className="text-purple-400 w-8 h-8" />
                    Profile & Settings
                </h1>
                <p className="text-white/60 text-lg">Manage your account details and security preferences.</p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* User Details Box */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6 md:col-span-2 flex flex-col sm:flex-row items-center sm:items-start gap-8">
                    <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex flex-shrink-0 items-center justify-center shadow-lg shadow-purple-500/20">
                        <span className="text-white font-black text-4xl">
                            {user.first_name[0]}{user.last_name[0]}
                        </span>
                    </div>
                    <div className="flex-1 space-y-4 w-full">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">Full Name</p>
                                <p className="text-white font-semibold text-lg">{user.first_name} {user.last_name}</p>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">Account Role</p>
                                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold leading-none bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                    <Shield className="w-3 h-3 mr-1" />
                                    {user.role.toUpperCase()}
                                </span>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">Primary Email</p>
                                <p className="text-white font-semibold text-lg">{user.email}</p>
                            </div>
                            <div>
                                <p className="text-white/50 text-sm font-medium mb-1">Backup Email</p>
                                <p className="text-white font-semibold text-lg">{user.backup_email || <span className="text-white/30 italic">Not set</span>}</p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Backup Email Form */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6">
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                            <Mail className="text-indigo-400 w-6 h-6" />
                            Backup Email
                        </h3>
                        <p className="text-white/50 text-sm">Add a backup email address that can be used only to restore access to the banking app.</p>
                    </div>

                    <form onSubmit={handleBackupUpdate} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">New Backup Email</label>
                            <input
                                type="email"
                                value={backupEmail}
                                onChange={(e) => setBackupEmail(e.target.value)}
                                placeholder="backup@example.com"
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                required
                            />
                        </div>

                        {backupError && <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2"><AlertCircle className="w-4 h-4" /> {backupError}</div>}
                        {backupSuccess && <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center gap-2"><CheckCircle className="w-4 h-4" /> {backupSuccess}</div>}

                        <button
                            type="submit"
                            disabled={backupLoading || !backupEmail}
                            className="w-full bg-white/10 hover:bg-white/20 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center"
                        >
                            {backupLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Update Backup Email'}
                        </button>
                    </form>
                </motion.div>

                {/* Password Form */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6">
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                            <Lock className="text-purple-400 w-6 h-6" />
                            Change Password
                        </h3>
                        <p className="text-white/50 text-sm">Ensure your account uses a long, random password to stay secure.</p>
                    </div>

                    <form onSubmit={handlePasswordSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">Current Password</label>
                            <input
                                type="password"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">New Password</label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-white/70 text-sm font-medium block">Confirm New Password</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                required
                            />
                        </div>

                        {passError && <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2"><AlertCircle className="w-4 h-4" /> {passError}</div>}
                        {passSuccess && <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center gap-2"><CheckCircle className="w-4 h-4" /> {passSuccess}</div>}

                        <button
                            type="submit"
                            disabled={passLoading || !currentPassword || !newPassword || !confirmPassword}
                            className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center shadow-lg"
                        >
                            {passLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Update Password'}
                        </button>
                    </form>
                </motion.div>
            </div>

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
                                <h3 className="text-2xl font-bold text-white">Change Password?</h3>
                                <p className="text-white/70">
                                    Are you sure you want to change your password? You will be logged out globally upon success.
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
