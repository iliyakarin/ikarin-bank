"use client";
import { useState } from 'react';

export default function TrafficSimulator() {
    const [tps, setTps] = useState(10);
    const [dispatched, setDispatched] = useState(0);
    const [loading, setLoading] = useState(false);

    const handleInject = async (count: number) => {
        setLoading(true);
        try {
            const res = await fetch('/api/admin/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tps, count }),
            });
            if (res.ok) {
                setDispatched(prev => prev + count);
            }
        } catch (error) {
            console.error("Simulation failed", error);
        }
        setLoading(false);
    };

    return (
        <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-red-600 rounded-full"></span>
                    Traffic Simulator
                </h3>
                <div className="text-xs font-mono text-red-500 bg-red-950/30 px-2 py-1 rounded border border-red-900/50">
                    SESSION DISPATCHED: {dispatched.toLocaleString()}
                </div>
            </div>

            <div className="space-y-8">
                <div>
                    <div className="flex justify-between mb-2">
                        <label className="text-xs text-gray-500 uppercase font-bold">Throughput (TPS)</label>
                        <span className="text-xs font-mono text-white bg-gray-800 px-2 py-0.5 rounded">{tps} tx/s</span>
                    </div>
                    <input
                        type="range"
                        min="1"
                        max="1000"
                        value={tps}
                        onChange={(e) => setTps(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-red-600"
                    />
                    <div className="flex justify-between mt-2 text-[10px] text-gray-600 font-mono">
                        <span>1 TPS</span>
                        <span>500 TPS</span>
                        <span>1000 TPS</span>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <button
                        onClick={() => handleInject(100)}
                        disabled={loading}
                        className="bg-gray-900 hover:bg-gray-800 text-gray-300 border border-gray-700 py-3 rounded-lg font-mono text-xs uppercase tracking-widest transition-all active:scale-95 disabled:opacity-50"
                    >
                        Inject 100
                    </button>
                    <button
                        onClick={() => handleInject(1000)}
                        disabled={loading}
                        className="bg-red-900/20 hover:bg-red-900/30 text-red-500 border border-red-900/50 py-3 rounded-lg font-mono text-xs uppercase tracking-widest transition-all active:scale-95 disabled:opacity-50 shadow-[0_0_15px_rgba(220,38,38,0.1)]"
                    >
                        🔥 BURST 1000
                    </button>
                </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-800/50">
                <div className="flex items-center gap-2 text-[10px] text-gray-600 font-mono">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-ping"></div>
                    Ready for injection signal...
                </div>
            </div>
        </div>
    );
}
