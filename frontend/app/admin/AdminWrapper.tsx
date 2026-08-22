"use client";
import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { AdminRouteBoundary } from '@/components/RouteErrorBoundaries';
import { Shield, ShieldAlert, ArrowLeft, LogOut, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

export function AdminWrapper({ children }: { children: React.ReactNode }) {
    const { token, isLoading, user, logout } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && !token) {
            router.replace('/auth/login');
        }
    }, [isLoading, token, router]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
                    <p className="text-white/40 font-bold uppercase tracking-widest text-xs">Accessing Command Layer...</p>
                </div>
            </div>
        );
    }

    if (!token) {
        return null;
    }

    // Role gate: if user is not an admin, render high-security Access Denied view without crashing
    if (user && user.role !== 'admin') {
        return (
            <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center p-6">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="max-w-md w-full p-8 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-2xl text-center space-y-6 shadow-2xl"
                >
                    <div className="w-16 h-16 rounded-2xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400 shadow-inner">
                        <ShieldAlert className="w-8 h-8" />
                    </div>

                    <div className="space-y-2">
                        <span className="px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 text-xs font-mono font-bold border border-rose-500/30">
                            403 FORBIDDEN
                        </span>
                        <h2 className="text-2xl font-black text-white tracking-tight mt-2">
                            Restricted Command Layer
                        </h2>
                        <p className="text-xs text-white/50 leading-relaxed">
                            Mission Control requires Administrator credentials. Your account (<span className="text-white/80 font-mono font-semibold">{user.email}</span>) is assigned standard Consumer tier.
                        </p>
                    </div>

                    <div className="flex flex-col gap-2.5 pt-2">
                        <button
                            onClick={() => router.push('/client')}
                            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-purple-500/20 transition-all flex items-center justify-center gap-2"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Return to Financial Dashboard</span>
                        </button>

                        <button
                            onClick={() => {
                                logout();
                                router.push('/auth/login');
                            }}
                            className="w-full py-2.5 px-4 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white font-medium text-xs border border-white/10 transition-all flex items-center justify-center gap-2"
                        >
                            <LogOut className="w-3.5 h-3.5" />
                            <span>Sign in with Administrator Account</span>
                        </button>
                    </div>
                </motion.div>
            </div>
        );
    }

    return (
        <AdminRouteBoundary>
            <div className="min-h-screen bg-[#020617] text-slate-200">
                {/* Premium Admin Header */}
                <header className="border-b border-white/5 bg-slate-950/50 backdrop-blur-xl sticky top-0 z-50">
                    <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
                        <div className="flex items-center gap-6">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-purple-500/20">
                                    <Shield className="w-4 h-4 text-white" />
                                </div>
                                <h1 className="text-lg font-black tracking-tight text-white">
                                    MISSION<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">CONTROL</span>
                                </h1>
                            </div>

                            <div className="hidden md:flex items-center gap-4 pl-4 border-l border-white/10">
                                <div className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/10">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/60">LIVE OPS</span>
                                </div>
                                <div className="text-[10px] font-mono text-white/40">
                                    NODE: PROD-US-EAST
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="hidden sm:flex items-center gap-3 pr-4 border-r border-white/10">
                                <div className="text-right">
                                    <p className="text-xs font-bold text-white">{user?.first_name || 'Admin'} {user?.last_name || ''}</p>
                                    <p className="text-[10px] text-purple-400 font-mono uppercase">{user?.email || 'admin@domain.local'}</p>
                                </div>
                            </div>

                            <button
                                onClick={() => router.push('/client')}
                                className="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white text-xs font-semibold transition-all flex items-center gap-1.5"
                            >
                                <ArrowLeft className="w-3.5 h-3.5" />
                                <span>Client App</span>
                            </button>
                        </div>
                    </div>
                </header>

                <main>{children}</main>
            </div>
        </AdminRouteBoundary>
    );
}
