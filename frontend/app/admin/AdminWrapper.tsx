"use client";
import React, { useEffect } from 'react';
import { useRouter, notFound } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { AdminRouteBoundary } from '@/components/RouteErrorBoundaries';
import { Shield, Activity, Zap, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

export function AdminWrapper({ children }: { children: React.ReactNode }) {
    const { token, isLoading, user } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading) {
            if (!token) {
                router.replace('/auth/login');
            } else if (user?.role !== 'admin') {
                notFound();
            }
        }
    }, [isLoading, token, user, router]);

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

    // Guard: Do not render anything if not logged in or not an admin
    // The useEffect will handle the actual redirection or notFound error
    if (!token || user?.role !== 'admin') {
        return null;
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
                                <div className="text-[10px] font-bold text-white/30 uppercase tracking-widest">
                                    SEC-LAYER: <span className="text-indigo-400">ALPHA-9</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-6">
                            <div className="hidden lg:flex items-center gap-8 mr-4">
                                <div className="flex flex-col items-end">
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest mb-1">
                                        <Zap className="w-3 h-3 text-amber-400" /> System Load
                                    </div>
                                    <div className="w-32 h-1 bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: "0%" }}
                                            animate={{ width: "24%" }}
                                            className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col items-end">
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest mb-1">
                                        <Activity className="w-3 h-3 text-emerald-400" /> Node Health
                                    </div>
                                    <div className="flex gap-1">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className={`w-1.5 h-3 rounded-sm ${i < 5 ? 'bg-emerald-500/40' : 'bg-white/5'}`} />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3 pl-6 border-l border-white/10">
                                <div className="text-right">
                                    <p className="text-xs font-bold text-white leading-none">{user?.first_name} {user?.last_name}</p>
                                    <p className="text-[10px] font-bold text-indigo-400 uppercase mt-0.5 tracking-tighter">Root Admin</p>
                                </div>
                                <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:border-purple-500/50 transition-all">
                                    <Cpu className="w-4 h-4 text-white/60" />
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <main className="max-w-[1600px] mx-auto p-8">
                    {children}
                </main>
            </div>
        </AdminRouteBoundary>
    );
}
