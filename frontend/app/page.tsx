"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';

export default function HomePage() {
    const router = useRouter();
    const { token, isLoading } = useAuth();

    useEffect(() => {
        if (!isLoading) {
            if (token) {
                router.replace('/client');
            } else {
                router.replace('/auth/login');
            }
        }
    }, [isLoading, token, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 via-indigo-900 to-black">
            <div className="animate-pulse text-white/60 font-bold">
                Redirecting...
            </div>
        </div>
    );
}
