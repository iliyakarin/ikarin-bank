"use client";

export default function DashboardSkeleton() {
    return (
        <div className="space-y-12 pb-12">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-3">
                    <div className="h-10 w-64 bg-white/10 rounded animate-pulse" />
                    <div className="h-6 w-48 bg-white/5 rounded animate-pulse" />
                </div>
                <div className="h-14 w-64 bg-white/5 rounded-2xl animate-pulse" />
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="glass-panel p-6 rounded-[2rem] space-y-4">
                        <div className="w-12 h-12 bg-white/10 rounded-2xl animate-pulse" />
                        <div className="space-y-2">
                            <div className="h-4 w-24 bg-white/5 rounded animate-pulse" />
                            <div className="h-8 w-32 bg-white/10 rounded animate-pulse" />
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                {/* Balance History */}
                <div className="xl:col-span-8 glass-panel p-8 rounded-[2rem] space-y-6">
                    <div className="h-6 w-40 bg-white/10 rounded animate-pulse" />
                    <div className="h-64 bg-white/5 rounded-2xl animate-pulse" />
                </div>

                {/* Spending by Category */}
                <div className="xl:col-span-4 glass-panel p-8 rounded-[2rem] space-y-6">
                    <div className="h-6 w-40 bg-white/10 rounded animate-pulse" />
                    <div className="space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="space-y-2">
                                <div className="flex justify-between">
                                    <div className="h-4 w-24 bg-white/5 rounded animate-pulse" />
                                    <div className="h-4 w-16 bg-white/5 rounded animate-pulse" />
                                </div>
                                <div className="h-2 bg-white/5 rounded-full animate-pulse" />
                            </div>
                        ))}
                    </div>
                </div>

                {/* Transactions */}
                <div className="xl:col-span-12 glass-panel p-2 rounded-[2.5rem] space-y-6">
                    <div className="p-6 flex justify-between items-center">
                        <div className="h-6 w-48 bg-white/10 rounded animate-pulse" />
                        <div className="h-5 w-16 bg-white/5 rounded animate-pulse" />
                    </div>
                    <div className="p-6 space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="flex items-center justify-between p-4 bg-white/5 rounded-2xl">
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 bg-white/10 rounded-2xl animate-pulse" />
                                    <div className="space-y-2">
                                        <div className="h-5 w-32 bg-white/10 rounded animate-pulse" />
                                        <div className="h-4 w-20 bg-white/5 rounded animate-pulse" />
                                    </div>
                                </div>
                                <div className="h-5 w-20 bg-white/10 rounded animate-pulse" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
