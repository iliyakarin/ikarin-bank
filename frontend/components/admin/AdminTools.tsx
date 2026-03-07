"use client";
import React, { useState } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Play, Settings, Info } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import { motion } from 'framer-motion';

export default function AdminTools() {
    const [tps, setTps] = useState(2);
    const [count, setCount] = useState(10);
    const [status, setStatus] = useState<string | null>(null);

    const startSimulation = async () => {
        try {
            const res = await fetch('/api/admin/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
        <Card className="h-full border-l-0 rounded-l-none bg-gray-50/50">
            <div className="space-y-8">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center">
                        <Settings className="text-white w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="font-bold text-gray-900">Traffic Engine</h3>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Pipeline Stress Test</p>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <label className="text-xs font-bold text-gray-500 uppercase">Throughput (TPS)</label>
                            <Badge variant="primary">{tps} TPS</Badge>
                        </div>
                        <input
                            type="range" min="1" max="20" value={tps}
                            onChange={(e) => setTps(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black"
                        />
                    </div>

                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <label className="text-xs font-bold text-gray-500 uppercase">Batch Count</label>
                            <Badge variant="neutral">{count} TXs</Badge>
                        </div>
                        <input
                            type="range" min="1" max="100" value={count}
                            onChange={(e) => setCount(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black"
                        />
                    </div>

                    <Button
                        onClick={startSimulation}
                        className="w-full"
                        size="md"
                    >
                        <Play className="w-4 h-4 mr-2" /> Start Simulation
                    </Button>

                    {status && (
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-xs font-bold text-emerald-600 text-center"
                        >
                            {status}
                        </motion.p>
                    )}
                </div>

                <div className="pt-8 border-t border-gray-100">
                    <div className="bg-white p-4 rounded-2xl border border-gray-100 flex gap-3">
                        <Info className="w-5 h-5 text-indigo-500 flex-shrink-0" />
                        <p className="text-[10px] font-medium text-gray-400 leading-relaxed">
                            Simulation tokens are ephemeral and purely for stress-testing Kafka lag and ClickHouse ingestion speed.
                        </p>
                    </div>
                </div>
            </div>
        </Card>
    );
}
