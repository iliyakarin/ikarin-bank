"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { AdminRouteBoundary } from '@/components/RouteErrorBoundaries';

export function AdminWrapper({ children }: { children: React.ReactNode }) {
    const { token, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && !token) {
            router.replace('/auth/login');
        }
    }, [isLoading, token, router]);

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    }

    return (
        <AdminRouteBoundary>
            <div className="min-h-screen bg-[#050505] text-gray-300 font-mono">
                {/* HUD Header */}
                <header className="border-b border-gray-900 bg-black/50 backdrop-blur-md sticky top-0 z-50">
                    <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-6 h-6 bg-red-600 rounded flex items-center justify-center text-white font-black text-xs">M</div>
                            <h1 className="text-sm font-bold uppercase tracking-[0.2em] text-white">Mission Control</h1>
                            <div className="h-4 w-[1px] bg-gray-800 mx-2"></div>
                            <div className="text-[10px] text-gray-500 font-mono">SECTOR: TRW-01</div>
                        </div>

                        <div className="flex items-center gap-6">
                            <div className="flex flex-col items-end">
                                <span className="text-[9px] text-gray-500 uppercase font-black tracking-widest">Network Load</span>
                                <div className="w-24 h-1 bg-gray-900 rounded-full overflow-hidden">
                                    <div className="w-1/3 h-full bg-red-600"></div>
                                </div>
                            </div>
                            <div className="w-8 h-8 rounded border border-gray-800 flex items-center justify-center text-gray-500 text-xs">
                                01
                            </div>
                        </div>
                    </div>
                </header>

                <main className="max-w-[1600px] mx-auto p-6">
                    {children}
                </main>
            </div>
        </AdminRouteBoundary>
    );
}