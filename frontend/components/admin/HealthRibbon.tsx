"use client";

interface MetricProps {
    label: string;
    value: number | string;
    threshold?: number;
    suffix?: string;
    type?: 'count' | 'lag';
}

function Metric({ label, value, threshold, suffix = "", type = 'count' }: MetricProps) {
    let statusColor = "text-green-400";
    if (threshold && typeof value === 'number') {
        if (value > threshold) statusColor = "text-red-500";
        else if (value > threshold * 0.7) statusColor = "text-yellow-400";
    }

    return (
        <div className="flex flex-col px-6 border-r border-gray-800 last:border-0">
            <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">{label}</span>
            <div className={`text-xl font-mono font-bold ${statusColor}`}>
                {typeof value === 'number' ? value.toLocaleString() : value}
                <span className="text-xs ml-1 opacity-50">{suffix}</span>
            </div>
        </div>
    );
}

export default function HealthRibbon({ metrics }: { metrics: any }) {
    return (
        <div className="bg-black border-y border-gray-800 py-3 flex items-center overflow-x-auto no-scrollbar shadow-[0_0_20px_rgba(0,0,0,0.5)]">
            <div className="flex items-center px-4 mr-4">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse mr-2"></div>
                <span className="text-[10px] font-mono text-green-500 font-bold uppercase tracking-tighter">System Live</span>
            </div>

            <Metric label="Postgres Count" value={metrics?.postgres_count ?? 0} />
            <Metric label="Kafka Lag" value={metrics?.kafka_lag ?? 0} threshold={5000} suffix="msg" type="lag" />
            <Metric label="ClickHouse Count" value={metrics?.clickhouse_count ?? 0} />

            <div className="ml-auto px-6 flex items-center gap-4">
                <div className="text-[10px] font-mono text-gray-600">
                    Uptime: <span className="text-gray-400">02:45:12</span>
                </div>
                <div className="text-[10px] font-mono text-gray-600">
                    Nodes: <span className="text-gray-400">4/4</span>
                </div>
            </div>
        </div>
    );
}
