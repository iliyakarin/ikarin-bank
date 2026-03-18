"use client";
import Link from 'next/link';
import { ShieldAlert, Home, ChevronLeft } from 'lucide-react';

export default function NotFound() {
    return (
        <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 font-sans">
            {/* Ambient background blobs */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/20 blur-[120px] rounded-full" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[45%] h-[45%] bg-indigo-600/15 blur-[120px] rounded-full" />
            </div>

            <div className="w-full max-w-lg text-center space-y-10">
                {/* Animated Icon Container */}
                <div className="relative inline-block">
                    <div className="w-24 h-24 bg-gradient-to-br from-purple-500/20 to-indigo-600/20 rounded-[2rem] flex items-center justify-center border border-white/10 shadow-2xl backdrop-blur-xl relative z-10">
                        <ShieldAlert className="w-10 h-10 text-purple-400" />
                    </div>
                    <div className="absolute -inset-4 bg-purple-500/20 blur-2xl rounded-full animate-pulse" />
                </div>

                <div className="space-y-4">
                    <h1 className="text-8xl font-black tracking-tighter text-white opacity-90">404</h1>
                    <h2 className="text-2xl font-bold text-white tracking-tight uppercase tracking-[0.1em]">Target Not Located</h2>
                    <p className="text-white/40 text-sm max-w-sm mx-auto leading-relaxed font-medium uppercase tracking-wider">
                        The requested data coordinates or administrative layer is inaccessible from your current node.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 items-center justify-center pt-6">
                    <Link
                        href="/client"
                        className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-black text-xs uppercase tracking-[0.2em] rounded-2xl shadow-xl shadow-purple-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3"
                    >
                        <Home className="w-4 h-4" />
                        Return to Base
                    </Link>
                    <button
                        onClick={() => window.history.back()}
                        className="w-full sm:w-auto px-8 py-4 bg-white/5 border border-white/10 text-white/60 font-black text-xs uppercase tracking-[0.2em] rounded-2xl hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-3"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Back Track
                    </button>
                </div>

                <div className="pt-12">
                    <p className="text-[10px] font-black text-white/10 uppercase tracking-[0.5em]">Karin Bank Security Protocol · Alpha-9</p>
                </div>
            </div>
        </div>
    );
}
