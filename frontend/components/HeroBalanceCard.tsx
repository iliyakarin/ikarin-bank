"use client";

interface SparklineProps {
    data: { value: number }[];
    color?: string;
}

function Sparkline({ data, color = "#2563eb" }: SparklineProps) {
    if (!data || data.length === 0) return null;

    const min = Math.min(...data.map(d => d.value));
    const max = Math.max(...data.map(d => d.value));
    const range = max - min || 1;
    const width = 100;
    const height = 30;

    const points = data.map((d, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((d.value - min) / range) * height;
        return `${x},${y}`;
    }).join(" ");

    return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
            />
        </svg>
    );
}

export default function HeroBalanceCard({ balance, trend }: { balance: number, trend: { value: number }[] }) {
    return (
        <div className="bg-gradient-to-br from-primary-600 to-indigo-700 rounded-2xl p-6 text-white shadow-xl shadow-primary-200">
            <div className="flex flex-col gap-1">
                <span className="text-primary-100 text-sm font-medium">Total Balance</span>
                <h1 className="text-4xl font-bold tracking-tight">
                    ${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </h1>
            </div>

            <div className="mt-8">
                <div className="flex justify-between items-end mb-2">
                    <span className="text-primary-100 text-xs font-medium">Monthly Trend</span>
                    <span className="text-green-300 text-xs font-bold">+4.2%</span>
                </div>
                <div className="h-10 opacity-80">
                    <Sparkline data={trend} color="white" />
                </div>
            </div>
        </div>
    );
}
