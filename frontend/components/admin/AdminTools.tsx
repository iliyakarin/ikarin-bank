"use client";
import React, { useState } from 'react';
import { Play, Settings, Info, Zap, Layers, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';

export default function AdminTools() {
    const { token } = useAuth();
    const [tps, setTps] = useState(2);
    const [count, setCount] = useState(10);
    const [status, setStatus] = useState<string | null>(null);

    const startSimulation = async () => {
        try {
            const res = await fetch('/api/v1/admin/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ tps, count }),
            });
            if (res.ok) {
                setStatus('Simulation started');
                setTimeout(() => setStatus(null), 3000);
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel border-l-0 rounded-l-none bg-slate-900/40 p-8 h-full space-y-10"
        >
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                    <Settings className="text-white w-6 h-6" />
                </div>
                <div>
                    <h3 className="font-black text-white text-lg tracking-tight">TRAFFIC ENGINE</h3>
                    <p className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] opacity-70">Stress Test Module</p>
                </div>
            </div>

            <div className="space-y-8">
                <div className="space-y-4">
                    <div className="flex justify-between items-center px-1">
                        <div className="flex items-center gap-2">
                            <Zap className="w-3.5 h-3.5 text-amber-400" />
                            <label className="text-[10px] font-black text-white/40 uppercase tracking-widest">Throughput</label>
                        </div>
                        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-black text-indigo-400">{tps} TPS</span>
                    </div>
                    <div className="relative h-6 flex items-center">
                        <input
                            type="range" min="1" max="20" value={tps}
                            onChange={(e) => setTps(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-white/5 rounded-full appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 transition-all border border-white/5"
                        />
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex justify-between items-center px-1">
                        <div className="flex items-center gap-2">
                            <Layers className="w-3.5 h-3.5 text-blue-400" />
                            <label className="text-[10px] font-black text-white/40 uppercase tracking-widest">Batch Load</label>
                        </div>
                        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-black text-blue-400">{count} TXs</span>
                    </div>
                    <div className="relative h-6 flex items-center">
                        <input
                            type="range" min="1" max="100" value={count}
                            onChange={(e) => setCount(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-white/5 rounded-full appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 transition-all border border-white/5"
                        />
                    </div>
                </div>

                <div className="pt-4">
                    <button
                        onClick={startSimulation}
                        className="w-full h-14 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-black text-sm uppercase tracking-widest rounded-2xl shadow-xl shadow-purple-500/20 transition-all flex items-center justify-center gap-3 active:scale-[0.98]"
                    >
                        <Play className="w-4 h-4 fill-current" /> Initialize Blast
                    </button>

                    {status && (
                        <motion.p
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-[10px] font-black text-emerald-400 text-center mt-4 tracking-[0.2em] uppercase"
                        >
                            {status}
                        </motion.p>
                    )}
                </div>
            </div>

            <div className="pt-10 border-t border-white/5">
                <div className="bg-white/5 p-5 rounded-3xl border border-white/5 flex gap-4">
                    <div className="mt-1">
                        <Cpu className="w-5 h-5 text-indigo-400 opacity-60" />
                    </div>
                    <p className="text-[10px] font-bold text-white/40 leading-relaxed tracking-tight">
                        Simulation tokens are ephemeral and processed isolate from the production ledger.
                        Used for stress-testing <span className="text-indigo-400/60">Kafka-ClickHouse</span> sync pipelines.
                    </p>
                </div>
            </div>
        </motion.div>
    );
}
