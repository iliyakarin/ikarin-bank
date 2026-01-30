"use client";
import React from 'react';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { Database, Zap, Activity, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface MetricTilesProps {
    stats: {
        postgres_count: number;
        clickhouse_count: number;
        delta: number;
        kafka_lag: number;
        system_volume: number;
        sync_health: string;
        status: string;
    } | null;
}

export default function MetricTiles({ stats }: MetricTilesProps) {
    if (!stats) return null;

    const metrics = [
        {
            label: "Postgres Total",
            value: stats.postgres_count.toLocaleString(),
            icon: Database,
            color: "indigo",
            status: "Source of Truth"
        },
        {
            label: "Kafka Backlog",
            value: stats.kafka_lag,
            icon: Zap,
            color: "amber",
            status: stats.kafka_lag > 100 ? "High Latency" : "Healthy"
        },
        {
            label: "ClickHouse Ingested",
            value: stats.clickhouse_count.toLocaleString(),
            icon: Activity,
            color: "emerald",
            status: "Real-time"
        },
        {
            label: "Pipeline Drift",
            value: stats.delta,
            icon: AlertCircle,
            color: stats.delta > 5 ? "red" : "gray",
            status: stats.sync_health
        },
        {
            label: "System Volume (24h)",
            value: `$${stats.system_volume.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            icon: Database,
            color: "purple",
            status: "P2P Transfers"
        }
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-10">
            {metrics.map((m, i) => (
                <motion.div
                    key={m.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                >
                    <Card className="hover:border-gray-200 transition-all cursor-default group">
                        <div className="flex items-start justify-between">
                            <div className={`p-3 rounded-2xl bg-${m.color}-50 text-${m.color}-600 group-hover:scale-110 transition-transform`}>
                                <m.icon className="w-6 h-6" />
                            </div>
                            <Badge variant={m.color === 'red' ? 'error' : 'neutral'}>
                                {m.status}
                            </Badge>
                        </div>
                        <div className="mt-6">
                            <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest">{m.label}</h3>
                            <p className="text-3xl font-black text-gray-900 mt-1">{m.value}</p>
                        </div>
                    </Card>
                </motion.div>
            ))}
        </div>
    );
}
