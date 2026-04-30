"use client";
import React, { useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import { motion, AnimatePresence } from 'framer-motion';
import { usePathname, useRouter } from 'next/navigation';
import PortalHeader from '@/components/PortalHeader';
import { useAuth } from '@/lib/AuthContext';
import { ClientRouteBoundary } from '@/components/RouteErrorBoundaries';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { token, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && !token) {
            router.replace('/auth/login');
        }
    }, [isLoading, token, router]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-black">Loading...</div>
        );
    }

    return (
        <ClientRouteBoundary key={pathname}>
            <div className="flex bg-gradient-to-br from-purple-900 via-indigo-900 to-black min-h-screen font-sans selection:bg-white selection:text-black">
                <Sidebar />
                <main className="flex-1 relative overflow-x-hidden min-h-screen">
                    <div className="p-6 md:p-10 max-w-7xl mx-auto">
                        <PortalHeader />
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={pathname}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
                            >
                                {children}
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </ClientRouteBoundary>
    );
}
