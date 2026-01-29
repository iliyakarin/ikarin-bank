"use client";
import { useState, useEffect } from 'react';
import HealthRibbon from '@/components/admin/HealthRibbon';
import TrafficSimulator from '@/components/admin/TrafficSimulator';
import LogTraceTable from '@/components/admin/LogTraceTable';

export default function AdminPage() {
    const [metrics, setMetrics] = useState<any>(null);
    const [traces, setTraces] = useState<any[]>([]);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const res = await fetch('http://localhost:8000/admin/metrics');
                const data = await res.json();
                setMetrics(data);
            } catch (e) {
                console.error("Metrics poll failed", e);
            }
        };

        const fetchTraces = async () => {
            try {
                const res = await fetch('http://localhost:8000/admin/traces');
                const data = await res.json();
                setTraces(data);
            } catch (e) {
                console.error("Traces poll failed", e);
            }
        };

        // Initial load
        fetchMetrics();
        fetchTraces();

        // High frequency polling
        const metricsInterval = setInterval(fetchMetrics, 2000);
        const tracesInterval = setInterval(fetchTraces, 1000);

        return () => {
            clearInterval(metricsInterval);
            clearInterval(tracesInterval);
        };
    }, []);

    return (
        <div className="space-y-6">
            <section className="-mx-6">
                <HealthRibbon metrics={metrics} />
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <section className="lg:col-span-4">
                    <TrafficSimulator />

                    <div className="mt-6 p-6 border border-gray-800 rounded-xl bg-[#0a0a0a]">
                        <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-4">Pipeline Intelligence</h4>
                        <div className="space-y-4">
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Avg E2E Latency</span>
                                <span className="text-green-500 font-mono">4.2ms</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">99th Percentile</span>
                                <span className="text-yellow-500 font-mono">85ms</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Error Rate</span>
                                <span className="text-gray-600 font-mono">0.00%</span>
                            </div>
                            <div className="pt-4 border-t border-gray-900 flex gap-2">
                                <div className="flex-1 h-1 bg-green-500/20 rounded-full"></div>
                                <div className="flex-1 h-1 bg-green-500/20 rounded-full"></div>
                                <div className="flex-1 h-1 bg-green-500/20 rounded-full"></div>
                                <div className="flex-1 h-1 bg-yellow-500/20 rounded-full"></div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="lg:col-span-8">
                    <LogTraceTable traces={traces} />
                </section>
            </div>

            <footer className="pt-12 text-center">
                <div className="inline-flex items-center gap-4 px-4 py-2 bg-gray-900/30 border border-gray-800 rounded-full">
                    <span className="text-[10px] text-gray-600 font-mono">ENCRYPTION: AES-256</span>
                    <span className="text-[10px] text-gray-600 font-mono">AUTH: ADMIN_LVL_4</span>
                    <span className="text-[10px] text-green-900 font-mono">SECURE_LINK_ACTIVE</span>
                </div>
            </footer>
        </div>
    );
}