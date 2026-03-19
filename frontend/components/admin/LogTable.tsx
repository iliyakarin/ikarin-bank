"use client";
import React from 'react';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { Database, Clock, Server, CheckCircle2, AlertCircle, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

interface LogEntry {
    id: string;
    merchant: string;
    postgres_at: string;
    kafka_at?: string;
    clickhouse_at?: string;
    latency?: number;
    status: string;
}

export default function MultiSourceLogTable({ logs }: { logs: LogEntry[] }) {
    return (
        <Card noPadding>
            <div className="p-6 border-b border-gray-50 flex items-center justify-between">
                <div>
                    <h3 className="font-bold text-gray-900">Distributed Traces</h3>
                    <p className="text-xs font-medium text-gray-400">Live multi-source propagation logs</p>
                </div>
                <Badge variant="neutral" icon={<Activity className="w-3 h-3 text-emerald-500" />}>
                    Live Update
                </Badge>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="bg-gray-50/50 text-left">
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Transaction ID</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Sources</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest text-right">Latency</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest text-right">Final Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {logs.map((log, i) => (
                            <motion.tr
                                key={log.id}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.05 }}
                                className="group hover:bg-gray-50/50 transition-colors"
                            >
                                <td className="px-6 py-5">
                                    <div className="flex flex-col">
                                        <span className="text-gray-900 font-bold text-sm truncate w-32">{log.merchant}</span>
                                        <code className="text-[10px] font-mono text-gray-400 mt-1">{log.id}</code>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="flex flex-col items-center gap-1 group/source">
                                            <Database className={`w-4 h-4 ${log.postgres_at ? 'text-indigo-500' : 'text-gray-200'}`} />
                                            <span className="text-[8px] font-bold text-gray-400">PG</span>
                                        </div>
                                        <div className="w-4 h-px bg-gray-200" />
                                        <div className="flex flex-col items-center gap-1">
                                            <Server className={`w-4 h-4 ${log.kafka_at ? 'text-amber-500' : 'text-gray-200'}`} />
                                            <span className="text-[8px] font-bold text-gray-400">KF</span>
                                        </div>
                                        <div className="w-4 h-px bg-gray-200" />
                                        <div className="flex flex-col items-center gap-1">
                                            <CheckCircle2 className={`w-4 h-4 ${log.clickhouse_at ? 'text-emerald-500' : 'text-gray-200'}`} />
                                            <span className="text-[8px] font-bold text-gray-400">CH</span>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5 text-right">
                                    {log.latency ? (
                                        <span className="text-xs font-bold text-gray-700">
                                            {Math.round(log.latency)}ms
                                        </span>
                                    ) : (
                                        <span className="text-xs font-bold text-gray-300">N/A</span>
                                    )}
                                </td>
                                <td className="px-6 py-5 text-right">
                                    <Badge variant={log.status === 'cleared' ? 'success' : 'warning'}>
                                        {log.status === 'cleared' ? 'Finalized' : log.status}
                                    </Badge>
                                </td>
                            </motion.tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </Card>
    );
}
