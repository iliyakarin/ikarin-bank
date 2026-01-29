"use client";

interface Trace {
    id: string;
    merchant: string;
    postgres_at: string;
    kafka_at: string;
    clickhouse_at: string | null;
    latency: number | null;
}

export default function LogTraceTable({ traces }: { traces: Trace[] }) {
    const formatTime = (isoString: string) => {
        return new Date(isoString).toLocaleTimeString(undefined, {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3,
        });
    };

    return (
        <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-gray-800 bg-[#0f0f0f] flex justify-between items-center">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                    Multi-Source Trace View
                </h3>
                <div className="text-[10px] font-mono text-gray-500">
                    Showing last 20 propagations
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#111] text-gray-500 uppercase">
                        <tr>
                            <th className="px-4 py-3 border-b border-gray-800">Transaction ID</th>
                            <th className="px-4 py-3 border-b border-gray-800 text-blue-500">Postgres (SOT)</th>
                            <th className="px-4 py-3 border-b border-gray-800 text-orange-500">Kafka (Ingest)</th>
                            <th className="px-4 py-3 border-b border-gray-800 text-green-500">ClickHouse (BI)</th>
                            <th className="px-4 py-3 border-b border-gray-800 text-right">E2E Latency</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-900">
                        {traces.length > 0 ? (
                            traces.map((trace) => (
                                <tr key={trace.id} className="hover:bg-gray-900/50 transition-colors group">
                                    <td className="px-4 py-3 text-gray-400">
                                        <span className="text-gray-600">ID_</span>
                                        {trace.id.substring(0, 8)}...
                                        <div className="text-[9px] text-gray-700">{trace.merchant}</div>
                                    </td>
                                    <td className="px-4 py-3 text-blue-400">{formatTime(trace.postgres_at)}</td>
                                    <td className="px-4 py-3 text-orange-400">{formatTime(trace.kafka_at)}</td>
                                    <td className="px-4 py-3">
                                        {trace.clickhouse_at ? (
                                            <span className="text-green-500">{formatTime(trace.clickhouse_at)}</span>
                                        ) : (
                                            <div className="flex items-center gap-1.5 text-gray-600 italic animate-pulse">
                                                <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                                                Processing...
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        {trace.latency ? (
                                            <span className={`font-bold ${trace.latency > 1000 ? 'text-red-500' : 'text-gray-300'}`}>
                                                {trace.latency.toFixed(0)}
                                                <span className="text-[9px] ml-1 opacity-50 font-normal">ms</span>
                                            </span>
                                        ) : (
                                            <span className="text-gray-700">--</span>
                                        )}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={5} className="px-4 py-12 text-center text-gray-600 italic">
                                    Waiting for transaction traffic...
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
